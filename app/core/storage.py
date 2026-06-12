import os
from typing import Any
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import httpx


def get_s3_client() -> Any:
    """Instantiate and return an S3 client configured via env variables."""
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    aws_endpoint_url = os.getenv("AWS_ENDPOINT_URL")

    kwargs = {}
    if aws_endpoint_url:
        kwargs["endpoint_url"] = aws_endpoint_url

    return boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region,
        config=Config(signature_version="s3v4"),
        **kwargs,
    )


def download_image(
    source: str, local_path: str, is_presigned_url: bool = False
) -> None:
    """Downloads an image from either a pre-signed URL or an S3 key to a local path."""
    if (
        is_presigned_url
        or source.startswith("http://")
        or source.startswith("https://")
    ):
        with httpx.stream("GET", source, follow_redirects=True) as response:
            if response.status_code != 200:
                raise RuntimeError(
                    f"Failed to download image from URL. "
                    f"Status code: {response.status_code}"
                )
            with open(local_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
    else:
        s3 = get_s3_client()
        bucket = os.getenv("AWS_BUCKET", "madeena-media")
        try:
            s3.download_file(bucket, source, local_path)
        except ClientError as e:
            raise RuntimeError(f"Failed to download image from S3: {str(e)}")


def upload_image(
    local_path: str,
    target: str,
    is_presigned_url: bool = False,
    mime_type: str = "image/png",
) -> None:
    """Uploads an image from local path to pre-signed write URL or S3."""
    if (
        is_presigned_url
        or target.startswith("http://")
        or target.startswith("https://")
    ):
        with open(local_path, "rb") as f:
            response = httpx.put(target, content=f, headers={"Content-Type": mime_type})
            if response.status_code not in (200, 201, 204):
                raise RuntimeError(
                    f"Failed to upload image to URL. "
                    f"Status code: {response.status_code}, "
                    f"body: {response.text}"
                )
    else:
        s3 = get_s3_client()
        bucket = os.getenv("AWS_BUCKET", "madeena-media")
        try:
            s3.upload_file(
                local_path,
                bucket,
                target,
                ExtraArgs={"ContentType": mime_type},
            )
        except ClientError as e:
            raise RuntimeError(f"Failed to upload image to S3: {str(e)}")
