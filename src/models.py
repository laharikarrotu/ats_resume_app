from typing import List, Dict, Optional

from pydantic import BaseModel, Field


class JobDescriptionRequest(BaseModel):
    job_description: str = Field(
        ...,
        min_length=10,
        description="Raw job description text pasted by user or recruiter.",
    )


class ResumeResponse(BaseModel):
    download_path: str = Field(
        ...,
        description="Relative path to download the generated resume DOCX.",
    )
    keywords: List[str] = Field(
        ...,
        description="Keywords extracted from the job description.",
    )


# Resume Data Models for Parsing
class Education(BaseModel):
    degree: str = Field(..., description="Degree name (e.g., 'Master's in Computer Science')")
    university: str = Field(default="", description="University name")
    location: str = Field(default="", description="University location")
    dates: str = Field(default="", description="Date range (e.g., '2022-2024')")
    gpa: str = Field(default="", description="GPA if mentioned")
    coursework: List[str] = Field(default_factory=list, description="List of relevant coursework")


class Experience(BaseModel):
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    dates: str = Field(default="", description="Date range (e.g., 'May 2025 - Present')")
    bullets: List[str] = Field(default_factory=list, description="Achievement bullet points")


class Project(BaseModel):
    name: str = Field(..., description="Project name")
    description: str = Field(default="", description="Project description")
    technologies: List[str] = Field(default_factory=list, description="Technologies used")
    category: str = Field(default="", description="Project category/domain")


class Certification(BaseModel):
    name: str = Field(..., description="Certification name")
    issuer: str = Field(default="", description="Issuing organization")
    year: str = Field(default="", description="Year obtained")


class ResumeData(BaseModel):
    """Structured resume data extracted from uploaded resume file."""
    name: str = Field(..., description="Full name")
    email: str = Field(default="", description="Email address")
    phone: str = Field(default="", description="Phone number")
    linkedin: str = Field(default="", description="LinkedIn profile URL")
    github: str = Field(default="", description="GitHub profile URL")
    location: str = Field(default="", description="Location (city, state)")
    education: List[Education] = Field(default_factory=list, description="Education history")
    skills: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Technical skills organized by category (e.g., 'Programming': ['Python', 'Java'])"
    )
    experience: List[Experience] = Field(default_factory=list, description="Work experience")
    projects: List[Project] = Field(default_factory=list, description="Projects")
    certifications: List[Certification] = Field(default_factory=list, description="Certifications")


