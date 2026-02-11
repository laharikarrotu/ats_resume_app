"""
Supabase CRUD operations — persistent storage layer.

Every public function here is a no-op when Supabase is not configured,
so the rest of the app never needs to check is_db_enabled() itself.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..logger import logger
from .client import get_supabase


# ── Helpers ──────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_execute(table: str, operation: str, fn):
    """
    Execute a Supabase operation, swallowing errors so the main
    request is never blocked by a DB failure.
    """
    client = get_supabase()
    if client is None:
        return None
    try:
        return fn(client)
    except Exception as exc:
        logger.warning("Supabase %s.%s failed: %s", table, operation, exc)
        return None


# ═══════════════════════════════════════════════════════════
# Sessions
# ═══════════════════════════════════════════════════════════

def save_session(
    session_id: str,
    resume_name: str = "",
    resume_email: str = "",
    experience_count: int = 0,
    skills_count: int = 0,
    projects_count: int = 0,
    certifications_count: int = 0,
    resume_data: Optional[Dict] = None,
) -> Optional[Dict]:
    """Record a new upload/parse session with full resume data."""
    row = {
        "session_id": session_id,
        "resume_name": resume_name,
        "resume_email": resume_email,
        "experience_count": experience_count,
        "skills_count": skills_count,
        "projects_count": projects_count,
        "certifications_count": certifications_count,
        "resume_data": resume_data or {},
        "created_at": _now_iso(),
        "last_accessed_at": _now_iso(),
    }
    return _safe_execute("sessions", "insert", lambda c: (
        c.table("sessions").insert(row).execute()
    ))


def update_session_resume_data(
    session_id: str,
    resume_data: Dict,
) -> Optional[Dict]:
    """Update the resume_data JSON for an existing session."""
    return _safe_execute("sessions", "update", lambda c: (
        c.table("sessions")
        .update({"resume_data": resume_data, "last_accessed_at": _now_iso()})
        .eq("session_id", session_id)
        .execute()
    ))


def update_session_analysis(
    session_id: str,
    analysis_data: Dict,
) -> Optional[Dict]:
    """Store the ATS analysis result on the session."""
    return _safe_execute("sessions", "update", lambda c: (
        c.table("sessions")
        .update({"analysis_data": analysis_data, "last_accessed_at": _now_iso()})
        .eq("session_id", session_id)
        .execute()
    ))


def get_session(session_id: str) -> Optional[Dict]:
    """Fetch a single session by session_id (includes resume_data + analysis_data)."""
    result = _safe_execute("sessions", "select", lambda c: (
        c.table("sessions")
        .select("*")
        .eq("session_id", session_id)
        .limit(1)
        .execute()
    ))
    if result and hasattr(result, "data") and result.data:
        return result.data[0]
    return None


def touch_session(session_id: str) -> None:
    """Update last_accessed_at to keep session alive."""
    _safe_execute("sessions", "update", lambda c: (
        c.table("sessions")
        .update({"last_accessed_at": _now_iso()})
        .eq("session_id", session_id)
        .execute()
    ))


# ═══════════════════════════════════════════════════════════
# Analyses
# ═══════════════════════════════════════════════════════════

def save_analysis(
    session_id: str,
    overall_score: int,
    grade: str = "",
    keyword_match_pct: float = 0.0,
    matched_count: int = 0,
    missing_count: int = 0,
    format_issues_count: int = 0,
    skill_gaps_count: int = 0,
    job_description_snippet: str = "",
) -> Optional[Dict]:
    """Record an ATS analysis result."""
    row = {
        "session_id": session_id,
        "overall_score": overall_score,
        "grade": grade,
        "keyword_match_pct": round(keyword_match_pct, 2),
        "matched_count": matched_count,
        "missing_count": missing_count,
        "format_issues_count": format_issues_count,
        "skill_gaps_count": skill_gaps_count,
        "job_description_snippet": job_description_snippet[:500],
        "created_at": _now_iso(),
    }
    return _safe_execute("analyses", "insert", lambda c: (
        c.table("analyses").insert(row).execute()
    ))


# ═══════════════════════════════════════════════════════════
# Generations
# ═══════════════════════════════════════════════════════════

def save_generation(
    session_id: str,
    filename: str,
    output_format: str = "docx",
    ats_score: int = 0,
    ats_compatible: bool = True,
    ats_issues_count: int = 0,
    keywords_used: Optional[List[str]] = None,
    job_title: str = "",
    fast_mode: bool = False,
) -> Optional[Dict]:
    """Record a resume generation event."""
    row = {
        "session_id": session_id,
        "filename": filename,
        "output_format": output_format,
        "ats_score": ats_score,
        "ats_compatible": ats_compatible,
        "ats_issues_count": ats_issues_count,
        "keywords_used": keywords_used or [],
        "job_title": job_title,
        "fast_mode": fast_mode,
        "created_at": _now_iso(),
    }
    return _safe_execute("generations", "insert", lambda c: (
        c.table("generations").insert(row).execute()
    ))


# ═══════════════════════════════════════════════════════════
# Reads (for analytics / history)
# ═══════════════════════════════════════════════════════════

def get_session_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch recent sessions (newest first)."""
    result = _safe_execute("sessions", "select", lambda c: (
        c.table("sessions")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    ))
    return result.data if result and hasattr(result, "data") else []


def get_generation_history(
    session_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Fetch recent generation events, optionally filtered by session."""
    def _query(c):
        q = c.table("generations").select("*")
        if session_id:
            q = q.eq("session_id", session_id)
        return q.order("created_at", desc=True).limit(limit).execute()

    result = _safe_execute("generations", "select", _query)
    return result.data if result and hasattr(result, "data") else []


def get_usage_stats() -> Dict[str, Any]:
    """
    Aggregate usage statistics.
    Returns counts for sessions, analyses, and generations.
    """
    stats: Dict[str, Any] = {
        "total_sessions": 0,
        "total_analyses": 0,
        "total_generations": 0,
        "avg_ats_score": 0,
    }

    client = get_supabase()
    if client is None:
        return stats

    try:
        sessions = client.table("sessions").select("id", count="exact").execute()
        stats["total_sessions"] = sessions.count if sessions.count else 0

        analyses = client.table("analyses").select("id", count="exact").execute()
        stats["total_analyses"] = analyses.count if analyses.count else 0

        gens = client.table("generations").select("id, ats_score").execute()
        if gens.data:
            stats["total_generations"] = len(gens.data)
            scores = [g["ats_score"] for g in gens.data if g.get("ats_score")]
            if scores:
                stats["avg_ats_score"] = round(sum(scores) / len(scores), 1)
    except Exception as exc:
        logger.warning("Supabase usage stats query failed: %s", exc)

    return stats


# ═══════════════════════════════════════════════════════════
# Tasks (background task persistence)
# ═══════════════════════════════════════════════════════════

def save_task(
    task_id: str,
    func_name: str = "",
    status: str = "pending",
) -> Optional[Dict]:
    """Record a new background task."""
    row = {
        "task_id": task_id,
        "func_name": func_name,
        "status": status,
        "created_at": _now_iso(),
    }
    return _safe_execute("tasks", "insert", lambda c: (
        c.table("tasks").insert(row).execute()
    ))


def update_task(
    task_id: str,
    status: str,
    result: Any = None,
    error: Optional[str] = None,
    started_at: Optional[str] = None,
    completed_at: Optional[str] = None,
) -> Optional[Dict]:
    """Update a task's status and result."""
    update_data: Dict[str, Any] = {"status": status}
    if result is not None:
        # Only store serialisable results
        try:
            import json
            json.dumps(result)
            update_data["result"] = result
        except (TypeError, ValueError):
            update_data["result"] = {"__repr__": str(result)}
    if error is not None:
        update_data["error"] = error
    if started_at:
        update_data["started_at"] = started_at
    if completed_at:
        update_data["completed_at"] = completed_at

    return _safe_execute("tasks", "update", lambda c: (
        c.table("tasks")
        .update(update_data)
        .eq("task_id", task_id)
        .execute()
    ))


def get_task_db(task_id: str) -> Optional[Dict]:
    """Fetch a single task by task_id."""
    result = _safe_execute("tasks", "select", lambda c: (
        c.table("tasks")
        .select("*")
        .eq("task_id", task_id)
        .limit(1)
        .execute()
    ))
    if result and hasattr(result, "data") and result.data:
        return result.data[0]
    return None


def list_tasks_db(
    status: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    """Fetch recent tasks from the database."""
    def _query(c):
        q = c.table("tasks").select("*")
        if status:
            q = q.eq("status", status)
        return q.order("created_at", desc=True).limit(limit).execute()

    result = _safe_execute("tasks", "select", _query)
    return result.data if result and hasattr(result, "data") else []


def mark_stale_tasks_failed() -> int:
    """Mark any 'running' or 'pending' tasks as 'failed' (called on startup to clean up after crash)."""
    client = get_supabase()
    if client is None:
        return 0
    try:
        result = client.table("tasks") \
            .update({"status": "failed", "error": "Server restarted", "completed_at": _now_iso()}) \
            .in_("status", ["running", "pending"]) \
            .execute()
        count = len(result.data) if result and result.data else 0
        if count:
            logger.info("Marked %d stale tasks as failed after restart", count)
        return count
    except Exception as exc:
        logger.warning("Failed to mark stale tasks: %s", exc)
        return 0


# ═══════════════════════════════════════════════════════════
# Rate Limits (persist hit counters)
# ═══════════════════════════════════════════════════════════

def record_rate_limit_hit(client_ip: str, path: str = "") -> None:
    """Record a rate-limit hit for an IP address."""
    _safe_execute("rate_limits", "insert", lambda c: (
        c.table("rate_limits")
        .insert({"client_ip": client_ip, "path": path, "hit_at": _now_iso()})
        .execute()
    ))


def count_rate_limit_hits(client_ip: str, since_iso: str) -> int:
    """Count how many hits an IP has since the given timestamp."""
    result = _safe_execute("rate_limits", "select", lambda c: (
        c.table("rate_limits")
        .select("id", count="exact")
        .eq("client_ip", client_ip)
        .gte("hit_at", since_iso)
        .execute()
    ))
    if result and hasattr(result, "count") and result.count is not None:
        return result.count
    return 0


def cleanup_old_rate_limits(older_than_iso: str) -> int:
    """Delete rate_limit rows older than the given timestamp."""
    result = _safe_execute("rate_limits", "delete", lambda c: (
        c.table("rate_limits")
        .delete()
        .lt("hit_at", older_than_iso)
        .execute()
    ))
    return len(result.data) if result and hasattr(result, "data") and result.data else 0
