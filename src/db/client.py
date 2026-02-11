"""
Supabase client singleton.

Returns None when credentials are not configured so the rest of the app
keeps working with in-memory caches only.
"""

from typing import Optional

from ..config import settings
from ..logger import logger

_client = None
_initialised = False


def _init_client():
    """Lazy-initialise the Supabase client (called once)."""
    global _client, _initialised

    if _initialised:
        return

    _initialised = True

    if not settings.supabase_url or not settings.supabase_anon_key:
        logger.info("Supabase credentials not configured — running with in-memory storage only")
        return

    try:
        from supabase import create_client, Client

        key = settings.supabase_service_role_key or settings.supabase_anon_key
        _client = create_client(settings.supabase_url, key)
        logger.info("✅ Supabase client connected — %s", settings.supabase_url)
    except Exception as exc:
        logger.warning("⚠️  Failed to initialise Supabase client: %s", exc)
        _client = None


def get_supabase():
    """Return the Supabase client (or None if not configured)."""
    if not _initialised:
        _init_client()
    return _client


def is_db_enabled() -> bool:
    """Quick check: is the database layer active?"""
    return get_supabase() is not None
