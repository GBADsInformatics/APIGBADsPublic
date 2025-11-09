from typing import List, Optional
from pydantic import BaseModel


class CognitoUser(BaseModel):
    """
    User schema for Cognito authentication responses.
    Handles both Cognito JWT user data and legacy DPM token authentication.
    """
    type: str  # "cognito" or "legacy"
    user_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    groups: List[str] = []
    client_id: Optional[str] = None
    valid: Optional[bool] = None  # Used for legacy token validation

    @classmethod
    def from_legacy_token(cls) -> "CognitoUser":
        """
        Create a CognitoUser instance for legacy DPM token authentication
        """
        return cls(
            type="legacy",
            valid=True,
            groups=["Admin"]  # Legacy tokens have full access
        )

    @classmethod
    def from_cognito_payload(cls, payload: dict) -> "CognitoUser":
        """
        Create a CognitoUser instance from a Cognito JWT payload
        """
        return cls(
            type="cognito",
            user_id=payload.get("sub"),
            username=payload.get("cognito:username") or payload.get("username"),
            email=payload.get("email"),
            groups=payload.get("cognito:groups", []),
            client_id=payload.get("client_id") or payload.get("aud")
        )
