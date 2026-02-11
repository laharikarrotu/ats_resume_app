"""Tests for file and session cleanup."""

import time
from pathlib import Path

import pytest
from src.cleanup import _cleanup_old_files, _cleanup_expired_sessions


class TestCleanupOldFiles:
    def test_deletes_old_files(self, tmp_dir):
        """Should delete files older than max age."""
        old_file = tmp_dir / "old.txt"
        old_file.write_text("old content")
        # Backdate the file modification time
        import os
        old_time = time.time() - 48 * 3600  # 48 hours ago
        os.utime(old_file, (old_time, old_time))

        deleted = _cleanup_old_files(tmp_dir, max_age_seconds=24 * 3600)
        assert deleted == 1
        assert not old_file.exists()

    def test_keeps_recent_files(self, tmp_dir):
        """Should keep files within max age."""
        recent_file = tmp_dir / "recent.txt"
        recent_file.write_text("recent content")

        deleted = _cleanup_old_files(tmp_dir, max_age_seconds=24 * 3600)
        assert deleted == 0
        assert recent_file.exists()

    def test_nonexistent_directory(self):
        """Should handle nonexistent directory gracefully."""
        deleted = _cleanup_old_files(Path("/nonexistent/path"), max_age_seconds=3600)
        assert deleted == 0

    def test_mixed_files(self, tmp_dir):
        """Should only delete old files, keep recent ones."""
        import os

        old_file = tmp_dir / "old.docx"
        old_file.write_text("old")
        old_time = time.time() - 48 * 3600
        os.utime(old_file, (old_time, old_time))

        new_file = tmp_dir / "new.docx"
        new_file.write_text("new")

        deleted = _cleanup_old_files(tmp_dir, max_age_seconds=24 * 3600)
        assert deleted == 1
        assert not old_file.exists()
        assert new_file.exists()


class TestCleanupExpiredSessions:
    def test_removes_expired(self):
        """Should remove sessions older than max age."""
        from src.api.deps import resume_data_cache, session_timestamps
        from src.models import ResumeData

        # Add an expired session
        session_id = "expired-test-session"
        resume_data_cache[session_id] = ResumeData(name="Test")
        session_timestamps[session_id] = time.time() - 48 * 3600  # 48h ago

        expired = _cleanup_expired_sessions(max_age_seconds=24 * 3600)
        assert expired >= 1
        assert session_id not in resume_data_cache
        assert session_id not in session_timestamps

    def test_keeps_recent(self):
        """Should keep sessions within max age."""
        from src.api.deps import resume_data_cache, session_timestamps
        from src.models import ResumeData

        session_id = "recent-test-session"
        resume_data_cache[session_id] = ResumeData(name="Test")
        session_timestamps[session_id] = time.time()

        expired = _cleanup_expired_sessions(max_age_seconds=24 * 3600)
        assert session_id in resume_data_cache

        # Cleanup
        resume_data_cache.pop(session_id, None)
        session_timestamps.pop(session_id, None)
