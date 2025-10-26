# app/utils/dependencies.py
import os
from typing import Callable
from app.adapters.s3_adapter import S3Adapter
from app.adapters.rds_adapter import RDSAdapter
from app.adapters.tail_adapter import TailAdapterInstance
from app.adapters.metadata_adapter import MetadataAdapter

# Initialize TailAdapter once when the API starts
TailAdapterInstance.initialize()


def get_s3_adapter() -> S3Adapter:
    """
    Injects the S3Adapter dependency into FastAPI endpoints.
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
    Injects the RDSAdapter dependency into FastAPI endpoints.
    """
    def return_rds_adapter():
        return RDSAdapter(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password
        )
    return return_rds_adapter


def get_tail_adapter():
    """
    Injects the initialized TailAdapter into FastAPI endpoints.
    """
    return TailAdapterInstance

def get_metadata_adapter():
    """
    Lazily injects the MetadataAdapter singleton into FastAPI endpoints.
    """
    uri = os.getenv("GRAPHDB_URI")
    user = os.getenv("GRAPHDB_USERNAME")
    password = os.getenv("GRAPHDB_PASSWORD")

    # Use MetadataAdapter's singleton pattern
    return MetadataAdapter.get_instance(uri=uri, user=user, password=password)
