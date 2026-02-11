"""
Shared API dependencies: session stores with Supabase persistence.

In-memory dicts are the fast path. On cache miss, we fall back to Supabase.
On write, data is saved to both memory AND Supabase so it survives restarts.
"""

import time
from typing import Optional

from ..models import ResumeData, ATSAnalysisResult, ResumeVersion
from ..logger import logger


# ── In-memory caches (fast path) ──
resume_data_cache: dict[str, ResumeData] = {}
resume_versions: dict[str, list[ResumeVersion]] = {}  # session_id → versions
analysis_cache: dict[str, ATSAnalysisResult] = {}       # session_id:jd_hash → analysis
session_timestamps: dict[str, float] = {}                # session_id → creation epoch


def register_session(session_id: str) -> None:
    """Record creation time for a session."""
    session_timestamps[session_id] = time.time()


# ═══════════════════════════════════════════════════════════
# Persistent resume data (memory + Supabase)
# ═══════════════════════════════════════════════════════════

def save_resume_data(session_id: str, data: ResumeData) -> None:
    """Save parsed resume data to memory AND Supabase."""
    resume_data_cache[session_id] = data
    register_session(session_id)

    try:
        from ..db import update_session_resume_data, is_db_enabled
        if is_db_enabled():
            update_session_resume_data(session_id, data.model_dump())
    except Exception as exc:
        logger.debug("Failed to persist resume_data to DB: %s", exc)


def get_resume_data(session_id: str) -> Optional[ResumeData]:
    """
    Get parsed resume data — checks memory first, then Supabase.
    If found in Supabase, re-hydrates the in-memory cache.
    """
    # Fast path: in-memory
    if session_id in resume_data_cache:
        return resume_data_cache[session_id]

    # Slow path: Supabase
    try:
        from ..db import get_session, touch_session, is_db_enabled
        if not is_db_enabled():
            return None

        row = get_session(session_id)
        if row and row.get("resume_data") and row["resume_data"] != {}:
            data = ResumeData(**row["resume_data"])
            # Re-hydrate memory cache
            resume_data_cache[session_id] = data
            session_timestamps[session_id] = time.time()
            # Update last_accessed_at
            touch_session(session_id)
            logger.info("Restored session %s from Supabase", session_id)
            return data
    except Exception as exc:
        logger.debug("Failed to load resume_data from DB for %s: %s", session_id, exc)

    return None


# ═══════════════════════════════════════════════════════════
# Persistent analysis data (memory + Supabase)
# ═══════════════════════════════════════════════════════════

def save_analysis_data(session_id: str, cache_key: str, analysis: ATSAnalysisResult) -> None:
    """Save ATS analysis to memory AND Supabase."""
    analysis_cache[cache_key] = analysis

    try:
        from ..db import update_session_analysis, is_db_enabled
        if is_db_enabled():
            update_session_analysis(session_id, analysis.model_dump())
    except Exception as exc:
        logger.debug("Failed to persist analysis to DB: %s", exc)


def get_analysis_data(session_id: str, cache_key: str) -> Optional[ATSAnalysisResult]:
    """
    Get ATS analysis — checks memory first, then Supabase.
    """
    # Fast path: in-memory
    if cache_key in analysis_cache:
        return analysis_cache[cache_key]

    # Slow path: Supabase
    try:
        from ..db import get_session, is_db_enabled
        if not is_db_enabled():
            return None

        row = get_session(session_id)
        if row and row.get("analysis_data"):
            analysis = ATSAnalysisResult(**row["analysis_data"])
            # Re-hydrate memory cache
            analysis_cache[cache_key] = analysis
            logger.info("Restored analysis for session %s from Supabase", session_id)
            return analysis
    except Exception as exc:
        logger.debug("Failed to load analysis from DB for %s: %s", session_id, exc)

    return None


def has_session(session_id: str) -> bool:
    """Check if a session exists (memory or Supabase)."""
    if session_id in resume_data_cache:
        return True

    # Try loading from Supabase (will re-hydrate cache if found)
    data = get_resume_data(session_id)
    return data is not None
