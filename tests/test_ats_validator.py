"""Tests for the ATS output validator."""

import pytest
from src.core.ats_validator import (
    validate_resume_output,
    sanitize_for_ats,
    ATSValidationResult,
)
from src.models import ResumeData


GOOD_RESUME_TEXT = """
Jane Doe
jane.doe@example.com | (555) 123-4567 | San Francisco, CA | linkedin.com/in/janedoe

WORK EXPERIENCE

Senior Software Engineer — Google
Jan 2023 - Present
• Architected a microservices platform serving 10M+ daily requests with 99.99% uptime
• Led a team of 5 engineers to deliver a real-time data pipeline reducing latency by 60%
• Implemented CI/CD pipelines using GitHub Actions and Terraform

Software Engineer — Meta
Jun 2022 - Dec 2022
• Developed RESTful APIs using Python and FastAPI serving 5M+ requests per day
• Built React components for the internal developer tools platform

EDUCATION

Master of Science in Computer Science — Stanford University
2020 - 2022 | GPA: 3.9

SKILLS

Programming Languages: Python, Java, TypeScript, Go
Frameworks: FastAPI, React, Spring Boot, Django
Cloud & DevOps: AWS, Docker, Kubernetes, Terraform
Databases: PostgreSQL, MongoDB, Redis

PROJECTS

ATS Resume Optimizer
AI-powered resume optimization tool using LLMs

CERTIFICATIONS

AWS Solutions Architect – Associate | Amazon Web Services | 2023
"""

MINIMAL_RESUME_TEXT = """
John Doe
Some text here but not much.
"""


class TestValidateResumeOutput:
    def test_good_resume(self):
        """A well-formatted resume should pass validation."""
        result = validate_resume_output(GOOD_RESUME_TEXT)
        assert result.ats_compatible is True
        assert result.compatibility_score >= 70
        assert result.checks_passed > 0

    def test_section_detection(self):
        """Should detect standard sections."""
        result = validate_resume_output(GOOD_RESUME_TEXT)
        assert result.section_detection.get("experience") is True
        assert result.section_detection.get("education") is True
        assert result.section_detection.get("skills") is True

    def test_contact_parsing(self):
        """Should parse contact info from good resume."""
        result = validate_resume_output(GOOD_RESUME_TEXT)
        assert result.contact_parsed.get("email") is True
        assert result.contact_parsed.get("phone") is True

    def test_minimal_resume_fails(self):
        """A minimal resume should have issues."""
        result = validate_resume_output(MINIMAL_RESUME_TEXT)
        assert len(result.issues) > 0
        # Should flag missing sections
        has_section_issue = any(
            i.check == "section_detection" for i in result.issues
        )
        assert has_section_issue

    def test_empty_text(self):
        """Empty text should fail validation."""
        result = validate_resume_output("")
        assert result.ats_compatible is False
        assert result.compatibility_score < 70

    def test_keyword_density(self):
        """Should check keyword density when keywords provided."""
        keywords = ["Python", "AWS", "Docker", "Kubernetes", "GraphQL", "Rust"]
        result = validate_resume_output(GOOD_RESUME_TEXT, keywords=keywords)
        assert len(result.keyword_density) > 0
        assert result.keyword_density.get("Python", 0) > 0

    def test_special_characters_detected(self):
        """Should detect ATS-breaking special characters."""
        text_with_special = GOOD_RESUME_TEXT + "\n★ Special achievement ► Arrow"
        result = validate_resume_output(text_with_special)
        has_char_issue = any(
            i.check == "special_characters" for i in result.issues
        )
        assert has_char_issue

    def test_resume_data_verification(self):
        """Should verify contact info against original data."""
        resume_data = ResumeData(
            name="Jane Doe",
            email="jane.doe@example.com",
            phone="(555) 123-4567",
        )
        result = validate_resume_output(GOOD_RESUME_TEXT, resume_data=resume_data)
        # Email and phone are in the text, so no issues
        email_mismatch = any(
            "Original email" in i.message for i in result.issues
        )
        assert email_mismatch is False

    def test_resume_data_mismatch(self):
        """Should flag when original data doesn't match output."""
        resume_data = ResumeData(
            name="Jane Doe",
            email="totally.different@email.com",
        )
        result = validate_resume_output(GOOD_RESUME_TEXT, resume_data=resume_data)
        email_mismatch = any(
            "Original email" in i.message for i in result.issues
        )
        assert email_mismatch is True


class TestSanitizeForATS:
    def test_smart_quotes(self):
        result = sanitize_for_ats("He said \u201chello\u201d")
        assert "\u201c" not in result
        assert "\u201d" not in result
        assert '"hello"' in result

    def test_em_dash(self):
        result = sanitize_for_ats("Senior Engineer \u2014 Google")
        assert "\u2014" not in result
        assert "--" in result

    def test_en_dash(self):
        result = sanitize_for_ats("2020 \u2013 2022")
        assert "\u2013" not in result
        assert "-" in result

    def test_special_bullets(self):
        result = sanitize_for_ats("★ Achievement\n► Next item")
        assert "★" not in result
        assert "►" not in result

    def test_zero_width_chars(self):
        result = sanitize_for_ats("hello\u200bworld\ufeff")
        assert "\u200b" not in result
        assert "\ufeff" not in result

    def test_multiple_spaces(self):
        result = sanitize_for_ats("hello    world")
        assert "    " not in result
        assert "hello world" in result

    def test_excessive_newlines(self):
        result = sanitize_for_ats("hello\n\n\n\n\nworld")
        assert "\n\n\n" not in result
