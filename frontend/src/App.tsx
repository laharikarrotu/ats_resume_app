import Layout from "./components/Layout";
import FileUpload from "./components/FileUpload";
import JobDescription from "./components/JobDescription";
import AnalysisResult from "./components/AnalysisResult";
import GenerateResume from "./components/GenerateResume";
import { useResumeSession } from "./hooks/useResumeSession";
import { analyzeResume } from "./api/client";

export default function App() {
  const {
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
    onUploaded,
    reset,
  } = useResumeSession();

  /* ── Handlers ── */

  const handleAnalyze = async () => {
    if (!session.sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeResume(session.sessionId, jobDescription);
      setAnalysis(result);
      setStep("analyze");
    } catch (e: any) {
      setError(e.message ?? "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const handleGoToGenerate = () => {
    setStep("generate");
  };

  /* ── Render current step ── */

  const renderStep = () => {
    switch (step) {
      case "upload":
        return (
          <FileUpload
            onUploaded={onUploaded}
            setLoading={setLoading}
            setError={setError}
            loading={loading}
            error={error}
          />
        );

      case "describe":
        return (
          <JobDescription
            session={session}
            jobDescription={jobDescription}
            setJobDescription={setJobDescription}
            onAnalyze={handleAnalyze}
            loading={loading}
          />
        );

      case "analyze":
        return analysis ? (
          <AnalysisResult
            analysis={analysis}
            onGenerate={handleGoToGenerate}
            loading={loading}
          />
        ) : null;

      case "generate":
        return session.sessionId ? (
          <GenerateResume
            sessionId={session.sessionId}
            jobDescription={jobDescription}
            onReset={reset}
          />
        ) : null;
    }
  };

  return (
    <Layout step={step} onReset={reset}>
      {/* Global error toast */}
      {error && step !== "upload" && (
        <div className="mb-6 max-w-3xl mx-auto bg-danger-400/10 text-danger-600 rounded-xl px-4 py-3 text-sm flex items-center gap-2">
          <span className="shrink-0">⚠️</span>
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-auto text-danger-400 hover:text-danger-600"
          >
            ✕
          </button>
        </div>
      )}

      {renderStep()}
    </Layout>
  );
}
