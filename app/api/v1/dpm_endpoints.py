import io
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import StreamingResponse
from app.adapters.s3_adapter import S3Adapter
from app.utils.dependencies import get_s3_adapter, get_dpm_token_verifier
from app.utils.auth import DPMTokenVerifier

router = APIRouter()

@router.post("/upload")
async def upload_file(
    bucket_name: str,
    object_name: str,
    file: UploadFile = File(...),
    s3_adapter: S3Adapter = Depends(get_s3_adapter),
    token: DPMTokenVerifier = Depends(get_dpm_token_verifier),
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
    # Call the token verifier to check token validity (raises HTTPException on failure)

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
    token: DPMTokenVerifier = Depends(get_dpm_token_verifier),  # Note: calling the factory here
):
    """
    Download a file from S3.

    Args:
        bucket_name (str): The name of the S3 bucket.
        object_name (str): The name of the object in S3.
        token (str): Verified token string (injected for auth purposes).

    Returns:
        StreamingResponse: A streaming response to download the file.

    Raises:
        HTTPException: For file not found or internal server errors.
    """
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