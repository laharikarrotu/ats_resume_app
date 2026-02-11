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

export interface AnalysisResponse {
  overall_score: number;
  keyword_match_score: number;
  format_score: number;
  experience_score: number;
  matched_keywords: string[];
  missing_keywords: string[];
  format_issues: string[];
  recommendations: string[];
  skill_gaps: string[];
  strengths: string[];
}

export interface GenerateResponse {
  download_path: string;
  keywords: string[];
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
