#!/usr/bin/env python3
#
#  S3 Functions
#
import boto3


#
#  Access AWS Credentials and establish session
#
def credentials_client(access, secret):
    aws_access_key_id = access
    aws_secret_access_key = secret
    try:
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name="ca-central-1",
        )
        s3_client = session.client("s3")
        return s3_client
    except Exception as e:
        # Cannot connect to S3 as client
        print(e)
        ret = -1
        return ret


def credentials_resource(access, secret):
    aws_access_key_id = access
    aws_secret_access_key = secret
    try:
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name="ca-central-1",
        )
        s3_resource = session.resource("s3")
        return s3_resource
    except Exception as e:
        # Cannot connect to S3 as client
        print(e)
        ret = -1
        return ret


# Copy an object from one folder to another in the same bucket
# sourceObj and destObj are in the format path/objectName
def s3Copy(s3_client, bucket, sourceObj, destObj):
    # response = s3_client.copy_object(
    #     Bucket=bucket,  # Destination bucket
    #     CopySource=bucket + "/" + sourceObj,  # /Bucket-name/path/objectName
    #     Key=destObj,  # Destination path/objectName
    # )
    ret = 0
    return ret


# Delete an object given bucket and path to object
def s3Delete(s3_client, bucket, objectPath):
    # response = s3_client.delete_object(Bucket=bucket, Key=objectPath)
    ret = 0
    return ret


# Upload an object (file) given bucket and source and destination paths
def s3Upload(s3_resource, bucket, source_path, destination_path):
    try:
        s3_resource.Bucket(bucket).upload_file(source_path, destination_path)
        ret = 0
        return ret
    except Exception as e:
        print(e)
        ret = -1
        return ret


# Download an object (file) given bucket and source and destination paths
def s3Download(s3_resource, bucket, source, destination_path):
    try:
        s3_resource.Bucket(bucket).download_file(source, destination_path)
        ret = 0
        return ret
    except Exception as e:
        print(e)
        ret = -1
        return ret


def upload_fileobj(s3_client, bucket, object_name, fileobj):
    """
    Upload a file-like object to S3.
    :param s3_client: boto3 S3 client
    :param bucket: S3 bucket name
    :param object_name: S3 object key
    :param fileobj: file-like object to upload
    :return: 0 on success, -1 on failure
    """
    try:
        s3_client.upload_fileobj(fileobj, bucket, object_name)
        return 0
    except Exception as e:
        print(e)
        return -1


def download_file(s3_client, bucket, object_name):
    """
    Download an object from S3 and return its bytes.
    :param s3_client: boto3 S3 client
    :param bucket: S3 bucket name
    :param object_name: S3 object key
    :return: bytes of the file, or None on failure
    """
    try:
        response = s3_client.get_object(Bucket=bucket, Key=object_name)
        return response
    except Exception as e:
        print(e)
        return None
