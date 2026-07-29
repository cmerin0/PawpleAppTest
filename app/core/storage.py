from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from mypy_boto3_s3 import S3Client

from app.core.config import settings


def _create_object_storage_client(endpoint_url: str) -> S3Client:
    """
    Build an S3-compatible client for a particular endpoint.

    The upload client and presigned-URL client use the same credentials,
    but they may use different network addresses.
    """
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key.get_secret_value(),
        region_name=settings.minio_region,
        use_ssl=settings.minio_use_ssl,
        config=Config(
            signature_version="s3v4",
            # Path-style URLs are broadly compatible with local MinIO.
            s3={"addressing_style": "path"},
            retries={
                "mode": "standard",
                "max_attempts": 3,
            },
        ),
    )


@lru_cache
def get_object_storage_client() -> S3Client:
    """
    Return the client used by the API for upload and deletion operations.

    This endpoint must be reachable from the API process or container.
    """
    return _create_object_storage_client(settings.minio_endpoint_url)


@lru_cache
def get_public_object_storage_client() -> S3Client:
    """
    Return a client configured with the browser-facing MinIO address.

    Generating a presigned URL includes this endpoint in the resulting URL.
    """
    return _create_object_storage_client(settings.minio_public_endpoint_url)


def verify_object_storage_bucket() -> None:
    """Confirm that the configured bucket exists and is accessible."""
    try:
        get_object_storage_client().head_bucket(
            Bucket=settings.minio_bucket,
        )
    except (BotoCoreError, ClientError) as error:
        raise RuntimeError(
            f"Object-storage bucket '{settings.minio_bucket}' is unavailable."
        ) from error
