from unittest.mock import MagicMock, patch
from app.adapters.s3_adapter import S3Adapter
import pytest


@pytest.fixture
def s3_adapter():
    adapter = S3Adapter.__new__(S3Adapter)
    adapter.client = MagicMock()
    return adapter


def test_when_filepath_given_then_uploads_file(s3_adapter):
    s3_adapter.upload("bucket", "obj", filepath="file.txt")
    s3_adapter.client.upload_file.assert_called_once_with("file.txt", "bucket", "obj")


def test_when_fileobj_given_then_uploads_fileobj(s3_adapter):
    fileobj = MagicMock()
    s3_adapter.upload("bucket", "obj", fileobj=fileobj)
    s3_adapter.client.upload_fileobj.assert_called_once_with(fileobj, "bucket", "obj")


def test_when_no_or_both_file_sources_then_raises_value_error(s3_adapter):
    with pytest.raises(ValueError):
        s3_adapter.upload("bucket", "obj")
    with pytest.raises(ValueError):
        s3_adapter.upload("bucket", "obj", filepath="file.txt", fileobj=MagicMock())


def test_when_destination_given_then_downloads_to_file(s3_adapter):
    s3_adapter.download("bucket", "obj", destination="dest.txt")
    s3_adapter.client.download_file.assert_called_once_with("bucket", "obj", "dest.txt")


def test_when_no_destination_then_downloads_to_bytes(s3_adapter):
    mock_body = MagicMock()
    mock_body.read.return_value = b"data"
    s3_adapter.client.get_object.return_value = {"Body": mock_body}
    result = s3_adapter.download("bucket", "obj")
    s3_adapter.client.get_object.assert_called_once_with(Bucket="bucket", Key="obj")
    assert result == b"data"


def test_when_delete_called_then_deletes_object(s3_adapter):
    s3_adapter.delete("bucket", "obj")
    s3_adapter.client.delete_object.assert_called_once_with(Bucket="bucket", Key="obj")


def test_when_copy_called_then_copies_object(s3_adapter):
    s3_adapter.copy("bucket", "src", "dest")
    s3_adapter.client.copy.assert_called_once_with({'Bucket': 'bucket', 'Key': 'src'}, "bucket", "dest")


def test_when_move_called_then_copies_and_deletes_object(s3_adapter):
    s3_adapter.move("bucket", "src", "dest")
    s3_adapter.client.copy.assert_called_once_with({'Bucket': 'bucket', 'Key': 'src'}, "bucket", "dest")
    s3_adapter.client.delete_object.assert_called_once_with(Bucket="bucket", Key="src")


@patch("app.adapters.s3_adapter.boto3.client")
def test_when_init_success_then_client_created(mock_boto):
    mock_boto.return_value = MagicMock()
    adapter = S3Adapter("ak", "sk", "region")
    assert adapter.client == mock_boto.return_value


@patch("app.adapters.s3_adapter.boto3.client", side_effect=Exception("fail"))
def test_when_init_failure_then_raises_exception(mock_boto):
    with pytest.raises(Exception):
        S3Adapter("ak", "sk", "region")
