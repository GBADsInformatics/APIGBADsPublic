import logging
from typing import Union, Optional
from io import BinaryIO
import boto3


logging.basicConfig(level=logging.INFO, format='%(levelname)s:\t%(name)s: %(message)s')
logger = logging.getLogger(__name__)


class S3Adapter:
    """
    A class to interact with AWS S3 using boto3.
    This class provides methods to upload, download, delete, and manage files in S3 buckets.
    """

    def __init__(self, access_key: str, secret_key: str, region: str):
        try:
            self.client = boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
        except Exception as exc:
            logging.error("Error initializing S3 client: %s", exc)
            raise

    def upload(self, bucket: str, object_name: str, filepath: str = None, fileobj: Optional[BinaryIO] = None) -> None:
        """
        Upload a file to an S3 bucket.
        :param bucket: S3 bucket name
        :param object_name: S3 object key
        :param filepath: Local file path to upload
        :param fileobj: File-like object to upload
        :raises ValueError: If neither or both of filepath and fileobj are provided
        :return: None
        """
        if (fileobj is None) == (filepath is None):
            raise ValueError("Provide exactly one of 'filepath' or 'fileobj'")
        if fileobj:
            self.client.upload_fileobj(fileobj, bucket, object_name)
        else:
            self.client.upload_file(filepath, bucket, object_name)
        logging.info("File %s uploaded to %s", object_name, bucket)

    def download(self, bucket: str, object_name: str, destination: Optional[str] = None) -> Union[str, bytes]:
        """
        Download a file from an S3 bucket.
        :param bucket: S3 bucket name
        :param object_name: S3 object key
        :param destination: Local file path to save the downloaded file, or None to directly return bytes
        :return: Local file path if destination is provided, or bytes of the file if file wasn't saved locally
        """
        if destination is None:
            obj = self.client.get_object(Bucket=bucket, Key=object_name)
            return obj['Body'].read()
        self.client.download_file(bucket, object_name, destination)
        return destination

    def delete(self, bucket: str, object_name: str) -> None:
        """
        Delete a file from an S3 bucket.
        :param bucket: S3 bucket name
        :param object_name: S3 object key
        :return: None
        """
        self.client.delete_object(Bucket=bucket, Key=object_name)
        logging.info("File %s deleted from %s", object_name, bucket)

    def copy(self, bucket: str, source_object_name: str, destination_object_name: str) -> None:
        """
        Copy a file within an S3 bucket.
        :param bucket: S3 bucket name
        :param source_object_name: Source S3 object key
        :param destination_object_name: Destination S3 object key
        :return: None
        """
        copy_source = {'Bucket': bucket, 'Key': source_object_name}
        self.client.copy(copy_source, bucket, destination_object_name)
        logging.info("File %s copied to %s in %s", source_object_name, destination_object_name, bucket)

    def move(self, bucket: str, source_object_name: str, destination_object_name: str) -> None:
        """
        Move a file within an S3 bucket.
        :param bucket: S3 bucket name
        :param source_object_name: Source S3 object key
        :param destination_object_name: Destination S3 object key
        :return: None
        """
        copy_source = {'Bucket': bucket, 'Key': source_object_name}
        self.client.copy(copy_source, bucket, destination_object_name)
        self.client.delete_object(Bucket=bucket, Key=source_object_name)
        logging.info("File %s moved to %s in %s", source_object_name, destination_object_name, bucket)
