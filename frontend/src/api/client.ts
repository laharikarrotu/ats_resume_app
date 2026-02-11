/**
 * API client — talks to the FastAPI backend.
 *
 * In dev, Vite proxies /api/* → http://127.0.0.1:8000
 * In prod, both are served from the same origin or the base URL is configured.
 */

import type {
  UploadResponse,
  AnalysisResponse,
  CoverLetterResponse,
  HealthResponse,
  ResumeVersion,
  ValidateResponse,
} from "../types";

const BASE = import.meta.env.VITE_API_BASE ?? "";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(body.detail ?? "Request failed", res.status);
  }
  return res.json();
}

/* ── Upload ── */

export async function uploadResumeFile(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadResponse>("/upload_resume/", {
    method: "POST",
    body: form,
  });
}

export async function uploadResumeText(text: string): Promise<UploadResponse> {
  const form = new FormData();
  form.append("resume_text", text);
  return request<UploadResponse>("/upload_resume_text/", {
    method: "POST",
    body: form,
  });
}

/* ── Analyze ── */

export async function analyzeResume(
  sessionId: string,
  jobDescription: string,
): Promise<AnalysisResponse> {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("job_description", jobDescription);
  return request<AnalysisResponse>("/api/analyze", {
    method: "POST",
    body: form,
  });
}

/* ── Generate ── */

export interface GenerateResult {
  blob: Blob;
  atsCompatible: boolean;
  atsScore: number;
  atsIssues: number;
}

export async function generateResume(
  sessionId: string,
  jobDescription: string,
  outputFormat: "docx" | "pdf" = "docx",
  fastMode = false,
): Promise<GenerateResult> {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("job_description", jobDescription);
  form.append("output_format", outputFormat);
  form.append("fast_mode", String(fastMode));

  const res = await fetch(`${BASE}/generate_resume/`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(body.detail ?? "Generation failed", res.status);
  }

  // Extract ATS validation metadata from response headers
  const atsCompatible = res.headers.get("X-ATS-Compatible") !== "False";
  const atsScore = parseInt(res.headers.get("X-ATS-Score") ?? "100", 10);
  const atsIssues = parseInt(res.headers.get("X-ATS-Issues") ?? "0", 10);

  const blob = await res.blob();
  return { blob, atsCompatible, atsScore, atsIssues };
}

/* ── Validate ── */

export async function validateResume(
  filename: string,
  sessionId?: string,
  keywords?: string[],
): Promise<ValidateResponse> {
  const form = new FormData();
  form.append("filename", filename);
  if (sessionId) form.append("session_id", sessionId);
  if (keywords?.length) form.append("keywords", keywords.join(","));
  return request<ValidateResponse>("/api/validate", {
    method: "POST",
    body: form,
  });
}

/* ── Cover Letter ── */

export async function generateCoverLetter(
  sessionId: string,
  jobDescription: string,
  companyName?: string,
  jobTitle?: string,
  tone?: string,
): Promise<CoverLetterResponse> {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("job_description", jobDescription);
  if (companyName) form.append("company_name", companyName);
  if (jobTitle) form.append("job_title", jobTitle);
  if (tone) form.append("tone", tone);

  return request<CoverLetterResponse>("/api/cover_letter", {
    method: "POST",
    body: form,
  });
}

/* ── Resume Data Preview ── */

export async function getResumeData(sessionId: string): Promise<any> {
  return request(`/api/resume_data?session_id=${sessionId}`);
}

/* ── Versions ── */

export async function getVersions(
  sessionId: string,
): Promise<{ versions: ResumeVersion[] }> {
  return request(`/api/versions?session_id=${sessionId}`);
}

/* ── Health ── */

export async function getHealth(): Promise<HealthResponse> {
  return request("/health");
}

export { ApiError };
