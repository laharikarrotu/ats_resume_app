"""
Application configuration — Pydantic BaseSettings with env-variable validation.

All settings are loaded from environment variables (or .env file) and validated at startup.
Import `settings` from this module instead of reading os.environ directly.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


# ── Derived project paths (not configurable, always relative to repo root) ──
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR = BASE_DIR / "uploads"
RESUME_TEMPLATES_DIR = BASE_DIR / "resume_templates"
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"

# Ensure required directories exist at import time
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    """
    Validated application settings.

    Values are read from environment variables → .env file → defaults (in that order).
    """

    # ── App metadata ──
    app_title: str = "ATS Resume Optimizer"
    app_version: str = "2.0.0"
    debug: bool = False

    # ── Server ──
    host: str = "127.0.0.1"
    port: int = 8000

    # ── LLM provider keys ──
    gemini_api_key: str = ""
    openai_api_key: str = ""

    # ── Supabase ──
    supabase_url: str = Field(default="", description="Supabase project URL (e.g., https://xxx.supabase.co)")
    supabase_anon_key: str = Field(default="", description="Supabase anonymous/public API key")
    supabase_service_role_key: str = Field(
        default="", description="Supabase service role key (server-side only, optional)"
    )

    # ── Auth ──
    api_keys: str = Field(
        default="",
        description="Comma-separated API keys. Empty = open access (no auth required)",
    )

    # ── Storage (S3 optional) ──
    s3_bucket: str = Field(default="", description="S3 bucket name (empty = local storage)")
    s3_region: str = Field(default="us-east-1", description="AWS region for S3")
    s3_prefix: str = Field(default="ats-resume-app/", description="Key prefix in S3 bucket")

    # ── LLM settings ──
    llm_provider: str = Field(
        default="auto",
        description="Force a provider: 'gemini', 'openai', or 'auto' (pick first available key)",
    )
    llm_timeout: int = Field(default=60, description="LLM request timeout in seconds")
    llm_max_retries: int = Field(default=2, description="LLM call retries before giving up")

    # ── Rate limiting ──
    rate_limit_requests: int = Field(
        default=30, description="Max requests per window per IP"
    )
    rate_limit_window_seconds: int = Field(
        default=3600, description="Rate limit window in seconds (default 1 hour)"
    )

    # ── File limits ──
    max_file_size_mb: int = Field(default=10, description="Max upload file size in MB")

    # ── Logging ──
    log_level: str = Field(default="INFO", description="Logging level")
    log_json: bool = Field(
        default=False, description="Emit structured JSON logs (useful in production)"
    )

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",          # ignore unknown env vars
    }


# ── Module-level singleton ──
settings = Settings()

# ── Convenience aliases (backwards-compatible) ──
APP_TITLE = settings.app_title
APP_VERSION = settings.app_version
