from fastapi import HTTPException
import jwt


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
