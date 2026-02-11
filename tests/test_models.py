"""Tests for Pydantic models — validation, defaults, serialization."""

import pytest
from src.models import (
    ResumeData,
    Education,
    Experience,
    Project,
    Certification,
    ATSAnalysisResult,
    ATSFormatIssue,
    KeywordMatch,
    SkillGap,
    BulletAnalysis,
    ResumeResponse,
    CoverLetterRequest,
    CoverLetterResponse,
    ResumeVersion,
    JobDescriptionRequest,
)


class TestResumeData:
    """Tests for the ResumeData model."""

    def test_minimal_resume(self):
        """A resume with only a name should be valid."""
        data = ResumeData(name="John Doe")
        assert data.name == "John Doe"
        assert data.email == ""
        assert data.skills == {}
        assert data.experience == []

    def test_full_resume(self, sample_resume_data):
        """Full resume should serialize and have correct counts."""
        d = sample_resume_data
        assert d.name == "Jane Doe"
        assert len(d.education) == 2
        assert len(d.experience) == 2
        assert len(d.projects) == 2
        assert len(d.certifications) == 2
        assert "Python" in d.skills.get("Programming Languages", [])

    def test_resume_model_dump(self, sample_resume_data):
        """Model should round-trip through dict serialization."""
        dumped = sample_resume_data.model_dump()
        restored = ResumeData(**dumped)
        assert restored.name == sample_resume_data.name
        assert len(restored.experience) == len(sample_resume_data.experience)

    def test_resume_json_round_trip(self, sample_resume_data):
        """Model should round-trip through JSON."""
        json_str = sample_resume_data.model_dump_json()
        restored = ResumeData.model_validate_json(json_str)
        assert restored.name == sample_resume_data.name


class TestEducation:
    def test_defaults(self):
        edu = Education(degree="BS CS")
        assert edu.university == ""
        assert edu.gpa == ""
        assert edu.coursework == []


class TestExperience:
    def test_with_bullets(self):
        exp = Experience(
            title="Engineer",
            company="Acme",
            bullets=["Built X", "Led Y"],
        )
        assert len(exp.bullets) == 2
        assert exp.dates == ""


class TestProject:
    def test_defaults(self):
        proj = Project(name="My Project")
        assert proj.technologies == []
        assert proj.category == ""


class TestATSAnalysisResult:
    def test_defaults(self):
        result = ATSAnalysisResult()
        assert result.overall_score == 0
        assert result.grade == "C"
        assert result.keyword_matches == []
        assert result.top_recommendations == []

    def test_full_result(self):
        result = ATSAnalysisResult(
            overall_score=85,
            grade="B+",
            keyword_match_percentage=72.5,
            matched_keywords=["Python", "AWS"],
            missing_keywords=["Go"],
            format_issues=[
                ATSFormatIssue(severity="warning", category="formatting", message="Test issue")
            ],
            skill_gaps=[
                SkillGap(skill="Go", importance="high", suggestion="Learn Go")
            ],
            bullet_analyses=[
                BulletAnalysis(original="Built X", has_metrics=True, score=80)
            ],
        )
        assert result.overall_score == 85
        assert len(result.format_issues) == 1
        assert result.format_issues[0].severity == "warning"


class TestResumeResponse:
    def test_with_ats_metadata(self):
        resp = ResumeResponse(
            download_path="/download/test.docx",
            keywords=["Python"],
            ats_compatible=True,
            ats_compatibility_score=92,
            ats_issues_count=1,
        )
        assert resp.ats_compatible is True
        assert resp.ats_compatibility_score == 92


class TestJobDescriptionRequest:
    def test_valid(self):
        req = JobDescriptionRequest(job_description="This is a valid job description with enough text.")
        assert len(req.job_description) > 10

    def test_too_short(self):
        with pytest.raises(Exception):
            JobDescriptionRequest(job_description="short")


class TestCoverLetterModels:
    def test_request(self):
        req = CoverLetterRequest(
            job_description="Senior Engineer at Acme Corp building scalable systems.",
            company_name="Acme",
            job_title="Senior Engineer",
            tone="professional",
        )
        assert req.tone == "professional"

    def test_response(self):
        resp = CoverLetterResponse(
            cover_letter="Dear Hiring Manager...",
            word_count=150,
            key_points=["Experience", "Skills"],
        )
        assert resp.word_count == 150
