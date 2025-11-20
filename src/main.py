from pathlib import Path
from uuid import uuid4
from typing import Optional
import shutil

from fastapi import FastAPI, Form, Request, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.gzip import GZipMiddleware

from .resume_generator import generate_resume
from .llm_client import extract_keywords
from .llm_client_async import extract_keywords_async

# Try to import optimized version (faster)
try:
    from .llm_client_optimized import (
        extract_keywords_async_optimized,
        prepare_resume_data_optimized
    )
    OPTIMIZED_AVAILABLE = True
except ImportError:
    OPTIMIZED_AVAILABLE = False

# Try to import LaTeX generator
try:
    from .resume_generator_latex import generate_resume_latex
    LATEX_AVAILABLE = True
except ImportError:
    LATEX_AVAILABLE = False
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

# Add GZip compression for better performance
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Static files with cache headers for better performance
class CachedStaticFiles(StaticFiles):
    async def __call__(self, scope, receive, send):
        response = await super().__call__(scope, receive, send)
        if hasattr(response, 'headers'):
            # Cache static files for 1 year (immutable)
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

app.mount("/static", CachedStaticFiles(directory=str(STATIC_DIR)), name="static")
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
    session_id: Optional[str] = Form(None),
    output_format: str = Form("docx"),  # "docx" or "pdf" (LaTeX)
    fast_mode: str = Form("false")  # "true" or "false" for fast mode
):
    """
    HTML form endpoint: returns a DOCX file directly.
    
    If session_id is provided, uses parsed resume data for personalized generation.
    Otherwise, generates a basic resume with keywords only.
    
    fast_mode: "true" for ultra-fast generation (1-2s), "false" for quality (2-5s)
    """
    # Use optimized keyword extraction with caching
    use_fast_mode = fast_mode.lower() == "true"
    if OPTIMIZED_AVAILABLE:
        keywords = await extract_keywords_async_optimized(job_description, use_cache=True)
    else:
        keywords = await extract_keywords_async(job_description)
    
    # Get parsed resume data if session_id provided
    resume_data = None
    if session_id and session_id in resume_data_cache:
        resume_data = resume_data_cache[session_id]
    
    filename = f"ATS_resume_{uuid4().hex[:8]}.docx"
    output_path = OUTPUT_DIR / filename
    
    # Generate resume with personalized data if available
    # Use parallel LLM calls for faster generation
    if output_format.lower() == "pdf" and LATEX_AVAILABLE:
        # Generate PDF using LaTeX (run in thread pool to not block)
        try:
            import asyncio
            pdf_path = await asyncio.to_thread(
                generate_resume_latex,
                str(output_path).replace('.docx', '.pdf'),
                keywords,
                resume_data,
                job_description
            )
            filename = Path(pdf_path).name
            return FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename=filename
            )
        except FileNotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail=f"LaTeX template not found. Please ensure the template file exists. Error: {str(e)}"
            )
        except RuntimeError as e:
            error_msg = str(e)
            if "LaTeX not installed" in error_msg or "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=503,
                    detail=f"LaTeX is not installed on the server. Please use DOCX format instead. Error: {error_msg}"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"LaTeX compilation failed: {error_msg}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating PDF: {str(e)}"
            )
    else:
        # Generate DOCX (default)
        await generate_resume(
            str(output_path),
            keywords,
            resume_data=resume_data,
            job_description=job_description,
            use_parallel=True,  # Enable parallel LLM calls for speed
            fast_mode=use_fast_mode,  # Fast mode option
            session_id=session_id  # For caching
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
    session_id: Optional[str] = Query(None, description="Session ID from resume upload"),
    output_format: str = Query("docx", description="Output format: 'docx' or 'pdf'")
):
    """
    JSON API endpoint: returns download path & extracted keywords.
    
    If session_id is provided in query parameter, uses parsed resume data.
    Example: POST /api/generate_resume?session_id=abc123
    """
    # Use async keyword extraction for faster generation
    keywords = await extract_keywords_async(payload.job_description)
    
    # Get parsed resume data if session_id provided
    resume_data = None
    if session_id and session_id in resume_data_cache:
        resume_data = resume_data_cache[session_id]
    
    # Generate based on format
    if output_format.lower() == "pdf" and LATEX_AVAILABLE:
        filename = f"ATS_resume_{uuid4().hex[:8]}.pdf"
        output_path = OUTPUT_DIR / filename
        try:
            import asyncio
            pdf_path = await asyncio.to_thread(
                generate_resume_latex,
                str(output_path),
                keywords,
                resume_data,
                payload.job_description
            )
        except FileNotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail=f"LaTeX template not found. Please ensure the template file exists. Error: {str(e)}"
            )
        except RuntimeError as e:
            error_msg = str(e)
            if "LaTeX not installed" in error_msg or "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=503,
                    detail=f"LaTeX is not installed on the server. Please use DOCX format instead. Error: {error_msg}"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"LaTeX compilation failed: {error_msg}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating PDF: {str(e)}"
            )
    else:
        filename = f"ATS_resume_{uuid4().hex[:8]}.docx"
        output_path = OUTPUT_DIR / filename
        # Generate DOCX with parallel LLM calls
        await generate_resume(
            str(output_path),
            keywords,
            resume_data=resume_data,
            job_description=payload.job_description,
            use_parallel=True  # Enable parallel processing
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


