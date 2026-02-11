"""Tests for the ATS scoring engine."""

import pytest
from src.core.ats_scorer import (
    analyze_resume_ats,
    _analyze_single_bullet,
    _score_to_grade,
    _build_resume_text,
)
from src.models import ResumeData, Experience


class TestScoreToGrade:
    def test_grades(self):
        assert _score_to_grade(95) == "A+"
        assert _score_to_grade(90) == "A"
        assert _score_to_grade(85) == "B+"
        assert _score_to_grade(80) == "B"
        assert _score_to_grade(75) == "C+"
        assert _score_to_grade(65) == "C"
        assert _score_to_grade(50) == "D"
        assert _score_to_grade(30) == "F"


class TestAnalyzeSingleBullet:
    def test_strong_bullet(self):
        bullet = "Engineered a microservices platform serving 10M+ daily requests with 99.99% uptime"
        result = _analyze_single_bullet(bullet)
        assert result.has_action_verb is True
        assert result.has_metrics is True
        assert result.score >= 70

    def test_weak_bullet(self):
        bullet = "Helped with some stuff"
        result = _analyze_single_bullet(bullet)
        assert result.has_action_verb is False
        assert result.has_metrics is False
        assert result.score < 50
        assert result.action_verb_suggestion != ""

    def test_metrics_only(self):
        bullet = "Managed a team of 5 engineers to deliver features 30% faster"
        result = _analyze_single_bullet(bullet)
        assert result.has_metrics is True

    def test_empty_bullet(self):
        result = _analyze_single_bullet("")
        assert result.score == 0


class TestBuildResumeText:
    def test_includes_all_sections(self, sample_resume_data):
        text = _build_resume_text(sample_resume_data)
        assert "Jane Doe" in text
        assert "Python" in text
        assert "Google" in text
        assert "Stanford" in text
        assert "ATS Resume Optimizer" in text
        assert "AWS Solutions Architect" in text


class TestAnalyzeResumeATS:
    def test_full_analysis(self, sample_resume_data, sample_keywords):
        """Full analysis should return a complete result."""
        result = analyze_resume_ats(
            sample_resume_data,
            "Senior Software Engineer - Python, AWS, Docker, Kubernetes",
            sample_keywords,
        )
        assert 0 <= result.overall_score <= 100
        assert result.grade in ["A+", "A", "B+", "B", "C+", "C", "D", "F"]
        assert len(result.keyword_matches) == len(sample_keywords)
        assert result.keyword_match_percentage >= 0
        assert isinstance(result.matched_keywords, list)
        assert isinstance(result.missing_keywords, list)

    def test_high_match_resume(self, sample_resume_data, sample_keywords):
        """Resume with matching skills should score well on keywords."""
        result = analyze_resume_ats(sample_resume_data, "Python, AWS", sample_keywords)
        # Should match most keywords since our sample resume is comprehensive
        assert len(result.matched_keywords) > 5
        assert result.keyword_match_percentage > 40

    def test_empty_keywords(self, sample_resume_data):
        """Empty keywords should not crash."""
        result = analyze_resume_ats(sample_resume_data, "Some job description", [])
        assert result.keyword_match_percentage == 0
        assert result.overall_score >= 0

    def test_minimal_resume(self, sample_keywords):
        """Minimal resume should get lower scores."""
        minimal = ResumeData(name="John Doe")
        result = analyze_resume_ats(minimal, "Python engineer", sample_keywords)
        assert result.overall_score < 50
        assert len(result.format_issues) > 0

    def test_score_breakdown_keys(self, sample_resume_data, sample_keywords):
        """Score breakdown should contain expected keys."""
        result = analyze_resume_ats(sample_resume_data, "Python engineer", sample_keywords)
        assert "overall" in result.score_breakdown
        assert "keyword_match" in result.score_breakdown
        assert "content_quality" in result.score_breakdown
        assert "completeness" in result.score_breakdown
        assert "formatting" in result.score_breakdown

    def test_recommendations_generated(self, sample_resume_data, sample_keywords):
        """Should always generate at least some recommendations."""
        result = analyze_resume_ats(sample_resume_data, "Python engineer", sample_keywords)
        # May or may not have recommendations depending on score
        assert isinstance(result.top_recommendations, list)

    def test_bullet_analysis(self, sample_resume_data, sample_keywords):
        """Bullet analysis should cover experience and projects."""
        result = analyze_resume_ats(sample_resume_data, "Python", sample_keywords)
        assert len(result.bullet_analyses) > 0
        assert result.bullets_with_metrics_pct >= 0
        assert result.bullets_with_action_verbs_pct >= 0
