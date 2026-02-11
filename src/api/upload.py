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
from ..core.resume_parser import parse_resume, parse_resume_from_text
from .deps import resume_data_cache

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

        resume_data = parse_resume(str(temp_file_path))
        resume_data_cache[session_id] = resume_data
        temp_file_path.unlink()

        return {
            "session_id": session_id,
            "message": "Resume uploaded and parsed successfully",
            "name": resume_data.name,
            "email": resume_data.email,
            "experience_count": len(resume_data.experience),
            "projects_count": len(resume_data.projects),
            "skills_count": sum(len(v) for v in resume_data.skills.values()),
            "certifications_count": len(resume_data.certifications),
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
        resume_data = parse_resume_from_text(resume_text)
        resume_data_cache[session_id] = resume_data

        return {
            "session_id": session_id,
            "message": "Resume text parsed successfully",
            "name": resume_data.name,
            "email": resume_data.email,
            "experience_count": len(resume_data.experience),
            "projects_count": len(resume_data.projects),
            "skills_count": sum(len(v) for v in resume_data.skills.values()),
            "certifications_count": len(resume_data.certifications),
        }

    except Exception as e:
        logger.error("Resume text parsing failed: %s", e, exc_info=True)
        raise FileParsingError(f"Error parsing resume text: {e}")
