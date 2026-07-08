import os
import tempfile
from unittest.mock import patch, MagicMock
from moto import mock_aws
from mpips.storage import get_s3_client, download_image, upload_image


@mock_aws
def test_s3_direct_upload_and_download() -> None:
    # Set up mocked env vars
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["AWS_BUCKET"] = "madeena-media"
    os.environ.pop("AWS_ENDPOINT_URL", None)

    s3 = get_s3_client()
    s3.create_bucket(Bucket="madeena-media")

    with tempfile.TemporaryDirectory() as tmpdir:
        local_src = os.path.join(tmpdir, "src.png")
        local_dest = os.path.join(tmpdir, "dest.png")

        content = b"fake-image-bytes"
        with open(local_src, "wb") as f:
            f.write(content)

        # Test upload_image (direct S3 key)
        upload_image(local_src, "tenant1/media/test_image.png")

        # Verify it exists in mocked S3
        resp = s3.get_object(Bucket="madeena-media", Key="tenant1/media/test_image.png")
        assert resp["Body"].read() == content
        assert resp["ContentType"] == "image/png"

        # Test download_image (direct S3 key)
        download_image("tenant1/media/test_image.png", local_dest)

        with open(local_dest, "rb") as f:
            downloaded_content = f.read()
        assert downloaded_content == content


def test_download_image_from_presigned_url() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_bytes.return_value = [b"chunk1", b"chunk2"]

    with patch("httpx.stream") as mock_stream:
        mock_stream.return_value.__enter__.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            local_dest = os.path.join(tmpdir, "dest.png")
            download_image(
                "https://presigned-read-url.com", local_dest, is_presigned_url=True
            )

            with open(local_dest, "rb") as f:
                downloaded_content = f.read()
            assert downloaded_content == b"chunk1chunk2"

        mock_stream.assert_called_once_with(
            "GET", "https://presigned-read-url.com", follow_redirects=True
        )


def test_upload_image_to_presigned_url() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("httpx.put") as mock_put:
        mock_put.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            local_src = os.path.join(tmpdir, "src.png")
            with open(local_src, "wb") as f:
                f.write(b"data-to-upload")

            upload_image(
                local_src,
                "https://presigned-write-url.com",
                is_presigned_url=True,
                mime_type="image/png",
            )

        mock_put.assert_called_once()
        args, kwargs = mock_put.call_args
        assert args[0] == "https://presigned-write-url.com"
        assert kwargs["headers"] == {"Content-Type": "image/png"}
