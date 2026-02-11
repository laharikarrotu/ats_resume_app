from typing import List, Dict, Optional
from datetime import datetime

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
    degree: str = Field(..., description="Degree name")
    university: str = Field(default="", description="University name")
    location: str = Field(default="", description="University location")
    dates: str = Field(default="", description="Date range")
    gpa: str = Field(default="", description="GPA if mentioned")
    coursework: List[str] = Field(default_factory=list, description="Relevant coursework")


class Experience(BaseModel):
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    dates: str = Field(default="", description="Date range")
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
        description="Technical skills organized by category"
    )
    experience: List[Experience] = Field(default_factory=list, description="Work experience")
    projects: List[Project] = Field(default_factory=list, description="Projects")
    certifications: List[Certification] = Field(default_factory=list, description="Certifications")


# ATS Analysis Models

class ATSFormatIssue(BaseModel):
    severity: str = Field(..., description="critical, warning, or info")
    category: str = Field(..., description="formatting, content, structure, keywords")
    message: str = Field(..., description="Human-readable description")
    suggestion: str = Field(default="", description="How to fix")


class KeywordMatch(BaseModel):
    keyword: str = Field(..., description="The keyword/skill")
    found_in_resume: bool = Field(default=False)
    context: str = Field(default="", description="Where found in resume")
    importance: str = Field(default="medium", description="high, medium, or low")


class SkillGap(BaseModel):
    skill: str = Field(..., description="The missing skill")
    importance: str = Field(default="medium", description="critical, high, medium, low")
    suggestion: str = Field(default="", description="How to address this gap")
    related_skills: List[str] = Field(default_factory=list, description="Similar skills you have")


class BulletAnalysis(BaseModel):
    original: str = Field(..., description="Original bullet text")
    has_metrics: bool = Field(default=False)
    has_action_verb: bool = Field(default=False)
    action_verb_suggestion: str = Field(default="")
    metric_suggestion: str = Field(default="")
    improved: str = Field(default="", description="Improved version")
    score: int = Field(default=50, description="Quality score 0-100")


class ATSAnalysisResult(BaseModel):
    overall_score: int = Field(default=0, description="Overall ATS score 0-100")
    score_breakdown: Dict[str, int] = Field(default_factory=dict)
    grade: str = Field(default="C", description="Letter grade")
    keyword_matches: List[KeywordMatch] = Field(default_factory=list)
    keyword_match_percentage: float = Field(default=0.0)
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    skill_gaps: List[SkillGap] = Field(default_factory=list)
    format_issues: List[ATSFormatIssue] = Field(default_factory=list)
    bullet_analyses: List[BulletAnalysis] = Field(default_factory=list)
    bullets_with_metrics_pct: float = Field(default=0.0)
    bullets_with_action_verbs_pct: float = Field(default=0.0)
    top_recommendations: List[str] = Field(default_factory=list)


class CoverLetterRequest(BaseModel):
    job_description: str = Field(..., min_length=10)
    company_name: str = Field(default="")
    job_title: str = Field(default="")
    tone: str = Field(default="professional")


class CoverLetterResponse(BaseModel):
    cover_letter: str = Field(..., description="Generated cover letter text")
    word_count: int = Field(default=0)
    key_points: List[str] = Field(default_factory=list)


class ResumeVersion(BaseModel):
    version_id: str = Field(..., description="Unique version identifier")
    job_title: str = Field(default="")
    company: str = Field(default="")
    created_at: str = Field(default="")
    filename: str = Field(default="")
    ats_score: int = Field(default=0)
    keywords_used: List[str] = Field(default_factory=list)
