import { useState, useCallback } from "react";
import type { AppStep, SessionState, AnalysisResponse } from "../types";

const INITIAL_SESSION: SessionState = {
  sessionId: null,
  resumeName: "",
  resumeEmail: "",
  experienceCount: 0,
  skillsCount: 0,
};

export function useResumeSession() {
  const [step, setStep] = useState<AppStep>("upload");
  const [session, setSession] = useState<SessionState>(INITIAL_SESSION);
  const [jobDescription, setJobDescription] = useState("");
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => setError(null), []);

  const onUploaded = useCallback(
    (data: {
      session_id: string;
      name: string;
      email: string;
      experience_count: number;
      skills_count: number;
    }) => {
      setSession({
        sessionId: data.session_id,
        resumeName: data.name,
        resumeEmail: data.email,
        experienceCount: data.experience_count,
        skillsCount: data.skills_count,
      });
      setStep("describe");
      setError(null);
    },
    [],
  );

  const reset = useCallback(() => {
    setStep("upload");
    setSession(INITIAL_SESSION);
    setJobDescription("");
    setAnalysis(null);
    setError(null);
  }, []);

  return {
    step,
    setStep,
    session,
    jobDescription,
    setJobDescription,
    analysis,
    setAnalysis,
    loading,
    setLoading,
    error,
    setError,
    clearError,
    onUploaded,
    reset,
  };
}
