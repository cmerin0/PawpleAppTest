from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from mypy_boto3_s3 import S3Client

from app.core.config import settings


# MinIO is not AWS, so boto3 must use the configured local endpoint.
# Create one cached S3-compatible client for MinIO
@lru_cache
def get_object_storage_client() -> S3Client:
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint_url,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key.get_secret_value(),
        region_name=settings.minio_region,
        use_ssl=settings.minio_use_ssl,
        config=Config(
            signature_version="s3v4",
            s3={
                "addressing_style": "path",
            },
            retries={
                "mode": "standard",
                "max_attempts": 3,
            },
        ),
    )


# Fail clearly when MinIO is unavailable or the configured bucket is missing.
def verify_object_storage_bucket() -> None:
    client = get_object_storage_client()

    try:
        # This checks bucket access without listing or modifying any objects.
        client.head_bucket(Bucket=settings.minio_bucket)
    except (BotoCoreError, ClientError) as error:
        raise RuntimeError(
            "Object storage is unavailable or the configured bucket does not exist."
        ) from error
