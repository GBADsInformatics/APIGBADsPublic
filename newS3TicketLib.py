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
