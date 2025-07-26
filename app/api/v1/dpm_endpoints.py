import io
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Security
from fastapi.responses import StreamingResponse
from app.adapters.s3_adapter import S3Adapter
from app.utils.dependencies import get_s3_adapter, get_dpm_token_verifier
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

@router.get("/list", response_model=List[str])
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
