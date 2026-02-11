"""
AWS S3 storage backend.

Requires: pip install boto3

Set these env vars:
  S3_BUCKET=my-bucket-name
  S3_REGION=us-east-1
  S3_PREFIX=ats-resume-app/     (optional key prefix)
  AWS_ACCESS_KEY_ID=...
  AWS_SECRET_ACCESS_KEY=...

Or use IAM roles / instance profiles (recommended in production).
"""

import time
from typing import List, Optional

from .base import StorageBackend, StorageFile

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class S3Storage(StorageBackend):
    """Store files in AWS S3 (or any S3-compatible service)."""

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        prefix: str = "",
        endpoint_url: Optional[str] = None,
    ):
        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for S3 storage. Install with: pip install boto3"
            )

        self.bucket = bucket
        self.prefix = prefix.rstrip("/") + "/" if prefix else ""
        self.region = region

        session = boto3.Session()
        self._s3 = session.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
        )

    def _full_key(self, key: str) -> str:
        """Prepend the prefix to the key."""
        return f"{self.prefix}{key}"

    def save(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        full_key = self._full_key(key)
        self._s3.put_object(
            Bucket=self.bucket,
            Key=full_key,
            Body=data,
            ContentType=content_type,
        )
        return f"s3://{self.bucket}/{full_key}"

    def read(self, key: str) -> Optional[bytes]:
        try:
            response = self._s3.get_object(Bucket=self.bucket, Key=self._full_key(key))
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise

    def delete(self, key: str) -> bool:
        try:
            self._s3.delete_object(Bucket=self.bucket, Key=self._full_key(key))
            return True
        except ClientError:
            return False

    def exists(self, key: str) -> bool:
        try:
            self._s3.head_object(Bucket=self.bucket, Key=self._full_key(key))
            return True
        except ClientError:
            return False

    def list_files(self, prefix: str = "") -> List[StorageFile]:
        full_prefix = self._full_key(prefix)
        files = []

        paginator = self._s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=full_prefix):
            for obj in page.get("Contents", []):
                # Strip the prefix to get relative key
                relative_key = obj["Key"]
                if self.prefix and relative_key.startswith(self.prefix):
                    relative_key = relative_key[len(self.prefix):]

                files.append(StorageFile(
                    key=relative_key,
                    size=obj["Size"],
                    last_modified=obj["LastModified"].timestamp(),
                    content_type=self._guess_content_type(relative_key),
                ))

        return sorted(files, key=lambda f: f.last_modified, reverse=True)

    def get_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """Generate a pre-signed URL for temporary access."""
        try:
            url = self._s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": self._full_key(key)},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError:
            return None

    def get_path(self, key: str) -> Optional[str]:
        """S3 doesn't have local paths — return None."""
        return None

    @staticmethod
    def _guess_content_type(key: str) -> str:
        """Guess MIME type from key extension."""
        ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
        types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "txt": "text/plain",
            "json": "application/json",
        }
        return types.get(ext, "application/octet-stream")
