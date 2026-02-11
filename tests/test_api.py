"""Integration tests for API endpoints."""

import pytest
from unittest.mock import patch, AsyncMock


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "llm" in data
        assert "database" in data

    def test_health_has_rate_limit(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "rate_limit" in data


class TestStatsEndpoint:
    def test_stats_returns_counts(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_sessions" in data
        assert "db_enabled" in data


class TestUploadEndpoint:
    def test_upload_text(self, client):
        """Should parse pasted resume text."""
        resp = client.post(
            "/upload_resume_text/",
            data={"resume_text": """
                Jane Doe
                jane@example.com | (555) 123-4567

                EXPERIENCE
                Software Engineer at Acme Corp
                Jan 2023 - Present
                - Built microservices with Python
                - Deployed to AWS using Docker

                EDUCATION
                BS in Computer Science - MIT, 2022

                SKILLS
                Python, Java, AWS, Docker, Kubernetes
            """},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["message"] == "Resume text parsed successfully"

    def test_upload_empty_text(self, client):
        """Should reject empty text."""
        resp = client.post(
            "/upload_resume_text/",
            data={"resume_text": ""},
        )
        assert resp.status_code == 400

    def test_upload_unsupported_file(self, client):
        """Should reject unsupported file types."""
        resp = client.post(
            "/upload_resume/",
            files={"file": ("test.xyz", b"content", "application/octet-stream")},
        )
        assert resp.status_code == 400


class TestResumeDataEndpoint:
    def test_get_resume_data(self, client, session_with_resume):
        """Should return parsed resume data."""
        resp = client.get(f"/api/resume_data?session_id={session_with_resume}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Jane Doe"
        assert "skills" in data
        assert "experience" in data

    def test_get_resume_data_missing_session(self, client):
        """Should 404 for nonexistent session."""
        resp = client.get("/api/resume_data?session_id=nonexistent")
        assert resp.status_code == 404


class TestAnalyzeEndpoint:
    @patch("src.api.analyze.extract_keywords_async", new_callable=AsyncMock)
    @patch("src.api.analyze.extract_keywords_async_optimized", new_callable=AsyncMock)
    def test_analyze_resume(self, mock_optimized, mock_basic, client, session_with_resume):
        """Should return ATS analysis."""
        mock_optimized.return_value = ["Python", "AWS", "Docker"]
        resp = client.post(
            "/api/analyze",
            data={
                "job_description": "Senior Python Engineer with AWS and Docker experience",
                "session_id": session_with_resume,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_score" in data
        assert "grade" in data
        assert "keyword_matches" in data
        assert "format_issues" in data

    def test_analyze_missing_session(self, client):
        """Should 404 for nonexistent session."""
        resp = client.post(
            "/api/analyze",
            data={
                "job_description": "Python engineer with AWS experience",
                "session_id": "nonexistent",
            },
        )
        assert resp.status_code == 404


class TestVersionsEndpoint:
    def test_get_versions_empty(self, client, session_with_resume):
        """Should return empty versions list."""
        resp = client.get(f"/api/versions?session_id={session_with_resume}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["versions"] == []


class TestValidateEndpoint:
    def test_validate_text(self, client):
        """Should validate resume text for ATS compatibility."""
        resp = client.post(
            "/api/validate/text",
            data={
                "resume_text": "Jane Doe\njane@example.com | (555) 123-4567 | San Francisco, CA\n\nWORK EXPERIENCE\nSoftware Engineer at Google, Jan 2023 - Present\n- Developed APIs serving 10M users with Python and FastAPI\n- Built microservices deployed to Kubernetes on AWS\n\nEDUCATION\nBS Computer Science - MIT 2022\n\nSKILLS\nPython, Java, AWS, Docker, Kubernetes, React, TypeScript",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "ats_compatible" in data
        assert "compatibility_score" in data
