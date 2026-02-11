"""
API Key Authentication — lightweight auth for usage tracking.

Supports two modes:
  1. Open mode (default): No auth required — anyone can use the API.
  2. Key mode: Requires a valid API key in the X-API-Key header or ?api_key param.

API keys are stored in Supabase (if configured) or an in-memory set.

Usage:
  # In route handlers:
  from src.auth import get_api_key, require_api_key

  @router.get("/protected")
  async def protected(api_key: str = Depends(require_api_key)):
      ...

  @router.get("/optional")
  async def optional(api_key: Optional[str] = Depends(get_api_key)):
      ...
"""

import hashlib
import secrets
import time
from typing import Optional, Dict, Set

from fastapi import Request, HTTPException, Depends
from fastapi.security import APIKeyHeader, APIKeyQuery

from .config import settings
from .logger import logger

# ── Security schemes ───────────────────────────────────

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_api_key_query = APIKeyQuery(name="api_key", auto_error=False)

# ── In-memory key store (loaded from config + Supabase) ──

_valid_keys: Set[str] = set()
_key_metadata: Dict[str, dict] = {}  # key_hash -> metadata
_key_usage: Dict[str, dict] = {}     # key_hash -> usage counters


def _hash_key(key: str) -> str:
    """Hash an API key for secure storage/comparison."""
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def _load_static_keys():
    """Load API keys from environment config."""
    raw = getattr(settings, "api_keys", "")
    if raw:
        for key in raw.split(","):
            key = key.strip()
            if key:
                _valid_keys.add(key)
                _key_metadata[_hash_key(key)] = {
                    "source": "env",
                    "created_at": time.time(),
                }
        logger.info("Loaded %d API key(s) from environment", len(_valid_keys))


def _init_auth():
    """Initialize auth on first use."""
    if not _valid_keys and not hasattr(_init_auth, "_loaded"):
        _load_static_keys()
        _init_auth._loaded = True


# ═══════════════════════════════════════════════════════════
# Key Management
# ═══════════════════════════════════════════════════════════

def generate_api_key(prefix: str = "ats") -> str:
    """
    Generate a new API key.

    Format: {prefix}_live_{32 random hex chars}
    Example: ats_live_a1b2c3d4e5f6...
    """
    random_part = secrets.token_hex(16)
    return f"{prefix}_live_{random_part}"


def add_api_key(key: str, metadata: Optional[dict] = None) -> None:
    """Register a new API key."""
    _valid_keys.add(key)
    _key_metadata[_hash_key(key)] = {
        "source": "runtime",
        "created_at": time.time(),
        **(metadata or {}),
    }


def revoke_api_key(key: str) -> bool:
    """Revoke an API key. Returns True if found and removed."""
    if key in _valid_keys:
        _valid_keys.discard(key)
        _key_metadata.pop(_hash_key(key), None)
        _key_usage.pop(_hash_key(key), None)
        return True
    return False


def is_auth_enabled() -> bool:
    """Check if authentication is required (any keys are configured)."""
    _init_auth()
    return len(_valid_keys) > 0


def validate_key(key: str) -> bool:
    """Check if an API key is valid."""
    _init_auth()
    if not _valid_keys:
        return True  # No keys configured → open access
    return key in _valid_keys


def record_usage(key: str, endpoint: str) -> None:
    """Record API key usage for tracking."""
    key_hash = _hash_key(key)
    if key_hash not in _key_usage:
        _key_usage[key_hash] = {
            "total_requests": 0,
            "endpoints": {},
            "last_used": 0,
        }
    usage = _key_usage[key_hash]
    usage["total_requests"] += 1
    usage["last_used"] = time.time()
    usage["endpoints"][endpoint] = usage["endpoints"].get(endpoint, 0) + 1


def get_key_stats() -> dict:
    """Get usage statistics for all keys."""
    return {
        "keys_configured": len(_valid_keys),
        "auth_enabled": is_auth_enabled(),
        "usage": {
            k: {**v, "key_prefix": k[:8]}
            for k, v in _key_usage.items()
        },
    }


# ═══════════════════════════════════════════════════════════
# FastAPI Dependencies
# ═══════════════════════════════════════════════════════════

async def get_api_key(
    request: Request,
    header_key: Optional[str] = Depends(_api_key_header),
    query_key: Optional[str] = Depends(_api_key_query),
) -> Optional[str]:
    """
    Extract API key from request (header or query param).
    Returns None if no key is provided.
    Does NOT enforce — use require_api_key for that.
    """
    key = header_key or query_key
    if key:
        record_usage(key, request.url.path)
    return key


async def require_api_key(
    request: Request,
    header_key: Optional[str] = Depends(_api_key_header),
    query_key: Optional[str] = Depends(_api_key_query),
) -> str:
    """
    Require a valid API key. Raises 401 if missing or invalid.
    Skips validation if no keys are configured (open mode).
    """
    _init_auth()

    # Open mode: no keys configured → allow everything
    if not _valid_keys:
        return "open_access"

    key = header_key or query_key
    if not key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide via X-API-Key header or ?api_key param.",
        )

    if not validate_key(key):
        raise HTTPException(
            status_code=403,
            detail="Invalid API key.",
        )

    record_usage(key, request.url.path)
    return key
