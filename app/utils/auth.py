import os
from typing import Optional
import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, status, Security
from fastapi.security import APIKeyHeader, OAuth2AuthorizationCodeBearer
from app.models.auth import CognitoUser


# Cognito OAuth2 scheme for Swagger UI
COGNITO_REGION = os.getenv("COGNITO_REGION", "ca-central-1")
COGNITO_DOMAIN = os.getenv("COGNITO_DOMAIN", "")


def _cognito_host(domain: str, region: str) -> str:
    """
    Resolve a host for Cognito OAuth URLs. Accepts either:
      - a Cognito domain prefix (e.g. "myapp-dev-auth") or
      - a custom domain (e.g. "login.gbadske.org" or "https://login.gbadske.org").
    """
    if not domain:
        return ""
    # If a full URL was provided, extract netloc
    try:
        from urllib.parse import urlparse
        parsed = urlparse(domain)
        if parsed.netloc:
            return parsed.netloc
    except Exception:
        pass

    # If domain contains a dot, assume it's a custom domain
    if "." in domain:
        return domain

    # Otherwise it's a Cognito domain prefix
    return f"{domain}.auth.{region}.amazoncognito.com"


COGNITO_HOST = _cognito_host(COGNITO_DOMAIN, COGNITO_REGION)
COGNITO_AUTHORIZATION_URL = f"https://{COGNITO_HOST}/oauth2/authorize" if COGNITO_HOST else ""
COGNITO_TOKEN_URL = f"https://{COGNITO_HOST}/oauth2/token" if COGNITO_HOST else ""

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=COGNITO_AUTHORIZATION_URL,
    tokenUrl=COGNITO_TOKEN_URL,
    scopes={"openid": "OpenID", "email": "Email", "profile": "Profile"},
    auto_error=False
) if COGNITO_DOMAIN else None


class CognitoVerifier:
    """
    FastAPI dependency for verifying Bearer tokens in API requests.
    Supports both legacy hardcoded tokens and AWS Cognito JWTs.
    Usage: Add as a dependency to endpoints. Raises HTTPException if invalid.
    """

    def __init__(
        self,
        expected_token: str = None,
        cognito_region: str = None,
        cognito_user_pool_id: str = None,
        accepted_client_ids: list = None,
        required_groups: list = None,
    ):
        # Legacy token support (backwards compatibility)
        self.expected_token = expected_token or os.getenv("DPM_AUTH_TOKEN")

        # Cognito configuration
        self.cognito_region = cognito_region or os.getenv("COGNITO_REGION")
        self.cognito_user_pool_id = cognito_user_pool_id or os.getenv("COGNITO_USER_POOL_ID")
        self.accepted_client_ids = accepted_client_ids or (
            os.getenv("COGNITO_CLIENT_IDS", "").split(",") if os.getenv("COGNITO_CLIENT_IDS") else []
        )
        self.required_groups = required_groups or []

        # Initialize JWKS client if Cognito is configured
        self.jwks_client = None
        if self.cognito_region and self.cognito_user_pool_id:
            jwks_url = f"https://cognito-idp.{self.cognito_region}.amazonaws.com/{self.cognito_user_pool_id}/.well-known/jwks.json"
            self.jwks_client = PyJWKClient(jwks_url)
            self.cognito_issuer = f"https://cognito-idp.{self.cognito_region}.amazonaws.com/{self.cognito_user_pool_id}"

    def __call__(
        self,
        api_key: Optional[str] = Security(APIKeyHeader(name="Authorization", auto_error=False)),
        oauth_token: Optional[str] = Security(oauth2_scheme) if oauth2_scheme else None
    ):
        # Try OAuth2 token first (from Swagger UI)
        if oauth_token:
            if self.jwks_client:
                try:
                    return self._verify_cognito_token(oauth_token)
                except HTTPException:
                    pass

        # Try Bearer token from Authorization header
        if api_key:
            scheme, _, token = api_key.partition(" ")
            if scheme.lower() == "bearer" and token:
                # Try legacy token first (backwards compatibility)
                if self.expected_token and token == self.expected_token:
                    user = CognitoUser.from_legacy_token()
                    if self.required_groups:
                        # Legacy tokens have admin access, so they pass group checks
                        pass
                    return user

                # Try Cognito JWT validation
                if self.jwks_client:
                    try:
                        return self._verify_cognito_token(token)
                    except HTTPException:
                        pass

        # No valid authentication found
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def _verify_cognito_token(self, token: str) -> dict:
        """
        Verify a Cognito JWT token.
        
        Returns:
            dict: Token payload with user information and groups
        
        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Get the signing key from Cognito
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            # Decode and verify the token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self.cognito_issuer,
                options={"verify_aud": False}  # We'll verify client_id manually if needed
            )

            # Verify client_id if accepted_client_ids is configured
            if self.accepted_client_ids:
                token_client_id = payload.get("client_id") or payload.get("aud")
                if token_client_id not in self.accepted_client_ids:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token from unauthorized client"
                    )

            # Get user groups
            user_groups = payload.get("cognito:groups", [])

            # Check required groups if specified
            if self.required_groups:
                if not any(group in user_groups for group in self.required_groups):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"User must be in one of these groups: {', '.join(self.required_groups)}"
                    )

            # Create CognitoUser instance
            user = CognitoUser.from_cognito_payload(payload)

            # Check required groups if specified
            if self.required_groups and not any(group in user.groups for group in self.required_groups):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"User must be in one of these groups: {', '.join(self.required_groups)}"
                )

            return user

        except jwt.ExpiredSignatureError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            ) from e
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {str(e)}"
            ) from e


class SlackJWTVerifier:
    """
    A class to verify Slack JWT tokens for specific applications and tasks.
    """
    def __init__(self, key_filename, desired_app, desired_task):
        self.key_filename = key_filename
        self.desired_app = desired_app
        self.desired_task = desired_task

    def __call__(self, authorization_token: str):
        return self.verify_slack_jwt_token(
            authorization_token,
            key_filename=self.key_filename,
            desired_app=self.desired_app,
            desired_task=self.desired_task
        )

    @staticmethod
    def verify_slack_jwt_token(
        authorization_token: str,
        key_filename: str,
        desired_app: str,
        desired_task: str
    ):
        """
        Verify a Slack JWT token against a public key.

        Args:
            authorization_token (str): The JWT token to verify.
            key_filename (str): Path to the public key file.
            desired_app (str): Expected application name in the JWT payload.
            desired_task (str): Expected task name in the JWT payload.

        Returns:
            dict: Decoded JWT payload if verification is successful.

        Raises:
            HTTPException: If verification fails.
        """
        # Read in the public key
        try:
            with open(key_filename, "rb") as fptr:
                key = fptr.read()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Bad public key filename: {exc}") from exc

        # Decode the token and check for validity
        try:
            decoded = jwt.decode(authorization_token, key, algorithms=["RS256"])
        except Exception as exc:
            raise HTTPException(status_code=401, detail=f"Invalid JSON Web Token: {exc}") from exc

        # Check to see if the JWT payload is valid
        if decoded.get("app") != desired_app:
            raise HTTPException(status_code=401, detail="Invalid app in JSON Web Token payload")
        if decoded.get("task") != desired_task:
            raise HTTPException(status_code=401, detail="Invalid task in JSON Web Token payload")

        return decoded
