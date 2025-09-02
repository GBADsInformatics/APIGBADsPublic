import os
from typing import Callable
from app.adapters.s3_adapter import S3Adapter
from app.adapters.rds_adapter import RDSAdapter


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
