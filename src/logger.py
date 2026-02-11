"""
Structured logging configuration.

Usage anywhere in the app:
    from src.logger import logger
    logger.info("something happened", extra={"session_id": "abc"})
"""

import logging
import json
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object (for production / Docker)."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge any extra keys the caller passed
        if hasattr(record, "session_id"):
            log_entry["session_id"] = record.session_id  # type: ignore[attr-defined]
        if hasattr(record, "endpoint"):
            log_entry["endpoint"] = record.endpoint  # type: ignore[attr-defined]
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms  # type: ignore[attr-defined]
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = str(record.exc_info[1])
        return json.dumps(log_entry, default=str)


class PrettyFormatter(logging.Formatter):
    """Human-friendly coloured output for local development."""

    COLORS = {
        "DEBUG": "\033[36m",     # cyan
        "INFO": "\033[32m",      # green
        "WARNING": "\033[33m",   # yellow
        "ERROR": "\033[31m",     # red
        "CRITICAL": "\033[1;31m",  # bold red
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        ts = datetime.now().strftime("%H:%M:%S")
        return f"{color}{ts} [{record.levelname:<8}]{self.RESET} {record.name}: {record.getMessage()}"


def setup_logging(level: str = "INFO", json_mode: bool = False) -> logging.Logger:
    """
    Configure and return the application root logger.

    Parameters:
        level:     Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_mode: If True, emit structured JSON; otherwise pretty-print.
    """
    root = logging.getLogger("ats")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove any existing handlers to avoid duplicate output on reloads
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter() if json_mode else PrettyFormatter())
    root.addHandler(handler)

    # Quiet noisy third-party loggers
    for noisy in ("httpx", "httpcore", "openai", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return root


# ── Default logger (reconfigured once settings are loaded in main.py) ──
logger = setup_logging()
