"""
ATS Validation routes — post-generation compatibility checks.

Endpoints:
  POST /api/validate       → Validate a generated resume file for ATS compat
  POST /api/validate/text  → Validate raw resume text for ATS compat
"""

from dataclasses import asdict
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Form, Query, HTTPException, UploadFile, File

from ..config import OUTPUT_DIR
from ..core.ats_validator import (
    validate_resume_output,
    validate_docx_file,
    validate_pdf_file,
    sanitize_for_ats,
)
from .deps import get_resume_data

router = APIRouter()


# ═══════════════════════════════════════════════════════════
# Validate a generated file (DOCX / PDF)
# ═══════════════════════════════════════════════════════════

@router.post("/api/validate")
async def validate_generated_resume(
    filename: str = Form(..., description="Name of generated file in output dir"),
    session_id: Optional[str] = Form(None),
    keywords: Optional[str] = Form(None, description="Comma-separated target keywords"),
):
    """
    Validate a previously generated resume file for ATS compatibility.

    Runs 10 checks that mirror how Workday / Taleo / Greenhouse parse resumes:
      text readability, section detection, contact parsing, date format,
      special characters, structure, section names, keyword density,
      contact completeness, bullet format.

    Returns a compatibility score (0–100) and detailed issues.
    """
    file_path = OUTPUT_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    resume_data = None
    if session_id:
        resume_data = get_resume_data(session_id)

    kw_list = [k.strip() for k in keywords.split(",")] if keywords else None

    suffix = file_path.suffix.lower()
    if suffix == ".docx":
        result = validate_docx_file(str(file_path), resume_data, kw_list)
    elif suffix == ".pdf":
        result = validate_pdf_file(str(file_path), resume_data, kw_list)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{suffix}'. Supported: .docx, .pdf"
        )

    return _result_to_dict(result)


# ═══════════════════════════════════════════════════════════
# Validate raw text (e.g. pasted or from frontend)
# ═══════════════════════════════════════════════════════════

@router.post("/api/validate/text")
async def validate_resume_text(
    resume_text: str = Form(..., min_length=50, description="Full resume text"),
    session_id: Optional[str] = Form(None),
    keywords: Optional[str] = Form(None, description="Comma-separated target keywords"),
):
    """
    Validate raw resume text for ATS compatibility.

    Useful for checking paste-in resumes or previewing ATS score
    before generating the final DOCX/PDF.
    """
    resume_data = None
    if session_id:
        resume_data = get_resume_data(session_id)

    kw_list = [k.strip() for k in keywords.split(",")] if keywords else None

    result = validate_resume_output(resume_text, resume_data, kw_list)
    return _result_to_dict(result)


# ═══════════════════════════════════════════════════════════
# Sanitize text (strip ATS-unfriendly chars)
# ═══════════════════════════════════════════════════════════

@router.post("/api/sanitize")
async def sanitize_text(
    text: str = Form(..., min_length=10, description="Text to sanitize"),
):
    """
    Clean text of ATS-breaking characters.

    Replaces fancy bullets, smart quotes, invisible characters,
    and other symbols that confuse ATS parsers.
    """
    cleaned = sanitize_for_ats(text)
    chars_replaced = sum(1 for a, b in zip(text, cleaned) if a != b) if len(text) == len(cleaned) else abs(len(text) - len(cleaned))
    return {
        "sanitized_text": cleaned,
        "characters_replaced": chars_replaced,
        "original_length": len(text),
        "sanitized_length": len(cleaned),
    }


# ═══════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════

def _result_to_dict(result) -> dict:
    """Convert ATSValidationResult dataclass to JSON-serializable dict."""
    data = asdict(result)
    # Ensure issues are clean dicts
    data["issues"] = [
        {
            "severity": i["severity"],
            "check": i["check"],
            "message": i["message"],
            "suggestion": i["suggestion"],
        }
        for i in data["issues"]
    ]
    return data
