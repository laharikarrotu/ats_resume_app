"""
File & session cleanup — automatically removes stale files and expired sessions.

Runs as an asyncio background task started on app startup.
"""

import asyncio
import time
from pathlib import Path

from .config import OUTPUT_DIR, UPLOAD_DIR
from .logger import logger


# ── Configuration ──
CLEANUP_INTERVAL_SECONDS = 3600      # Check every 1 hour
FILE_MAX_AGE_SECONDS = 24 * 3600     # Delete files older than 24 hours
SESSION_MAX_AGE_SECONDS = 24 * 3600  # Expire sessions after 24 hours


def _cleanup_old_files(directory: Path, max_age_seconds: int) -> int:
    """Delete files older than max_age_seconds in the given directory."""
    if not directory.exists():
        return 0

    now = time.time()
    deleted = 0
    for f in directory.iterdir():
        if f.is_file():
            age = now - f.stat().st_mtime
            if age > max_age_seconds:
                try:
                    f.unlink()
                    deleted += 1
                except OSError as e:
                    logger.warning("Failed to delete %s: %s", f, e)
    return deleted


def _cleanup_expired_sessions(max_age_seconds: int) -> int:
    """Remove expired sessions from in-memory caches."""
    from .api.deps import resume_data_cache, resume_versions, analysis_cache, session_timestamps

    now = time.time()
    expired = []

    for session_id, created_at in list(session_timestamps.items()):
        if now - created_at > max_age_seconds:
            expired.append(session_id)

    for session_id in expired:
        resume_data_cache.pop(session_id, None)
        resume_versions.pop(session_id, None)
        session_timestamps.pop(session_id, None)
        # Clean analysis cache entries for this session
        keys_to_remove = [k for k in analysis_cache if k.startswith(session_id)]
        for k in keys_to_remove:
            analysis_cache.pop(k, None)

    return len(expired)


async def cleanup_loop() -> None:
    """Background loop that runs periodic cleanup."""
    logger.info(
        "🧹 Cleanup task started — files older than %dh, sessions older than %dh, checking every %dm",
        FILE_MAX_AGE_SECONDS // 3600,
        SESSION_MAX_AGE_SECONDS // 3600,
        CLEANUP_INTERVAL_SECONDS // 60,
    )

    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        try:
            output_deleted = _cleanup_old_files(OUTPUT_DIR, FILE_MAX_AGE_SECONDS)
            upload_deleted = _cleanup_old_files(UPLOAD_DIR, FILE_MAX_AGE_SECONDS)
            sessions_expired = _cleanup_expired_sessions(SESSION_MAX_AGE_SECONDS)

            if output_deleted or upload_deleted or sessions_expired:
                logger.info(
                    "🧹 Cleanup: %d output files, %d upload files deleted; %d sessions expired",
                    output_deleted,
                    upload_deleted,
                    sessions_expired,
                )
        except Exception as e:
            logger.error("Cleanup task error: %s", e, exc_info=True)
