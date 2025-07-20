import io
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import StreamingResponse
from app.adapters.s3_adapter import S3Adapter
from app.utils.dependencies import get_s3_adapter

router = APIRouter()

@router.post("/upload")
async def upload_file(
    bucket_name: str,
    object_name: str,
    file: UploadFile = File(...),
    s3_adapter: S3Adapter = Depends(get_s3_adapter)
):
    """
    Upload a file to S3.\n
    :param bucket_name: The name of the S3 bucket.\n
    :param object_name: The name of the object in S3.\n
    :param file: The file to upload.\n
    :return: A message indicating success or failure.
    """
    try:
        s3_adapter.upload(bucket_name, object_name, fileobj=file.file)
        return {"message": "File uploaded successfully"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/download")
async def download_file(
    bucket_name: str,
    object_name: str,
    s3_adapter: S3Adapter = Depends(get_s3_adapter)
):
    """
    Download a file from S3.\n
    :param bucket_name: The name of the S3 bucket.\n
    :param object_name: The name of the object in S3.\n
    :return: A StreamingResponse to download the file.
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
