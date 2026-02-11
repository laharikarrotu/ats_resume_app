"""
Upload & Parse routes — handles resume file uploads and text input.
"""

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Form, UploadFile, File, HTTPException

from ..config import UPLOAD_DIR, settings
from ..exceptions import UnsupportedFileTypeError, FileParsingError, FileTooLargeError
from ..logger import logger
from ..metrics import metrics
from ..core.resume_parser import parse_resume, parse_resume_from_text
from ..db import save_session
from .deps import save_resume_data

router = APIRouter()


@router.post("/upload_resume/")
async def upload_resume(file: UploadFile = File(...)):
    """Upload and parse a resume file (PDF, DOCX, or TXT)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".pdf", ".docx", ".doc", ".txt", ".text"]:
        raise UnsupportedFileTypeError()

    # Check file size
    contents = await file.read()
    if len(contents) > settings.max_file_size_mb * 1024 * 1024:
        raise FileTooLargeError(f"File exceeds {settings.max_file_size_mb}MB limit.")
    await file.seek(0)

    session_id = uuid4().hex[:16]
    temp_file_path = UPLOAD_DIR / f"{session_id}{file_ext}"

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        with metrics.timer("resume_parse_seconds"):
            resume_data = parse_resume(str(temp_file_path))
        save_resume_data(session_id, resume_data)
        temp_file_path.unlink()
        metrics.inc("resume_uploads_total", labels={"type": "file", "ext": file_ext})

        exp_count = len(resume_data.experience)
        proj_count = len(resume_data.projects)
        skills_count = sum(len(v) for v in resume_data.skills.values())
        certs_count = len(resume_data.certifications)

        # Persist to Supabase (fire-and-forget)
        save_session(
            session_id=session_id,
            resume_name=resume_data.name,
            resume_email=resume_data.email,
            experience_count=exp_count,
            skills_count=skills_count,
            projects_count=proj_count,
            certifications_count=certs_count,
            resume_data=resume_data.model_dump(),
        )

        return {
            "session_id": session_id,
            "message": "Resume uploaded and parsed successfully",
            "name": resume_data.name,
            "email": resume_data.email,
            "experience_count": exp_count,
            "projects_count": proj_count,
            "skills_count": skills_count,
            "certifications_count": certs_count,
        }

    except Exception as e:
        if temp_file_path.exists():
            temp_file_path.unlink()
        logger.error("Resume parsing failed: %s", e, exc_info=True)
        raise FileParsingError(f"Error parsing resume: {e}")


@router.post("/upload_resume_text/")
async def upload_resume_text(resume_text: str = Form(...)):
    """Parse resume from pasted / typed plain text."""
    if not resume_text or not resume_text.strip():
        raise HTTPException(status_code=400, detail="Resume text is empty.")

    session_id = uuid4().hex[:16]

    try:
        with metrics.timer("resume_parse_seconds"):
            resume_data = parse_resume_from_text(resume_text)
        save_resume_data(session_id, resume_data)
        metrics.inc("resume_uploads_total", labels={"type": "text", "ext": "txt"})

        exp_count = len(resume_data.experience)
        proj_count = len(resume_data.projects)
        skills_count = sum(len(v) for v in resume_data.skills.values())
        certs_count = len(resume_data.certifications)

        # Persist to Supabase (fire-and-forget)
        save_session(
            session_id=session_id,
            resume_name=resume_data.name,
            resume_email=resume_data.email,
            experience_count=exp_count,
            skills_count=skills_count,
            projects_count=proj_count,
            certifications_count=certs_count,
            resume_data=resume_data.model_dump(),
        )

        return {
            "session_id": session_id,
            "message": "Resume text parsed successfully",
            "name": resume_data.name,
            "email": resume_data.email,
            "experience_count": exp_count,
            "projects_count": proj_count,
            "skills_count": skills_count,
            "certifications_count": certs_count,
        }

    except Exception as e:
        logger.error("Resume text parsing failed: %s", e, exc_info=True)
        raise FileParsingError(f"Error parsing resume text: {e}")
