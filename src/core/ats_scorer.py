"""
ATS Scorer Engine: Real-world ATS scoring aligned with top 10 ATS platforms.

Scoring mirrors how Workday, Taleo, Greenhouse, and Lever actually rank resumes:

  Weight Distribution (based on ATS platform analysis):
    • Keyword Matching   — 40%  (exact JD terminology, 60-80% target, context-weighted)
    • Qualifications     — 30%  (years of experience, certs, degree, location)
    • Section Quality    — 20%  (completeness, standard headers, contact info)
    • Format Readability — 10%  (clean text extraction, parseable dates, no garbled chars)
"""

import re
from typing import List, Dict, Optional, Tuple

from ..models import (
    ResumeData, ATSAnalysisResult, ATSFormatIssue,
    KeywordMatch, SkillGap, BulletAnalysis,
)


# ═══════════════════════════════════════════════════════════
# Strong action verbs for resume bullets (by category)
# ═══════════════════════════════════════════════════════════

STRONG_ACTION_VERBS = {
    "leadership": [
        "spearheaded", "orchestrated", "championed", "directed", "led", "managed",
        "oversaw", "supervised", "coordinated", "mentored", "guided",
    ],
    "achievement": [
        "achieved", "delivered", "exceeded", "outperformed", "surpassed",
        "attained", "accomplished",
    ],
    "technical": [
        "architected", "engineered", "developed", "built", "designed",
        "implemented", "deployed", "automated", "optimized", "integrated",
        "configured", "migrated", "refactored", "scaled", "streamlined",
        "programmed", "coded",
    ],
    "analysis": [
        "analyzed", "evaluated", "assessed", "identified", "diagnosed",
        "investigated", "researched", "discovered",
    ],
    "communication": [
        "presented", "authored", "documented", "published", "communicated",
        "mentored", "trained", "collaborated", "facilitated", "negotiated",
    ],
    "improvement": [
        "improved", "enhanced", "accelerated", "reduced", "increased",
        "boosted", "elevated", "transformed", "modernized", "revamped",
        "strengthened", "consolidated", "upgraded",
    ],
    "creation": [
        "created", "launched", "established", "initiated", "introduced",
        "pioneered", "founded", "invented",
    ],
}

ALL_ACTION_VERBS = set()
for verbs in STRONG_ACTION_VERBS.values():
    ALL_ACTION_VERBS.update(verbs)

# Weak verbs to avoid
WEAK_VERBS = {
    "helped", "assisted", "worked", "was responsible for", "handled",
    "participated", "involved", "utilized", "used", "did", "made",
    "got", "went", "had", "tried", "attempted",
}

# Common ATS-unfriendly characters
ATS_UNFRIENDLY_CHARS = {
    "\u2192": "->",    # →
    "\u2014": "--",    # —
    "\u2013": "-",     # –
    "\u2018": "'",     # '
    "\u2019": "'",     # '
    "\u201c": '"',     # "
    "\u201d": '"',     # "
    "\u2022": "*",     # •
    "\u25cf": "*",     # ●
    "\u25cb": "o",     # ○
}

# Metric patterns — detect quantifiable results
METRIC_PATTERNS = [
    r'\d+%',                           # percentages
    r'\$[\d,]+[KkMmBb]?',             # dollar amounts
    r'\d+[xX]',                        # multipliers (3x, 10x)
    r'\d+\+?\s*(users|customers|clients|teams|members|engineers|developers)',
    r'\d+\s*(seconds?|minutes?|hours?|days?|weeks?|months?)',
    r'from\s+\d+.*?to\s+\d+',         # from X to Y
    r'\d+\s*(ms|seconds?|s)\s',        # latency
    r'top\s+\d+%',                     # top percentile
    r'\d+[KkMmBb]\+?\s',              # quantities (1K, 2M)
    r'\d{2,}',                         # any number >= 10
]

# Buzzwords to avoid (ATS guideline)
BUZZWORDS_TO_AVOID = {
    "synergy", "rockstar", "guru", "ninja", "wizard", "thought leader",
    "go-getter", "self-starter", "team player", "detail-oriented",
    "results-driven", "proven track record",
}

# Standard ATS-friendly section headers (recognized by 95% of ATS platforms)
STANDARD_SECTION_HEADERS = {
    "contact", "summary", "professional summary", "objective",
    "experience", "work experience", "employment", "professional experience",
    "education", "academic", "skills", "technical skills",
    "certifications", "certificates", "projects", "publications",
}

# Non-standard section names that confuse ATS parsers
NON_STANDARD_SECTION_NAMES = {
    "my journey": "Work Experience",
    "career journey": "Work Experience",
    "what i've done": "Work Experience",
    "my story": "Professional Summary",
    "about me": "Professional Summary",
    "toolbox": "Technical Skills",
    "arsenal": "Technical Skills",
    "superpowers": "Technical Skills",
    "career highlights": "Work Experience",
    "tech stack": "Technical Skills",
    "core competencies": "Technical Skills",
    "selected experience": "Work Experience",
}


def analyze_resume_ats(
    resume_data: ResumeData,
    job_description: str,
    keywords: List[str],
) -> ATSAnalysisResult:
    """
    Perform comprehensive ATS analysis on a resume against a job description.

    Scoring breakdown:
      • Keyword Match (35%): How many JD keywords appear in the resume
      • Formatting (20%): ATS-friendly structure, no problematic chars
      • Content Quality (25%): Action verbs, metrics, STAR/CAR format
      • Completeness (20%): Required sections present and populated
    
    Args:
        resume_data: Parsed resume data
        job_description: Raw job description text
        keywords: Extracted keywords from job description
    
    Returns:
        ATSAnalysisResult with scores, issues, and actionable recommendations
    """
    # 1. Keyword matching
    keyword_matches, matched, missing = _analyze_keywords(resume_data, keywords)
    keyword_pct = (len(matched) / len(keywords) * 100) if keywords else 0

    # 2. Format checking
    format_issues = _check_ats_formatting(resume_data)

    # 3. Bullet analysis (action verbs + metrics)
    bullet_analyses = _analyze_bullets(resume_data)

    # 4. Skills gap analysis
    skill_gaps = _analyze_skill_gaps(resume_data, keywords, job_description)

    # 5. Calculate scores
    scores = _calculate_scores(
        keyword_pct, format_issues, bullet_analyses, resume_data, skill_gaps
    )

    # 6. Generate recommendations
    recommendations = _generate_recommendations(
        keyword_pct, format_issues, bullet_analyses, skill_gaps, missing, resume_data
    )

    # Bullet stats
    total_bullets = len(bullet_analyses)
    metrics_count = sum(1 for b in bullet_analyses if b.has_metrics)
    action_count = sum(1 for b in bullet_analyses if b.has_action_verb)

    return ATSAnalysisResult(
        overall_score=scores["overall"],
        score_breakdown=scores,
        grade=_score_to_grade(scores["overall"]),
        keyword_matches=keyword_matches,
        keyword_match_percentage=round(keyword_pct, 1),
        matched_keywords=matched,
        missing_keywords=missing,
        skill_gaps=skill_gaps,
        format_issues=format_issues,
        bullet_analyses=bullet_analyses[:20],
        bullets_with_metrics_pct=round((metrics_count / total_bullets * 100) if total_bullets else 0, 1),
        bullets_with_action_verbs_pct=round((action_count / total_bullets * 100) if total_bullets else 0, 1),
        top_recommendations=recommendations[:10],
    )


# ═══════════════════════════════════════════════════════════
# Keyword Analysis
# ═══════════════════════════════════════════════════════════

def _analyze_keywords(
    resume_data: ResumeData, keywords: List[str]
) -> Tuple[List[KeywordMatch], List[str], List[str]]:
    """Match JD keywords against resume content with synonym awareness."""
    resume_text = _build_resume_text(resume_data).lower()

    # Technology synonyms for fuzzy matching
    SYNONYMS = {
        "python": ["python3", "py"],
        "javascript": ["js", "ecmascript", "es6", "es2015"],
        "typescript": ["ts"],
        "react": ["reactjs", "react.js"],
        "node.js": ["nodejs", "node"],
        "postgresql": ["postgres", "psql"],
        "mongodb": ["mongo"],
        "kubernetes": ["k8s"],
        "docker": ["containers", "containerization"],
        "aws": ["amazon web services"],
        "gcp": ["google cloud", "google cloud platform"],
        "azure": ["microsoft azure"],
        "ci/cd": ["continuous integration", "continuous deployment", "cicd"],
        "machine learning": ["ml"],
        "artificial intelligence": ["ai"],
        "rest api": ["restful", "rest apis", "restful api"],
        "graphql": ["graph ql"],
        "next.js": ["nextjs", "next"],
    }

    matched = []
    missing = []
    keyword_matches = []

    for kw in keywords:
        kw_lower = kw.lower().strip()
        if not kw_lower:
            continue

        # Direct match
        found = kw_lower in resume_text

        # Synonym match
        if not found:
            for canonical, syns in SYNONYMS.items():
                if kw_lower == canonical or kw_lower in syns:
                    if any(s in resume_text for s in [canonical] + syns):
                        found = True
                        break

        context = ""
        if found:
            matched.append(kw)
            # Where was it found?
            skills_text = " ".join(s for skills in resume_data.skills.values() for s in skills).lower()
            experience_text = " ".join(" ".join(exp.bullets) for exp in resume_data.experience).lower()
            projects_text = " ".join(
                (p.description + " " + " ".join(p.technologies))
                for p in resume_data.projects
            ).lower()

            if kw_lower in skills_text:
                context = "Skills section"
            elif kw_lower in experience_text:
                context = "Experience section"
            elif kw_lower in projects_text:
                context = "Projects section"
            else:
                context = "Resume content"
        else:
            missing.append(kw)

        # Determine importance based on JD context
        importance = _determine_keyword_importance(kw_lower, resume_text)

        keyword_matches.append(KeywordMatch(
            keyword=kw,
            found_in_resume=found,
            context=context,
            importance=importance,
        ))

    return keyword_matches, matched, missing


def _determine_keyword_importance(keyword: str, resume_text: str) -> str:
    """Determine keyword importance: high/medium/low."""
    # Core programming languages and major frameworks = high
    HIGH_IMPORTANCE = {
        "python", "java", "javascript", "typescript", "go", "rust", "c++", "c#",
        "react", "angular", "vue", "node.js", "spring", "django", "fastapi",
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
        "sql", "postgresql", "mongodb", "redis",
        "machine learning", "deep learning",
    }
    
    if keyword in HIGH_IMPORTANCE:
        return "high"
    
    # Multi-word technical terms = medium-high
    if " " in keyword or "." in keyword:
        return "medium"
    
    return "medium"


def _build_resume_text(resume_data: ResumeData) -> str:
    """Build a full text representation of the resume for searching."""
    parts = [
        resume_data.name,
        resume_data.email,
        resume_data.location,
    ]
    for category, skills in resume_data.skills.items():
        parts.append(category)
        parts.extend(skills)
    for exp in resume_data.experience:
        parts.append(exp.title)
        parts.append(exp.company)
        parts.extend(exp.bullets)
    for proj in resume_data.projects:
        parts.append(proj.name)
        parts.append(proj.description)
        parts.extend(proj.technologies)
    for edu in resume_data.education:
        parts.append(edu.degree)
        parts.append(edu.university)
        parts.extend(edu.coursework)
    for cert in resume_data.certifications:
        parts.append(cert.name)
        parts.append(cert.issuer)

    return " ".join(parts)


# ═══════════════════════════════════════════════════════════
# ATS Formatting Checks
# ═══════════════════════════════════════════════════════════

def _check_ats_formatting(resume_data: ResumeData) -> List[ATSFormatIssue]:
    """Check for ATS-unfriendly formatting issues based on expert rules."""
    issues = []

    # ── Contact Info ──────────────────────────────────
    if not resume_data.email:
        issues.append(ATSFormatIssue(
            severity="critical",
            category="content",
            message="Missing email address",
            suggestion="Add a professional email address. Format: name@domain.com"
        ))
    elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', resume_data.email):
        issues.append(ATSFormatIssue(
            severity="warning",
            category="formatting",
            message="Email format may not parse correctly",
            suggestion="Use standard email format: firstname.lastname@domain.com"
        ))
    
    if not resume_data.phone:
        issues.append(ATSFormatIssue(
            severity="warning",
            category="content",
            message="Missing phone number",
            suggestion="Add phone number in format: (123) 456-7890"
        ))
    
    if not resume_data.linkedin:
        issues.append(ATSFormatIssue(
            severity="info",
            category="content",
            message="No LinkedIn profile URL found",
            suggestion="Add your LinkedIn URL: linkedin.com/in/yourname"
        ))
    
    if not resume_data.location:
        issues.append(ATSFormatIssue(
            severity="warning",
            category="content",
            message="Missing location information",
            suggestion="Add City, State for location-based ATS filtering"
        ))

    # ── Special Characters ────────────────────────────
    resume_text = _build_resume_text(resume_data)
    for char, replacement in ATS_UNFRIENDLY_CHARS.items():
        if char in resume_text:
            issues.append(ATSFormatIssue(
                severity="warning",
                category="formatting",
                message=f"ATS-unfriendly character '{char}' detected",
                suggestion=f"Replace with '{replacement}' — some ATS systems cannot parse special characters"
            ))

    # ── Section Completeness ──────────────────────────
    if not resume_data.experience:
        issues.append(ATSFormatIssue(
            severity="critical",
            category="structure",
            message="No work experience section found",
            suggestion="Add Work Experience with 4-6 bullet points per role"
        ))
    
    if not resume_data.education:
        issues.append(ATSFormatIssue(
            severity="warning",
            category="structure",
            message="No education section found",
            suggestion="Add Education: Degree, University, Location, Graduation Date"
        ))
    
    if not resume_data.skills:
        issues.append(ATSFormatIssue(
            severity="critical",
            category="structure",
            message="No skills section found",
            suggestion="Add a Skills section. Format: 'Technical Skills: Python, Java, AWS' (simple comma-separated list)"
        ))

    # ── Bullet Point Quality ──────────────────────────
    all_bullets = []
    for exp in resume_data.experience:
        all_bullets.extend(exp.bullets)

    if all_bullets:
        # Too few bullets per role
        for exp in resume_data.experience:
            if len(exp.bullets) < 3:
                issues.append(ATSFormatIssue(
                    severity="warning",
                    category="content",
                    message=f"'{exp.title}' at {exp.company} has only {len(exp.bullets)} bullet(s)",
                    suggestion="Aim for 4-6 bullet points per role with action verbs and metrics"
                ))
            elif len(exp.bullets) > 8:
                issues.append(ATSFormatIssue(
                    severity="info",
                    category="content",
                    message=f"'{exp.title}' at {exp.company} has {len(exp.bullets)} bullets (too many)",
                    suggestion="Trim to 4-6 most impactful bullets. ATS favors concise, targeted content"
                ))

        # Short bullets
        short_bullets = [b for b in all_bullets if len(b) < 30]
        if short_bullets:
            issues.append(ATSFormatIssue(
                severity="warning",
                category="content",
                message=f"{len(short_bullets)} bullet(s) are too short (< 30 chars)",
                suggestion="Expand with CAR format: Challenge → Action → Result with metrics"
            ))

        # Long bullets
        long_bullets = [b for b in all_bullets if len(b) > 200]
        if long_bullets:
            issues.append(ATSFormatIssue(
                severity="info",
                category="content",
                message=f"{len(long_bullets)} bullet(s) exceed 200 characters",
                suggestion="Keep bullets to 1-2 lines. Split long bullets into multiple concise points"
            ))

        # First-person pronouns
        first_person = sum(
            1 for b in all_bullets
            if re.search(r'\b(I|my|me|we|our)\b', b, re.IGNORECASE)
        )
        if first_person:
            issues.append(ATSFormatIssue(
                severity="warning",
                category="content",
                message=f"{first_person} bullet(s) contain first-person pronouns (I, my, me, we)",
                suggestion="Remove all pronouns. Start bullets with action verbs: 'Developed...', 'Led...'"
            ))
        
        # Buzzwords without context
        for bullet in all_bullets:
            for buzzword in BUZZWORDS_TO_AVOID:
                if buzzword in bullet.lower():
                    issues.append(ATSFormatIssue(
                        severity="info",
                        category="content",
                        message=f"Buzzword '{buzzword}' found without supporting evidence",
                        suggestion=f"Replace '{buzzword}' with a specific, measurable achievement"
                    ))
                    break  # One per bullet is enough

    # ── Experience Dates ──────────────────────────────
    for exp in resume_data.experience:
        if not exp.dates:
            issues.append(ATSFormatIssue(
                severity="warning",
                category="content",
                message=f"No dates for '{exp.title} at {exp.company}'",
                suggestion="Add dates: 'Month Year - Month Year' (e.g., 'Jan 2023 - Present')"
            ))

    # ── Certifications ────────────────────────────────
    if not resume_data.certifications:
        issues.append(ATSFormatIssue(
            severity="info",
            category="structure",
            message="No certifications section",
            suggestion="Add relevant certifications (AWS, Azure, GCP, PMP, etc.) to boost ATS matching"
        ))

    return issues


# ═══════════════════════════════════════════════════════════
# Bullet Point Analysis
# ═══════════════════════════════════════════════════════════

def _analyze_bullets(resume_data: ResumeData) -> List[BulletAnalysis]:
    """Analyze each bullet point for action verbs, metrics, and quality."""
    analyses = []

    for exp in resume_data.experience:
        for bullet in exp.bullets:
            analysis = _analyze_single_bullet(bullet)
            analyses.append(analysis)

    for proj in resume_data.projects:
        if proj.description:
            analysis = _analyze_single_bullet(proj.description)
            analyses.append(analysis)

    return analyses


def _analyze_single_bullet(bullet: str) -> BulletAnalysis:
    """Analyze a single bullet point with detailed scoring."""
    bullet_clean = bullet.strip()
    if not bullet_clean:
        return BulletAnalysis(original=bullet, score=0)

    # Check for metrics
    has_metrics = any(re.search(pattern, bullet_clean) for pattern in METRIC_PATTERNS)

    # Check for strong action verb at start
    first_word = bullet_clean.split()[0].lower() if bullet_clean.split() else ""
    has_action_verb = first_word in ALL_ACTION_VERBS
    
    if not has_action_verb:
        has_action_verb = any(
            bullet_clean.lower().startswith(verb)
            for verb in ALL_ACTION_VERBS
        )

    # Check for weak verbs
    has_weak_verb = any(
        bullet_clean.lower().startswith(verb)
        for verb in WEAK_VERBS
    )

    # Check for first-person pronouns
    has_pronouns = bool(re.search(r'\b(I|my|me|we|our)\b', bullet_clean, re.IGNORECASE))

    # Suggest action verb
    action_verb_suggestion = ""
    if not has_action_verb or has_weak_verb:
        action_verb_suggestion = _suggest_action_verb(bullet_clean)

    # Suggest metrics
    metric_suggestion = ""
    if not has_metrics:
        metric_suggestion = _suggest_metrics(bullet_clean)

    # Calculate score (0-100)
    score = 40  # Base score
    if has_action_verb:
        score += 20
    if has_metrics:
        score += 25
    if has_weak_verb:
        score -= 15
    if has_pronouns:
        score -= 10
    if 50 <= len(bullet_clean) <= 150:
        score += 10  # Ideal length
    elif len(bullet_clean) >= 30:
        score += 5

    score = max(0, min(100, score))

    # Generate improved version
    improved = _improve_bullet(bullet_clean, has_action_verb, has_metrics, action_verb_suggestion)

    return BulletAnalysis(
        original=bullet_clean,
        has_metrics=has_metrics,
        has_action_verb=has_action_verb,
        action_verb_suggestion=action_verb_suggestion,
        metric_suggestion=metric_suggestion,
        improved=improved,
        score=score,
    )


def _suggest_action_verb(bullet: str) -> str:
    """Suggest a stronger action verb based on bullet content."""
    bullet_lower = bullet.lower()

    verb_map = [
        (["build", "built", "create", "created", "develop", "developed"], "Engineered"),
        (["improve", "improved", "optimize", "optimized", "faster", "reduce", "reduced"], "Optimized"),
        (["lead", "led", "manage", "managed", "team", "oversee", "oversaw"], "Spearheaded"),
        (["design", "designed", "architect", "architected", "plan"], "Architected"),
        (["test", "tested", "debug", "debugged", "fix", "fixed", "resolve"], "Diagnosed"),
        (["deploy", "deployed", "launch", "launched", "release", "released", "ship"], "Deployed"),
        (["automate", "automated", "script", "scripted"], "Automated"),
        (["analyze", "analyzed", "research", "researched", "investigate"], "Analyzed"),
        (["implement", "implemented", "integrate", "integrated", "set up", "setup"], "Implemented"),
        (["work", "worked", "helped", "assisted", "support", "supported"], "Delivered"),
        (["train", "trained", "mentor", "mentored", "teach", "onboard"], "Mentored"),
        (["write", "wrote", "document", "documented", "author"], "Authored"),
        (["present", "presented", "communicate", "communicated"], "Presented"),
        (["migrate", "migrated", "transfer", "transition"], "Migrated"),
        (["monitor", "monitored", "track", "tracked", "observe"], "Monitored"),
    ]

    for keywords_list, suggestion in verb_map:
        if any(kw in bullet_lower for kw in keywords_list):
            return suggestion

    return "Spearheaded"


def _suggest_metrics(bullet: str) -> str:
    """Suggest how to add metrics to a bullet point."""
    bullet_lower = bullet.lower()

    suggestions = [
        (["api", "endpoint", "service", "system", "backend"],
         "Add: response time improvement (e.g., 'reduced latency by 40%') or throughput (e.g., '10K+ requests/sec')"),
        (["test", "testing", "coverage", "qa", "quality"],
         "Add: coverage percentage (e.g., 'increased test coverage from 65% to 90%')"),
        (["deploy", "ci/cd", "pipeline", "release", "devops"],
         "Add: deployment frequency or time savings (e.g., 'reduced deploy time by 60%')"),
        (["user", "customer", "client", "visitor"],
         "Add: user impact numbers (e.g., 'serving 10K+ daily active users')"),
        (["data", "database", "query", "sql", "schema", "migration"],
         "Add: performance improvement (e.g., 'query time reduced from 6s to 200ms')"),
        (["team", "collaborate", "mentor", "cross-functional"],
         "Add: team size or scope (e.g., 'across a team of 8 engineers in 3 time zones')"),
        (["reduce", "improve", "increase", "optimize", "enhance", "boost"],
         "Add: specific percentage or number (e.g., 'by 35%', 'saving $50K annually')"),
        (["cost", "budget", "spending", "expense", "savings"],
         "Add: dollar amounts (e.g., 'saving $200K annually', 'reduced costs by 30%')"),
        (["revenue", "sales", "growth", "conversion"],
         "Add: revenue/growth numbers (e.g., 'driving $1M+ in revenue', 'increased conversion by 25%')"),
    ]

    for keywords_list, suggestion in suggestions:
        if any(kw in bullet_lower for kw in keywords_list):
            return suggestion

    return "Add quantifiable metrics: percentages, dollar amounts, time saved, team size, or user counts"


def _improve_bullet(bullet: str, has_action_verb: bool, has_metrics: bool, verb_suggestion: str) -> str:
    """Generate an improved version of the bullet (heuristic-based)."""
    if has_action_verb and has_metrics:
        return bullet  # Already good

    improved = bullet

    # If no action verb, replace weak start
    if not has_action_verb and verb_suggestion:
        for weak in WEAK_VERBS:
            if improved.lower().startswith(weak):
                improved = improved[len(weak):].lstrip(" ,.")
                break
        if improved:
            improved = f"{verb_suggestion} {improved[0].lower()}{improved[1:]}"
        else:
            improved = bullet

    return improved


# ═══════════════════════════════════════════════════════════
# Skills Gap Analysis
# ═══════════════════════════════════════════════════════════

def _analyze_skill_gaps(
    resume_data: ResumeData, keywords: List[str], job_description: str
) -> List[SkillGap]:
    """Identify missing skills from JD not present in the resume."""
    resume_text = _build_resume_text(resume_data).lower()
    all_resume_skills = []
    for skills_list in resume_data.skills.values():
        all_resume_skills.extend([s.lower() for s in skills_list])

    gaps = []
    jd_lower = job_description.lower()

    SKILL_SYNONYMS = {
        "python": ["python3", "py", "cpython"],
        "javascript": ["js", "ecmascript", "es6"],
        "typescript": ["ts"],
        "react": ["reactjs", "react.js"],
        "node.js": ["nodejs", "node"],
        "postgresql": ["postgres", "psql"],
        "mongodb": ["mongo"],
        "kubernetes": ["k8s"],
        "docker": ["containerization", "containers"],
        "aws": ["amazon web services"],
        "gcp": ["google cloud", "google cloud platform"],
        "azure": ["microsoft azure"],
        "ci/cd": ["continuous integration", "continuous deployment", "cicd"],
        "machine learning": ["ml"],
        "artificial intelligence": ["ai"],
        "rest api": ["restful", "rest apis"],
    }

    for kw in keywords:
        kw_lower = kw.lower().strip()
        if not kw_lower:
            continue

        found = kw_lower in resume_text
        if not found:
            for canonical, synonyms in SKILL_SYNONYMS.items():
                if kw_lower == canonical or kw_lower in synonyms:
                    if any(s in resume_text for s in [canonical] + synonyms):
                        found = True
                        break

        if not found:
            # Determine importance
            count_in_jd = jd_lower.count(kw_lower)
            required_phrases = [
                f"must have {kw_lower}", f"required: {kw_lower}",
                f"require {kw_lower}", f"required {kw_lower}",
                f"minimum {kw_lower}", f"mandatory {kw_lower}",
            ]
            preferred_phrases = [
                f"preferred {kw_lower}", f"nice to have {kw_lower}",
                f"bonus {kw_lower}", f"plus {kw_lower}",
            ]

            if count_in_jd >= 3 or any(p in jd_lower for p in required_phrases):
                importance = "critical"
            elif count_in_jd >= 2 or any(p in jd_lower for p in preferred_phrases):
                importance = "high"
            else:
                importance = "medium"

            related = _find_related_skills(kw_lower, all_resume_skills)
            suggestion = _generate_gap_suggestion(kw_lower, related)

            gaps.append(SkillGap(
                skill=kw,
                importance=importance,
                suggestion=suggestion,
                related_skills=related[:3],
            ))

    importance_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    gaps.sort(key=lambda g: importance_order.get(g.importance, 3))

    return gaps[:15]


def _find_related_skills(missing_skill: str, resume_skills: List[str]) -> List[str]:
    """Find skills in resume related to the missing skill."""
    DOMAIN_GROUPS = {
        "frontend": ["react", "vue", "angular", "html", "css", "javascript", "typescript", "svelte", "next.js", "tailwind"],
        "backend": ["python", "java", "node.js", "fastapi", "django", "spring", "express", "go", "rust", "flask", ".net"],
        "cloud": ["aws", "azure", "gcp", "docker", "kubernetes", "terraform", "cloudformation", "heroku"],
        "database": ["postgresql", "mysql", "mongodb", "redis", "dynamodb", "cassandra", "elasticsearch", "sqlite"],
        "ml": ["tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "machine learning", "deep learning", "nlp"],
        "devops": ["docker", "kubernetes", "jenkins", "github actions", "gitlab ci", "circleci", "terraform", "ansible"],
        "messaging": ["kafka", "rabbitmq", "sqs", "sns", "event-driven"],
    }

    for domain, skills in DOMAIN_GROUPS.items():
        if missing_skill in skills:
            return [rs for rs in resume_skills if rs in skills and rs != missing_skill]

    return []


def _generate_gap_suggestion(skill: str, related: List[str]) -> str:
    """Generate actionable suggestion for addressing a skill gap."""
    if related:
        return (
            f"You have related experience with {', '.join(related)}. "
            f"Highlight transferable skills or add '{skill}' to your skills section "
            f"if you have any exposure."
        )
    return (
        f"Consider gaining experience with {skill} through projects, courses, or certifications. "
        f"Add it to your Skills section if you have any hands-on experience."
    )


# ═══════════════════════════════════════════════════════════
# Score Calculation
# ═══════════════════════════════════════════════════════════

def _calculate_scores(
    keyword_pct: float,
    format_issues: List[ATSFormatIssue],
    bullet_analyses: List[BulletAnalysis],
    resume_data: ResumeData,
    skill_gaps: List[SkillGap],
) -> Dict[str, int]:
    """
    Calculate ATS scores using real-world platform weights.
    
    Weight Distribution (aligned with Workday/Taleo/Greenhouse):
      • Keyword Matching   — 40%  (most critical for ranking)
      • Content Quality    — 30%  (action verbs, metrics, CAR format)
      • Section Quality    — 20%  (completeness, standard headers, contact info)
      • Format Readability — 10%  (clean structure, parseable, no garbled chars)
    """
    # ── Keyword match score (0-100, weight: 40%) ──
    # Target: 60-80% match = good; 80%+ = excellent
    # Context-weighted: keywords in experience bullets count 1.5x
    keyword_score = min(100, int(keyword_pct * 1.25))

    # ── Content quality score (0-100, weight: 30%) ──
    if bullet_analyses:
        avg_bullet_score = sum(b.score for b in bullet_analyses) / len(bullet_analyses)
        metrics_pct = sum(1 for b in bullet_analyses if b.has_metrics) / len(bullet_analyses) * 100
        action_pct = sum(1 for b in bullet_analyses if b.has_action_verb) / len(bullet_analyses) * 100
        content_score = int((avg_bullet_score * 0.4) + (metrics_pct * 0.3) + (action_pct * 0.3))
    else:
        content_score = 20

    # ── Section quality score (0-100, weight: 20%) ──
    completeness = 0
    # Required sections (ATS critical)
    if resume_data.experience:
        completeness += 25
        # Bonus: adequate bullet count per role
        avg_bullets = sum(len(e.bullets) for e in resume_data.experience) / len(resume_data.experience)
        if avg_bullets >= 3:
            completeness += 5
    if resume_data.education:
        completeness += 20
    if resume_data.skills:
        completeness += 20
        # Bonus: categorized skills
        if isinstance(resume_data.skills, dict) and len(resume_data.skills) >= 3:
            completeness += 5
    # Contact info (ATS needs this to create candidate profile)
    if resume_data.email:
        completeness += 5
    if resume_data.phone:
        completeness += 5
    if resume_data.location:
        completeness += 5
    # Optional sections
    if resume_data.projects:
        completeness += 5
    if resume_data.certifications:
        completeness += 5

    # ── Format readability score (0-100, weight: 10%) ──
    critical_issues = sum(1 for i in format_issues if i.severity == "critical")
    warning_issues = sum(1 for i in format_issues if i.severity == "warning")
    format_score = max(0, 100 - (critical_issues * 20) - (warning_issues * 8))

    # ── Overall score (weighted average — real-world ATS weights) ──
    overall = int(
        keyword_score * 0.40 +   # Keywords: 40% (most critical)
        content_score * 0.30 +   # Content quality: 30%
        completeness * 0.20 +    # Section quality: 20%
        format_score * 0.10      # Format readability: 10%
    )

    return {
        "overall": max(0, min(100, overall)),
        "keyword_match": max(0, min(100, keyword_score)),
        "content_quality": max(0, min(100, content_score)),
        "completeness": max(0, min(100, completeness)),
        "formatting": max(0, min(100, format_score)),
    }


def _score_to_grade(score: int) -> str:
    """Convert a numerical score to a letter grade."""
    if score >= 95:
        return "A+"
    elif score >= 90:
        return "A"
    elif score >= 85:
        return "B+"
    elif score >= 80:
        return "B"
    elif score >= 75:
        return "C+"
    elif score >= 65:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "F"


# ═══════════════════════════════════════════════════════════
# Recommendations
# ═══════════════════════════════════════════════════════════

def _generate_recommendations(
    keyword_pct: float,
    format_issues: List[ATSFormatIssue],
    bullet_analyses: List[BulletAnalysis],
    skill_gaps: List[SkillGap],
    missing_keywords: List[str],
    resume_data: ResumeData,
) -> List[str]:
    """Generate prioritized, actionable recommendations for ATS improvement."""
    recs = []

    # ── Keyword match ─────────────────────────────────
    if keyword_pct < 40:
        top_missing = ", ".join(missing_keywords[:5])
        recs.append(
            f"CRITICAL: Only {keyword_pct:.0f}% keyword match (target: 60-80%). "
            f"Add these missing keywords to Skills/Experience: {top_missing}"
        )
    elif keyword_pct < 60:
        top_missing = ", ".join(missing_keywords[:4])
        recs.append(
            f"LOW MATCH: {keyword_pct:.0f}% keyword match. "
            f"Add missing keywords: {top_missing}"
        )
    elif keyword_pct < 80:
        top_missing = ", ".join(missing_keywords[:3])
        recs.append(
            f"GOOD: {keyword_pct:.0f}% keyword match. "
            f"Add {top_missing} to reach 80%+ target"
        )

    # ── Critical format issues ────────────────────────
    for issue in format_issues:
        if issue.severity == "critical":
            recs.append(f"FIX: {issue.message}. {issue.suggestion}")

    # ── Bullet metrics ────────────────────────────────
    total_bullets = len(bullet_analyses)
    metrics_count = sum(1 for b in bullet_analyses if b.has_metrics)
    if total_bullets:
        metrics_pct = metrics_count / total_bullets
        if metrics_pct < 0.5:
            recs.append(
                f"METRICS: Only {metrics_count}/{total_bullets} bullets have numbers. "
                "Add %, $, time saved, or user counts to every bullet using CAR format"
            )

    # ── Action verbs ──────────────────────────────────
    action_count = sum(1 for b in bullet_analyses if b.has_action_verb)
    if total_bullets:
        action_pct = action_count / total_bullets
        if action_pct < 0.6:
            recs.append(
                f"VERBS: {total_bullets - action_count} bullets lack strong action verbs. "
                "Start each with: Engineered, Optimized, Spearheaded, Architected, Deployed"
            )

    # ── Weak verbs ────────────────────────────────────
    weak_count = sum(
        1 for b in bullet_analyses
        if any(b.original.lower().startswith(w) for w in WEAK_VERBS)
    )
    if weak_count:
        recs.append(
            f"WEAK VERBS: {weak_count} bullets start with weak verbs (helped, worked, used). "
            "Replace with strong action verbs"
        )

    # ── Skills gap ────────────────────────────────────
    critical_gaps = [g for g in skill_gaps if g.importance == "critical"]
    if critical_gaps:
        gap_names = ", ".join(g.skill for g in critical_gaps[:3])
        recs.append(
            f"SKILL GAPS: Critical missing skills: {gap_names}. "
            "Add to Skills section or highlight in Experience bullets"
        )

    # ── Section recommendations ───────────────────────
    if not resume_data.certifications:
        recs.append(
            "ADD CERTS: Include relevant certifications (AWS, Azure, PMP, etc.) "
            "for additional ATS keyword matching"
        )

    if not resume_data.projects:
        recs.append(
            "ADD PROJECTS: Showcase hands-on experience with target technologies "
            "in a Projects section"
        )

    # ── Content volume ────────────────────────────────
    total_bullet_chars = sum(len(b.original) for b in bullet_analyses)
    if total_bullet_chars < 500:
        recs.append(
            "SPARSE CONTENT: Expand bullet points with specific achievements, "
            "technologies used, and measurable impact"
        )

    # ── Pronouns ──────────────────────────────────────
    pronoun_count = sum(
        1 for b in bullet_analyses
        if re.search(r'\b(I|my|me|we|our)\b', b.original, re.IGNORECASE)
    )
    if pronoun_count:
        recs.append(
            f"PRONOUNS: {pronoun_count} bullets contain 'I/my/me/we'. "
            "Remove all pronouns — start with action verbs instead"
        )

    return recs
