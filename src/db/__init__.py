"""
Database layer — Supabase PostgreSQL integration.

Provides CRUD operations for sessions, analyses, generations, tasks, and rate limits.
All DB calls are best-effort so the app works without Supabase too (falls back to in-memory).
"""

from .client import get_supabase, is_db_enabled
from .operations import (
    # Sessions
    save_session,
    update_session_resume_data,
    update_session_analysis,
    get_session,
    touch_session,
    # Analyses & Generations
    save_analysis,
    save_generation,
    get_session_history,
    get_generation_history,
    get_usage_stats,
    # Tasks
    save_task,
    update_task,
    get_task_db,
    list_tasks_db,
    mark_stale_tasks_failed,
    # Rate limits
    record_rate_limit_hit,
    count_rate_limit_hits,
    cleanup_old_rate_limits,
)

__all__ = [
    "get_supabase",
    "is_db_enabled",
    # Sessions
    "save_session",
    "update_session_resume_data",
    "update_session_analysis",
    "get_session",
    "touch_session",
    # Analyses & Generations
    "save_analysis",
    "save_generation",
    "get_session_history",
    "get_generation_history",
    "get_usage_stats",
    # Tasks
    "save_task",
    "update_task",
    "get_task_db",
    "list_tasks_db",
    "mark_stale_tasks_failed",
    # Rate limits
    "record_rate_limit_hit",
    "count_rate_limit_hits",
    "cleanup_old_rate_limits",
]
