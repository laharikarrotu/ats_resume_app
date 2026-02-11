"""
Multi-LLM Provider: Supports Gemini (free) + OpenAI with automatic fallback.

Provider priority:
  1. Google Gemini 2.0 Flash (FREE — 15 RPM, 1M tokens/day)
  2. OpenAI GPT-4o-mini (paid — ~$0.15/1M input)
  3. Fallback (no API key — basic heuristic extraction)

Both providers use the OpenAI Python SDK — Gemini provides an OpenAI-compatible endpoint.

Setup:
  Option A (FREE):  Set GEMINI_API_KEY in .env → uses Gemini Flash
  Option B (PAID):  Set OPENAI_API_KEY in .env → uses GPT-4o-mini
  Option C (BOTH):  Set both → Gemini primary, OpenAI fallback
"""

from typing import Optional, Tuple

from openai import OpenAI, AsyncOpenAI

from ..config import settings
from ..logger import logger

# ═══════════════════════════════════════════════════════════════
# Configuration (from validated settings)
# ═══════════════════════════════════════════════════════════════

GEMINI_API_KEY = settings.gemini_api_key
OPENAI_API_KEY = settings.openai_api_key

# Gemini uses the OpenAI-compatible endpoint
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = "gemini-2.0-flash"       # Free, fast, great for structured output
GEMINI_MODEL_LITE = "gemini-2.0-flash-lite"  # Even faster, lower quality

OPENAI_MODEL = "gpt-4o-mini"            # Paid, reliable, excellent quality


def _get_active_provider() -> str:
    """Determine which provider to use based on available API keys."""
    if GEMINI_API_KEY:
        return "gemini"
    elif OPENAI_API_KEY:
        return "openai"
    else:
        return "none"


ACTIVE_PROVIDER = _get_active_provider()


# ═══════════════════════════════════════════════════════════════
# Sync Clients
# ═══════════════════════════════════════════════════════════════

def get_sync_client() -> Tuple[Optional[OpenAI], str]:
    """
    Get the sync OpenAI client configured for the active provider.

    Returns:
        Tuple of (client, model_name). Client is None if no API key is set.
    """
    if GEMINI_API_KEY:
        client = OpenAI(
            api_key=GEMINI_API_KEY,
            base_url=GEMINI_BASE_URL,
            timeout=settings.llm_timeout,
            max_retries=settings.llm_max_retries,
        )
        return client, GEMINI_MODEL

    if OPENAI_API_KEY:
        client = OpenAI(
            api_key=OPENAI_API_KEY,
            timeout=settings.llm_timeout,
            max_retries=settings.llm_max_retries,
        )
        return client, OPENAI_MODEL

    return None, ""


def get_fallback_sync_client() -> Tuple[Optional[OpenAI], str]:
    """
    Get the fallback sync client (OpenAI if Gemini is primary, or None).
    """
    if GEMINI_API_KEY and OPENAI_API_KEY:
        client = OpenAI(
            api_key=OPENAI_API_KEY,
            timeout=settings.llm_timeout,
            max_retries=settings.llm_max_retries,
        )
        return client, OPENAI_MODEL
    return None, ""


# ═══════════════════════════════════════════════════════════════
# Async Clients
# ═══════════════════════════════════════════════════════════════

def get_async_client() -> Tuple[Optional[AsyncOpenAI], str]:
    """
    Get the async OpenAI client configured for the active provider.

    Returns:
        Tuple of (async_client, model_name). Client is None if no API key is set.
    """
    if GEMINI_API_KEY:
        client = AsyncOpenAI(
            api_key=GEMINI_API_KEY,
            base_url=GEMINI_BASE_URL,
            timeout=settings.llm_timeout,
            max_retries=settings.llm_max_retries,
        )
        return client, GEMINI_MODEL

    if OPENAI_API_KEY:
        client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            timeout=settings.llm_timeout,
            max_retries=settings.llm_max_retries,
        )
        return client, OPENAI_MODEL

    return None, ""


def get_fallback_async_client() -> Tuple[Optional[AsyncOpenAI], str]:
    """
    Get the fallback async client (OpenAI if Gemini is primary, or None).
    """
    if GEMINI_API_KEY and OPENAI_API_KEY:
        client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            timeout=settings.llm_timeout,
            max_retries=settings.llm_max_retries,
        )
        return client, OPENAI_MODEL
    return None, ""


# ═══════════════════════════════════════════════════════════════
# Pre-built clients (module-level singletons)
# ═══════════════════════════════════════════════════════════════

# Primary
client, MODEL = get_sync_client()
async_client, ASYNC_MODEL = get_async_client()

# Fallback
fallback_client, FALLBACK_MODEL = get_fallback_sync_client()
fallback_async_client, FALLBACK_ASYNC_MODEL = get_fallback_async_client()

logger.info(
    "LLM provider ready — primary: %s, fallback: %s",
    ACTIVE_PROVIDER,
    "openai" if fallback_client else "none",
)


def get_provider_info() -> dict:
    """Return info about the active LLM provider (for health/status endpoints)."""
    return {
        "active_provider": ACTIVE_PROVIDER,
        "model": MODEL or "none (fallback mode)",
        "has_fallback": fallback_client is not None,
        "fallback_model": FALLBACK_MODEL or "none",
        "gemini_configured": bool(GEMINI_API_KEY),
        "openai_configured": bool(OPENAI_API_KEY),
    }
