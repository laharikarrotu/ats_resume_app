"""
Local filesystem storage backend.

Stores files on the local disk. This is the default backend.
"""

import os
import time
from pathlib import Path
from typing import List, Optional

from .base import StorageBackend, StorageFile


class LocalStorage(StorageBackend):
    """Store files on the local filesystem."""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        """Resolve a key to an absolute path (prevent path traversal)."""
        resolved = (self.base_dir / key).resolve()
        if not str(resolved).startswith(str(self.base_dir.resolve())):
            raise ValueError(f"Path traversal detected: {key}")
        return resolved

    def save(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def read(self, key: str) -> Optional[bytes]:
        path = self._resolve(key)
        if path.exists() and path.is_file():
            return path.read_bytes()
        return None

    def delete(self, key: str) -> bool:
        path = self._resolve(key)
        if path.exists() and path.is_file():
            path.unlink()
            return True
        return False

    def exists(self, key: str) -> bool:
        path = self._resolve(key)
        return path.exists() and path.is_file()

    def list_files(self, prefix: str = "") -> List[StorageFile]:
        search_dir = self._resolve(prefix) if prefix else self.base_dir
        if not search_dir.exists():
            return []

        files = []
        base_resolved = self.base_dir.resolve()

        iterator = search_dir.rglob("*") if search_dir.is_dir() else [search_dir]
        for path in iterator:
            if path.is_file():
                stat = path.stat()
                relative_key = str(path.resolve().relative_to(base_resolved))
                content_type = self._guess_content_type(path.suffix)
                files.append(StorageFile(
                    key=relative_key,
                    size=stat.st_size,
                    last_modified=stat.st_mtime,
                    content_type=content_type,
                ))

        return sorted(files, key=lambda f: f.last_modified, reverse=True)

    def get_url(self, key: str) -> Optional[str]:
        """Local storage doesn't have URLs — return file:// path."""
        path = self._resolve(key)
        if path.exists():
            return f"file://{path}"
        return None

    def get_path(self, key: str) -> Optional[str]:
        """Return the local filesystem path."""
        path = self._resolve(key)
        if path.exists():
            return str(path)
        return None

    @staticmethod
    def _guess_content_type(suffix: str) -> str:
        """Guess MIME type from file extension."""
        types = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".txt": "text/plain",
            ".json": "application/json",
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml",
        }
        return types.get(suffix.lower(), "application/octet-stream")
