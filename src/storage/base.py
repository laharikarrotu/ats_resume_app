"""
Abstract storage backend interface.

All storage implementations (local, S3, GCS, etc.) must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class StorageFile:
    """Metadata for a stored file."""
    key: str
    size: int
    last_modified: float  # Unix timestamp
    content_type: str = "application/octet-stream"


class StorageBackend(ABC):
    """Abstract base class for file storage backends."""

    @abstractmethod
    def save(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """
        Save data to storage.

        Args:
            key: Storage key / path (e.g., "outputs/resume_abc.docx")
            data: File contents as bytes
            content_type: MIME type

        Returns:
            Full path or URL to the saved file
        """
        ...

    @abstractmethod
    def read(self, key: str) -> Optional[bytes]:
        """
        Read data from storage.

        Args:
            key: Storage key / path

        Returns:
            File contents as bytes, or None if not found
        """
        ...

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete a file from storage.

        Args:
            key: Storage key / path

        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a file exists in storage."""
        ...

    @abstractmethod
    def list_files(self, prefix: str = "") -> List[StorageFile]:
        """
        List files matching a prefix.

        Args:
            prefix: Key prefix to filter by (e.g., "outputs/")

        Returns:
            List of StorageFile metadata objects
        """
        ...

    @abstractmethod
    def get_url(self, key: str) -> Optional[str]:
        """
        Get a public or signed URL for a file.

        Args:
            key: Storage key / path

        Returns:
            URL string, or None if not applicable
        """
        ...

    @abstractmethod
    def get_path(self, key: str) -> Optional[str]:
        """
        Get the local filesystem path (only for local storage).

        Args:
            key: Storage key / path

        Returns:
            Filesystem path, or None for remote storage
        """
        ...
