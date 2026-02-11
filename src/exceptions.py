"""
Custom exception hierarchy for the ATS Resume application.

All domain-specific errors inherit from AppError so they can be caught
by a single global handler in main.py and returned as structured JSON.
"""

from typing import Optional


class AppError(Exception):
    """Base application error — every custom exception inherits from this."""

    status_code: int = 500
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: Optional[str] = None, *, status_code: Optional[int] = None):
        self.detail = detail or self.__class__.detail
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.detail)


# ── File / Upload errors ──

class FileParsingError(AppError):
    """Raised when a resume file cannot be parsed."""
    status_code = 422
    detail = "Failed to parse the uploaded file."


class UnsupportedFileTypeError(AppError):
    """Raised when the file type is not supported."""
    status_code = 400
    detail = "Unsupported file type. Accepted formats: PDF, DOCX, TXT."


class FileTooLargeError(AppError):
    """Raised when the upload exceeds the size limit."""
    status_code = 413
    detail = "File exceeds the maximum allowed size."


# ── LLM errors ──

class LLMProviderError(AppError):
    """Raised when the LLM API call fails (timeout, auth, quota, etc.)."""
    status_code = 502
    detail = "LLM service is currently unavailable. Please try again."


class LLMQuotaExceededError(LLMProviderError):
    """Raised when the LLM provider rate/quota limit is hit."""
    status_code = 429
    detail = "LLM rate limit reached. Please wait and retry."


class NoLLMConfiguredError(AppError):
    """Raised when no LLM API key is configured."""
    status_code = 503
    detail = "No LLM provider configured. Set GEMINI_API_KEY or OPENAI_API_KEY."


# ── Resume / Session errors ──

class SessionNotFoundError(AppError):
    """Raised when a session_id doesn't match any cached data."""
    status_code = 404
    detail = "Session not found. Please upload a resume first."


class ResumeGenerationError(AppError):
    """Raised when resume generation (DOCX or PDF) fails."""
    status_code = 500
    detail = "Failed to generate the resume document."


class LaTeXCompilationError(ResumeGenerationError):
    """Raised when pdflatex compilation fails."""
    status_code = 500
    detail = "LaTeX compilation failed."


class LaTeXNotInstalledError(ResumeGenerationError):
    """Raised when pdflatex is not found on the system."""
    status_code = 503
    detail = "LaTeX is not installed. Use DOCX output format instead."


# ── Rate limiting ──

class RateLimitExceededError(AppError):
    """Raised when the client exceeds the IP-based rate limit."""
    status_code = 429
    detail = "Too many requests. Please slow down."
