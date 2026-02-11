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

export async function generateResume(
  sessionId: string,
  jobDescription: string,
  outputFormat: "docx" | "pdf" = "docx",
  fastMode = false,
): Promise<Blob> {
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

  return res.blob();
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
