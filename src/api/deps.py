"""
Shared API dependencies: in-memory caches and session stores.

These are module-level singletons shared across all route handlers.
"""

from ..models import ResumeData, ATSAnalysisResult, ResumeVersion

# ── In-memory storage (session-based) ──
resume_data_cache: dict[str, ResumeData] = {}
resume_versions: dict[str, list[ResumeVersion]] = {}  # session_id → versions
analysis_cache: dict[str, ATSAnalysisResult] = {}       # session_id:jd_hash → analysis
