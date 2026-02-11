/* ── API Response Types ── */

export interface UploadResponse {
  session_id: string;
  message: string;
  name: string;
  email: string;
  experience_count: number;
  projects_count: number;
  skills_count: number;
  certifications_count: number;
}

/* Matches backend ATSAnalysisResult.model_dump() */
export interface KeywordMatch {
  keyword: string;
  found_in_resume: boolean;
  context: string;
  importance: string;
}

export interface SkillGap {
  skill: string;
  importance: string;
  suggestion: string;
  related_skills: string[];
}

export interface ATSFormatIssue {
  severity: string;
  category: string;
  message: string;
  suggestion: string;
}

export interface BulletAnalysis {
  original: string;
  has_metrics: boolean;
  has_action_verb: boolean;
  action_verb_suggestion: string;
  metric_suggestion: string;
  improved: string;
  score: number;
}

export interface AnalysisResponse {
  overall_score: number;
  score_breakdown: Record<string, number>;
  grade: string;

  keyword_matches: KeywordMatch[];
  keyword_match_percentage: number;
  matched_keywords: string[];
  missing_keywords: string[];

  skill_gaps: SkillGap[];
  format_issues: ATSFormatIssue[];

  bullet_analyses: BulletAnalysis[];
  bullets_with_metrics_pct: number;
  bullets_with_action_verbs_pct: number;

  top_recommendations: string[];
}

export interface GenerateResponse {
  download_path: string;
  keywords: string[];
  ats_compatible: boolean;
  ats_compatibility_score: number;
  ats_issues_count: number;
}

export interface ATSValidationIssue {
  severity: string;
  check: string;
  message: string;
  suggestion: string;
}

export interface ValidateResponse {
  ats_compatible: boolean;
  compatibility_score: number;
  issues: ATSValidationIssue[];
  checks_passed: number;
  checks_total: number;
  section_detection: Record<string, boolean>;
  contact_parsed: Record<string, boolean>;
  keyword_density: Record<string, number>;
}

export interface CoverLetterResponse {
  cover_letter: string;
  key_points: string[];
}

export interface HealthResponse {
  status: string;
  version: string;
  llm: {
    active_provider: string;
    model: string;
    has_fallback: boolean;
    fallback_model: string;
    gemini_configured: boolean;
    openai_configured: boolean;
  };
  rate_limit: string;
}

export interface ResumeVersion {
  version_id: string;
  job_title: string;
  company: string;
  created_at: string;
  filename: string;
  ats_score: number;
  keywords_used: string[];
}

/* ── App State Types ── */

export type AppStep = "upload" | "describe" | "analyze" | "generate";

export interface SessionState {
  sessionId: string | null;
  resumeName: string;
  resumeEmail: string;
  experienceCount: number;
  skillsCount: number;
}
