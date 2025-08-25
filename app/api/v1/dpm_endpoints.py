import io
import os
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Security
from fastapi.responses import StreamingResponse
from app.models.schemas import User, UserCreate
from app.adapters.rds_adapter import RDSAdapter
from app.adapters.s3_adapter import S3Adapter
from app.utils.dependencies import get_rds_adapter, get_s3_adapter, get_dpm_token_verifier
from app.utils.auth import DPMTokenVerifier, api_key_header  # import api_key_header

router = APIRouter()

@router.post("/upload")
async def upload_file(
    bucket_name: str,
    object_name: str,
    file: UploadFile = File(...),
    s3_adapter: S3Adapter = Depends(get_s3_adapter),
    token_verifier: DPMTokenVerifier = Depends(get_dpm_token_verifier),
    api_key: str = Security(api_key_header),  # get raw token string here
):
    """
    Upload a file to S3.

    Args:
        bucket_name (str): The name of the S3 bucket.
        object_name (str): The name of the object in S3.
        file (UploadFile): The file to upload.
        token_verifier (DPMTokenVerifier): The token verifier instance (dependency injected).

    Returns:
        dict: Success message or raises HTTPException on failure.
    """
    # Explicitly verify token
    await token_verifier.verify(api_key)

    try:
        s3_adapter.upload(bucket_name, object_name, fileobj=file.file)
        return {"message": "File uploaded successfully"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/download")
async def download_file(
    bucket_name: str,
    object_name: str,
    s3_adapter: S3Adapter = Depends(get_s3_adapter),
    token_verifier: DPMTokenVerifier = Depends(get_dpm_token_verifier),
    api_key: str = Security(api_key_header),  # get raw token string here too
):
    """
    Download a file from S3.

    Args:
        bucket_name (str): The name of the S3 bucket.
        object_name (str): The name of the object in S3.
        token_verifier (DPMTokenVerifier): The token verifier instance (dependency injected).

    Returns:
        StreamingResponse: A streaming response to download the file.

    Raises:
        HTTPException: For file not found or internal server errors.
    """
    # Explicitly verify token
    await token_verifier.verify(api_key)

    try:
        file_content = s3_adapter.download(bucket_name, object_name)
        if not file_content:
            raise HTTPException(status_code=404, detail="File not found or empty")
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={object_name}"}
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/list", response_model = List[str])
async def list_files(
    bucket_name: str,
    prefix: str = "",  # Optional folder path
    s3_adapter: S3Adapter = Depends(get_s3_adapter),
    token_verifier: DPMTokenVerifier = Depends(get_dpm_token_verifier),
    api_key: str = Security(api_key_header),
):
    """
    List all filenames in a specified S3 bucket folder.

    Args:
        bucket_name (str): The name of the S3 bucket.
        folder (str, optional): The folder path inside the bucket. Defaults to root ("").
        token_verifier (DPMTokenVerifier): The token verifier instance (dependency injected).

    Returns:
        List[str]: A list of filenames in the specified folder.
    """
    await token_verifier.verify(api_key)

    try:
        files = s3_adapter.list_files(bucket_name=bucket_name, prefix=prefix)
        return files
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/user/{id}")
async def get_user_data(
    id: int,
    rds_adapter: RDSAdapter = Depends(get_rds_adapter(
        db_host=os.getenv("RDS_DPM_HOST"),
        db_name=os.getenv("RDS_DPM_NAME"),
        db_user=os.getenv("RDS_DPM_USER"),
        db_password= os.getenv("RDS_DPM_PASS")
    )),
    token_verifier: DPMTokenVerifier = Depends(get_dpm_token_verifier),
    api_key: str = Security(api_key_header),
):
    """
    Get user data from the database.
    :param id: The ID of the user to retrieve.
    :return: A dictionary containing user data.
    """
    await token_verifier.verify(api_key)
    assert isinstance(id, int), "ID must be an integer"

    users, column_names, _ = rds_adapter.select(table_name='users', where="user_id = %s", where_params=(id,))
    if not users:
        raise HTTPException(status_code=404, detail="User not found")
    user_obj = {}
    for col, val in zip(column_names, users[0]):
        user_obj[col] = val
    return user_obj


@router.post("/user")
async def create_user(
    user: UserCreate,
    rds_adapter: RDSAdapter = Depends(get_rds_adapter(
        db_host=os.getenv("RDS_DPM_HOST"),
        db_name=os.getenv("RDS_DPM_NAME"),
        db_user=os.getenv("RDS_DPM_USER"),
        db_password=os.getenv("RDS_DPM_PASS")
    )),
    token_verifier: DPMTokenVerifier = Depends(get_dpm_token_verifier),
    api_key: str = Security(api_key_header),
):
    """
    Create a new user in the database.
    :param user: The user data to create.
    :return: A dictionary containing the created user data.
    """
    await token_verifier.verify(api_key)
    new_users = rds_adapter.insert(
        table='public.users (user_firstname, user_lastname, user_email, user_country, user_language, user_role)',
        values=(
            user.user_firstname,
            user.user_lastname,
            user.user_email,
            user.user_country,
            user.user_language,
            user.user_role
        )
    )
    if not new_users or len(new_users) != 1:
        raise HTTPException(status_code=500, detail="Failed to create user")
    new_user_obj = new_users[0]
    new_user = User(
        user_id=new_user_obj[0],
        user_firstname=new_user_obj[1],
        user_lastname=new_user_obj[2],
        user_email=new_user_obj[3],
        user_country=new_user_obj[4],
        user_language=new_user_obj[5],
        user_role=new_user_obj[6]
    )
    return new_user


@router.delete("/user/{id}")
async def delete_user(
    id: int,
    rds_adapter: RDSAdapter = Depends(get_rds_adapter(
        db_host=os.getenv("RDS_DPM_HOST"),
        db_name=os.getenv("RDS_DPM_NAME"),
        db_user=os.getenv("RDS_DPM_USER"),
        db_password=os.getenv("RDS_DPM_PASS")
    )),
    token_verifier: DPMTokenVerifier = Depends(get_dpm_token_verifier),
    api_key: str = Security(api_key_header),
):
    """
    Delete user from the database.
    :return: A success message.
    """
    await token_verifier.verify(api_key)
    assert isinstance(id, int), "ID must be an integer"
    rds_adapter.execute("DELETE FROM public.users WHERE user_id = %s", (id,))
    return {"message": "User deleted successfully"}
