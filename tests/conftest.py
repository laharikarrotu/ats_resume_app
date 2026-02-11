"""
Shared test fixtures for the ATS Resume App test suite.

Provides reusable fixtures for:
  - FastAPI test client
  - Sample resume data
  - Sample job descriptions
  - Temporary file helpers
  - Mock LLM responses
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Generator

import pytest
from fastapi.testclient import TestClient

# Ensure test env doesn't hit real services
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("SUPABASE_URL", "")
os.environ.setdefault("SUPABASE_ANON_KEY", "")
os.environ.setdefault("DEBUG", "true")


# ── App / Client Fixtures ──────────────────────────────

@pytest.fixture(scope="session")
def app():
    """Create the FastAPI application for testing."""
    from src.main import app as fastapi_app
    return fastapi_app


@pytest.fixture()
def client(app) -> Generator:
    """FastAPI test client — no real server needed."""
    with TestClient(app) as c:
        yield c


# ── Resume Data Fixtures ───────────────────────────────

@pytest.fixture()
def sample_resume_data():
    """A realistic ResumeData object for testing."""
    from src.models import ResumeData, Education, Experience, Project, Certification

    return ResumeData(
        name="Jane Doe",
        email="jane.doe@example.com",
        phone="(555) 123-4567",
        linkedin="https://linkedin.com/in/janedoe",
        github="https://github.com/janedoe",
        location="San Francisco, CA",
        education=[
            Education(
                degree="Master of Science in Computer Science",
                university="Stanford University",
                location="Stanford, CA",
                dates="2020 - 2022",
                gpa="3.9",
                coursework=["Machine Learning", "Distributed Systems", "Algorithms"],
            ),
            Education(
                degree="Bachelor of Science in Software Engineering",
                university="UC Berkeley",
                location="Berkeley, CA",
                dates="2016 - 2020",
                gpa="3.7",
            ),
        ],
        skills={
            "Programming Languages": ["Python", "Java", "TypeScript", "Go"],
            "Frameworks": ["FastAPI", "React", "Spring Boot", "Django"],
            "Cloud & DevOps": ["AWS", "Docker", "Kubernetes", "Terraform"],
            "Databases": ["PostgreSQL", "MongoDB", "Redis"],
        },
        experience=[
            Experience(
                title="Senior Software Engineer",
                company="Google",
                dates="Jan 2023 - Present",
                bullets=[
                    "Architected a microservices platform serving 10M+ daily requests with 99.99% uptime",
                    "Led a team of 5 engineers to deliver a real-time data pipeline reducing latency by 60%",
                    "Implemented CI/CD pipelines using GitHub Actions and Terraform, cutting deploy time by 75%",
                    "Optimized PostgreSQL queries resulting in 3x throughput improvement for analytics dashboard",
                ],
            ),
            Experience(
                title="Software Engineer",
                company="Meta",
                dates="Jun 2022 - Dec 2022",
                bullets=[
                    "Developed RESTful APIs using Python and FastAPI serving 5M+ requests per day",
                    "Built React components for the internal developer tools platform used by 2000+ engineers",
                    "Reduced test suite execution time from 45 minutes to 12 minutes through parallelization",
                ],
            ),
        ],
        projects=[
            Project(
                name="ATS Resume Optimizer",
                description="AI-powered resume optimization tool using LLMs for keyword extraction and content rewriting",
                technologies=["Python", "FastAPI", "React", "TypeScript", "Supabase"],
                category="AI/ML",
            ),
            Project(
                name="Distributed Task Scheduler",
                description="Built a distributed task scheduling system processing 1M+ jobs daily with fault tolerance",
                technologies=["Go", "Redis", "Kubernetes", "gRPC"],
                category="Systems",
            ),
        ],
        certifications=[
            Certification(name="AWS Solutions Architect – Associate", issuer="Amazon Web Services", year="2023"),
            Certification(name="Certified Kubernetes Administrator", issuer="CNCF", year="2022"),
        ],
    )


@pytest.fixture()
def sample_job_description():
    """A realistic software engineer job description."""
    return """
    Senior Software Engineer - Backend

    About the Role:
    We are looking for a Senior Software Engineer to join our platform team.
    You will design and build scalable microservices that power our core product.

    Requirements:
    - 5+ years of experience in software engineering
    - Strong proficiency in Python, Go, or Java
    - Experience with cloud platforms (AWS, GCP, or Azure)
    - Experience with containerization (Docker, Kubernetes)
    - Solid understanding of SQL and NoSQL databases (PostgreSQL, MongoDB, Redis)
    - Experience building RESTful APIs and microservices
    - Familiarity with CI/CD pipelines and infrastructure as code (Terraform)

    Nice to Have:
    - Experience with React or TypeScript
    - Knowledge of machine learning concepts
    - Open source contributions

    We offer:
    - Competitive salary ($180K - $250K)
    - Remote-friendly work environment
    - Generous equity package
    """


@pytest.fixture()
def sample_keywords():
    """Keywords that would be extracted from the sample JD."""
    return [
        "Python", "Go", "Java", "AWS", "Docker", "Kubernetes",
        "PostgreSQL", "MongoDB", "Redis", "REST API", "microservices",
        "CI/CD", "Terraform", "React", "TypeScript", "machine learning",
    ]


# ── Temporary File Fixtures ────────────────────────────

@pytest.fixture()
def tmp_dir() -> Generator:
    """Provide a temporary directory that's cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture()
def tmp_file(tmp_dir) -> Path:
    """Provide a temporary file path."""
    return tmp_dir / "test_resume.txt"


# ── Mock Fixtures ──────────────────────────────────────

@pytest.fixture()
def mock_llm_keywords():
    """Mock the LLM keyword extraction to return predictable results."""
    keywords = [
        "Python", "Go", "AWS", "Docker", "Kubernetes",
        "PostgreSQL", "MongoDB", "Redis", "microservices",
    ]
    with patch("src.llm.client_async.extract_keywords_async", new_callable=AsyncMock) as mock:
        mock.return_value = keywords
        yield mock


@pytest.fixture()
def mock_supabase():
    """Mock Supabase client for testing without a real DB."""
    with patch("src.db.client.get_supabase") as mock:
        mock.return_value = None  # Simulate no DB
        yield mock


# ── Session Fixture ────────────────────────────────────

@pytest.fixture()
def session_with_resume(client, sample_resume_data):
    """Set up a session with resume data pre-loaded in cache."""
    from src.api.deps import resume_data_cache, register_session

    session_id = "test-session-001"
    resume_data_cache[session_id] = sample_resume_data
    register_session(session_id)

    yield session_id

    # Cleanup
    resume_data_cache.pop(session_id, None)
