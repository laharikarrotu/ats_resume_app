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
    ats_compatible: bool = Field(
        default=True,
        description="Whether the generated resume passed ATS compatibility checks.",
    )
    ats_compatibility_score: int = Field(
        default=100,
        description="ATS compatibility score 0-100 (post-generation validation).",
    )
    ats_issues_count: int = Field(
        default=0,
        description="Number of ATS issues found in the generated resume.",
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


# ═══════════════════════════════════════════════════════════════
# ATS Analysis Models
# ═══════════════════════════════════════════════════════════════

class ATSFormatIssue(BaseModel):
    """A single ATS formatting issue found in the resume."""
    severity: str = Field(..., description="'critical', 'warning', or 'info'")
    category: str = Field(..., description="Category: 'formatting', 'content', 'structure', 'keywords'")
    message: str = Field(..., description="Human-readable description of the issue")
    suggestion: str = Field(default="", description="How to fix the issue")


class KeywordMatch(BaseModel):
    """Keyword match between job description and resume."""
    keyword: str = Field(..., description="The keyword/skill")
    found_in_resume: bool = Field(default=False, description="Whether this keyword appears in the resume")
    context: str = Field(default="", description="Where in the resume it was found")
    importance: str = Field(default="medium", description="'high', 'medium', or 'low' importance")


class SkillGap(BaseModel):
    """A skill gap between the job requirements and the resume."""
    skill: str = Field(..., description="The missing skill")
    importance: str = Field(default="medium", description="'critical', 'high', 'medium', or 'low'")
    suggestion: str = Field(default="", description="How to address this gap")
    related_skills: List[str] = Field(default_factory=list, description="Similar skills you DO have")


class BulletAnalysis(BaseModel):
    """Analysis of a single resume bullet point."""
    original: str = Field(..., description="Original bullet text")
    has_metrics: bool = Field(default=False, description="Contains quantifiable metrics")
    has_action_verb: bool = Field(default=False, description="Starts with a strong action verb")
    action_verb_suggestion: str = Field(default="", description="Suggested stronger action verb")
    metric_suggestion: str = Field(default="", description="Suggestion to add quantification")
    improved: str = Field(default="", description="Improved version of the bullet")
    score: int = Field(default=50, description="Quality score 0-100")


class ATSAnalysisResult(BaseModel):
    """Complete ATS analysis result for a resume against a job description."""
    # Overall Score
    overall_score: int = Field(default=0, description="Overall ATS score 0-100")
    score_breakdown: Dict[str, int] = Field(
        default_factory=dict,
        description="Score breakdown by category (keyword_match, formatting, content_quality, etc.)"
    )
    grade: str = Field(default="C", description="Letter grade: A+, A, B+, B, C+, C, D, F")

    # Keyword Analysis
    keyword_matches: List[KeywordMatch] = Field(default_factory=list, description="Keyword match details")
    keyword_match_percentage: float = Field(default=0.0, description="Percentage of JD keywords found")
    matched_keywords: List[str] = Field(default_factory=list, description="Keywords found in resume")
    missing_keywords: List[str] = Field(default_factory=list, description="Keywords NOT found in resume")

    # Skills Gap
    skill_gaps: List[SkillGap] = Field(default_factory=list, description="Skills gap analysis")

    # Format Issues
    format_issues: List[ATSFormatIssue] = Field(default_factory=list, description="ATS formatting issues")

    # Bullet Analysis
    bullet_analyses: List[BulletAnalysis] = Field(default_factory=list, description="Per-bullet analysis")
    bullets_with_metrics_pct: float = Field(default=0.0, description="% of bullets with quantifiable metrics")
    bullets_with_action_verbs_pct: float = Field(default=0.0, description="% of bullets starting with action verbs")

    # Recommendations
    top_recommendations: List[str] = Field(default_factory=list, description="Top 5 actionable recommendations")


class CoverLetterRequest(BaseModel):
    """Request to generate a cover letter."""
    job_description: str = Field(..., min_length=10, description="Job description text")
    company_name: str = Field(default="", description="Company name for personalization")
    job_title: str = Field(default="", description="Job title applying for")
    tone: str = Field(default="professional", description="'professional', 'enthusiastic', or 'conversational'")


class CoverLetterResponse(BaseModel):
    """Generated cover letter response."""
    cover_letter: str = Field(..., description="Generated cover letter text")
    word_count: int = Field(default=0, description="Word count")
    key_points: List[str] = Field(default_factory=list, description="Key points addressed")


class ResumeVersion(BaseModel):
    """A saved resume version for a specific job application."""
    version_id: str = Field(..., description="Unique version identifier")
    job_title: str = Field(default="", description="Target job title")
    company: str = Field(default="", description="Target company")
    created_at: str = Field(default="", description="Creation timestamp")
    filename: str = Field(default="", description="Generated file name")
    ats_score: int = Field(default=0, description="ATS score for this version")
    keywords_used: List[str] = Field(default_factory=list, description="Keywords used in this version")

