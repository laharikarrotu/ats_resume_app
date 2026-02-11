"""
File storage abstraction — swap between local filesystem and S3.

Usage:
    from src.storage import storage

    # Save a file
    storage.save("resumes/output.docx", file_bytes)

    # Read a file
    data = storage.read("resumes/output.docx")

    # Delete a file
    storage.delete("resumes/output.docx")

    # List files
    files = storage.list_files("resumes/")
"""

from .base import StorageBackend
from .local import LocalStorage

# Lazy import to avoid requiring boto3 when not using S3
_storage_instance = None


def get_storage() -> StorageBackend:
    """Get the configured storage backend (singleton)."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = _create_storage()
    return _storage_instance


def _create_storage() -> StorageBackend:
    """Create the appropriate storage backend based on config."""
    from ..config import settings

    s3_bucket = getattr(settings, "s3_bucket", "")
    if s3_bucket:
        try:
            from .s3 import S3Storage
            return S3Storage(
                bucket=s3_bucket,
                region=getattr(settings, "s3_region", "us-east-1"),
                prefix=getattr(settings, "s3_prefix", "ats-resume-app/"),
            )
        except ImportError:
            from ..logger import logger
            logger.warning("boto3 not installed — falling back to local storage")

    from ..config import OUTPUT_DIR
    return LocalStorage(base_dir=str(OUTPUT_DIR.parent))


# Convenience alias
storage = property(lambda self: get_storage())


# Re-export for type checking
__all__ = ["StorageBackend", "LocalStorage", "get_storage"]
