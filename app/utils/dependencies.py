import os
from typing import Callable
from fastapi import Depends, Header, HTTPException
from app.adapters.s3_adapter import S3Adapter
from app.adapters.rds_adapter import RDSAdapter
from app.utils.auth import DPMTokenVerifier

def verify_dpm_token(
    authorization: str = Header(..., alias="Authorization"),
    verifier: DPMTokenVerifier = Depends(DPMTokenVerifier),
):
    """
    Dependency that verifies the Bearer token from the Authorization header.

    Args:
        authorization (str): The value of the 'Authorization' HTTP header, 
                             expected in the format "Bearer <token>".
        verifier (DPMTokenVerifier): An instance of the token verifier class.

    Raises:
        HTTPException: 
            - 400 Bad Request if the Authorization header format is invalid.
            - 401 Unauthorized if the token verification fails.
    """
    try:
        scheme, token = authorization.strip().split(" ")
        if scheme.lower() != "bearer":
            raise ValueError("Authorization scheme is not Bearer")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Authorization header") from exc

    verifier.verify(token)

def get_s3_adapter() -> S3Adapter:
    """
    This function is used to inject the S3Adapter dependency into FastAPI endpoints.
    Returns: S3Adapter: An instance of S3Adapter.
    """
    access_key = os.getenv("S3_USER_ACCESS_KEY_ID")
    secret_key = os.getenv("S3_USER_SECRET_ACCESS_KEY")
    region = os.getenv("S3_USER_REGION")
    return S3Adapter(
        access_key=access_key,
        secret_key=secret_key,
        region=region
    )


def get_rds_adapter(db_host: str, db_name: str, db_user: str, db_password: str) -> Callable[[], RDSAdapter]:
    """
    This function is used to inject the RDSAdapter dependency into FastAPI endpoints.
    Returns: RDSAdapter: An instance of RDSAdapter.
    """
    def return_rds_adapter():
        """
        Returns an instance of RDSAdapter with the provided database connection parameters.
        """
        return RDSAdapter(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password
        )
    # Assuming RDSAdapter is defined similarly to S3Adapter
    return return_rds_adapter
