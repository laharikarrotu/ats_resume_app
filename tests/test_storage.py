"""Tests for the storage abstraction layer."""

import pytest
from src.storage.local import LocalStorage


@pytest.fixture()
def storage(tmp_dir):
    """Local storage backed by a temp directory."""
    return LocalStorage(base_dir=str(tmp_dir))


class TestLocalStorage:
    def test_save_and_read(self, storage):
        content = b"Hello, World!"
        path = storage.save("test/hello.txt", content, "text/plain")
        assert path.endswith("hello.txt")

        data = storage.read("test/hello.txt")
        assert data == content

    def test_exists(self, storage):
        assert storage.exists("nonexistent.txt") is False
        storage.save("exists.txt", b"data")
        assert storage.exists("exists.txt") is True

    def test_delete(self, storage):
        storage.save("deleteme.txt", b"data")
        assert storage.exists("deleteme.txt") is True
        assert storage.delete("deleteme.txt") is True
        assert storage.exists("deleteme.txt") is False

    def test_delete_nonexistent(self, storage):
        assert storage.delete("nope.txt") is False

    def test_read_nonexistent(self, storage):
        assert storage.read("nope.txt") is None

    def test_list_files(self, storage):
        storage.save("a.txt", b"aaa")
        storage.save("b.txt", b"bbb")
        storage.save("sub/c.txt", b"ccc")

        files = storage.list_files()
        assert len(files) == 3
        keys = {f.key for f in files}
        assert "a.txt" in keys
        assert "b.txt" in keys

    def test_list_files_with_prefix(self, storage):
        storage.save("docs/a.txt", b"aaa")
        storage.save("docs/b.txt", b"bbb")
        storage.save("other/c.txt", b"ccc")

        files = storage.list_files("docs")
        assert len(files) == 2

    def test_list_empty(self, storage):
        files = storage.list_files()
        assert files == []

    def test_get_path(self, storage):
        storage.save("test.txt", b"data")
        path = storage.get_path("test.txt")
        assert path is not None
        assert path.endswith("test.txt")

    def test_get_url(self, storage):
        storage.save("test.txt", b"data")
        url = storage.get_url("test.txt")
        assert url is not None
        assert url.startswith("file://")

    def test_path_traversal_prevention(self, storage):
        with pytest.raises(ValueError, match="Path traversal"):
            storage.save("../../etc/passwd", b"hack")

    def test_content_type_guessing(self):
        assert LocalStorage._guess_content_type(".pdf") == "application/pdf"
        assert LocalStorage._guess_content_type(".docx").startswith("application/")
        assert LocalStorage._guess_content_type(".unknown") == "application/octet-stream"

    def test_overwrite(self, storage):
        storage.save("test.txt", b"version1")
        storage.save("test.txt", b"version2")
        assert storage.read("test.txt") == b"version2"

    def test_file_metadata(self, storage):
        storage.save("meta.txt", b"12345")
        files = storage.list_files()
        assert len(files) == 1
        assert files[0].size == 5
        assert files[0].last_modified > 0
