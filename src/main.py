from pathlib import Path
from uuid import uuid4
from typing import Optional
import shutil

from fastapi import FastAPI, Form, Request, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .resume_generator import generate_resume
from .llm_client import extract_keywords
from .models import JobDescriptionRequest, ResumeResponse, ResumeData
from .resume_parser import parse_resume


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = BASE_DIR / "uploads"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="ATS Resume Generator", version="0.1.0")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# In-memory storage for parsed resume data (session-based)
# In production, use a database or session storage
resume_data_cache: dict[str, ResumeData] = {}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "ATS Resume Generator",
        },
    )


@app.post("/upload_resume/")
async def upload_resume(file: UploadFile = File(...)):
    """
    Upload and parse a resume file (PDF or DOCX).
    Returns a session ID to use for generating personalized resumes.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ['.pdf', '.docx', '.doc']:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF and DOCX files are supported."
        )
    
    # Save uploaded file temporarily
    session_id = uuid4().hex[:16]
    temp_file_path = UPLOAD_DIR / f"{session_id}{file_ext}"
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Parse resume
        resume_data = parse_resume(str(temp_file_path))
        
        # Store parsed data in cache
        resume_data_cache[session_id] = resume_data
        
        # Clean up temp file
        temp_file_path.unlink()
        
        return {
            "session_id": session_id,
            "message": "Resume uploaded and parsed successfully",
            "name": resume_data.name,
            "email": resume_data.email,
            "experience_count": len(resume_data.experience),
            "projects_count": len(resume_data.projects),
        }
    
    except Exception as e:
        # Clean up on error
        if temp_file_path.exists():
            temp_file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error parsing resume: {str(e)}")


@app.post("/generate_resume/", response_class=FileResponse)
async def create_resume(
    job_description: str = Form(...),
    session_id: Optional[str] = Form(None)
):
    """
    HTML form endpoint: returns a DOCX file directly.
    
    If session_id is provided, uses parsed resume data for personalized generation.
    Otherwise, generates a basic resume with keywords only.
    """
    keywords = extract_keywords(job_description)
    
    # Get parsed resume data if session_id provided
    resume_data = None
    if session_id and session_id in resume_data_cache:
        resume_data = resume_data_cache[session_id]
    
    filename = f"ATS_resume_{uuid4().hex[:8]}.docx"
    output_path = OUTPUT_DIR / filename
    
    # Generate resume with personalized data if available
    generate_resume(
        str(output_path),
        keywords,
        resume_data=resume_data,
        job_description=job_description
    )
    
    return FileResponse(
        path=str(output_path),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        filename="ATS_resume.docx",
    )


@app.post("/api/generate_resume", response_model=ResumeResponse)
async def create_resume_api(
    payload: JobDescriptionRequest,
    session_id: Optional[str] = Query(None, description="Session ID from resume upload")
):
    """
    JSON API endpoint: returns download path & extracted keywords.
    
    If session_id is provided in query parameter, uses parsed resume data.
    Example: POST /api/generate_resume?session_id=abc123
    """
    keywords = extract_keywords(payload.job_description)
    
    # Get parsed resume data if session_id provided
    resume_data = None
    if session_id and session_id in resume_data_cache:
        resume_data = resume_data_cache[session_id]
    
    filename = f"ATS_resume_{uuid4().hex[:8]}.docx"
    output_path = OUTPUT_DIR / filename
    
    # Generate resume with personalized data if available
    generate_resume(
        str(output_path),
        keywords,
        resume_data=resume_data,
        job_description=payload.job_description
    )
    
    return ResumeResponse(
        download_path=f"/download/{filename}",
        keywords=keywords,
    )


@app.get("/download/{filename}", response_class=FileResponse)
async def download_resume(filename: str):
    """Serve generated resume files by name."""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        # FastAPI will convert this to a 404
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(file_path),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        filename="ATS_resume.docx",
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}


