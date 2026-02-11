import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Download,
  FileText,
  FileType,
  Loader2,
  CheckCircle2,
  RotateCcw,
  Zap,
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  ArrowLeft,
} from "lucide-react";
import { generateResume } from "../api/client";
import type { GenerateResult } from "../api/client";
import CoverLetter from "./CoverLetter";

interface Props {
  sessionId: string;
  jobDescription: string;
  onBack: () => void;
  onReset: () => void;
}

type Format = "docx" | "pdf";

const GENERATION_STEPS = [
  "Extracting target keywords…",
  "Rewriting experience bullets…",
  "Optimizing project descriptions…",
  "Building ATS-compliant document…",
  "Running compatibility checks…",
];

export default function GenerateResume({
  sessionId,
  jobDescription,
  onBack,
  onReset,
}: Props) {
  const [format, setFormat] = useState<Format>("docx");
  const [fastMode, setFastMode] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [genStep, setGenStep] = useState(0);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [atsResult, setAtsResult] = useState<Pick<
    GenerateResult,
    "atsCompatible" | "atsScore" | "atsIssues"
  > | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Cycle progress messages while generating
  useEffect(() => {
    if (!generating) {
      setGenStep(0);
      return;
    }
    const interval = setInterval(() => {
      setGenStep((prev) =>
        prev < GENERATION_STEPS.length - 1 ? prev + 1 : prev,
      );
    }, 3000);
    return () => clearInterval(interval);
  }, [generating]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    setDownloadUrl(null);
    setAtsResult(null);
    try {
      const result = await generateResume(
        sessionId,
        jobDescription,
        format,
        fastMode,
      );
      const url = URL.createObjectURL(result.blob);
      setDownloadUrl(url);
      setAtsResult({
        atsCompatible: result.atsCompatible,
        atsScore: result.atsScore,
        atsIssues: result.atsIssues,
      });

      // Auto-trigger download
      const a = document.createElement("a");
      a.href = url;
      a.download = `ATS_Resume.${format}`;
      a.click();
    } catch (e: any) {
      setError(e.message ?? "Generation failed");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-2xl mx-auto"
    >
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center size-16 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 mb-4">
          <Sparkles className="size-7 text-white" />
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold text-slate-800">
          Generate Tailored Resume
        </h2>
        <p className="text-slate-500 mt-2 text-sm">
          AI will rewrite your resume to maximize ATS compatibility
        </p>
      </div>

      {/* Options card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6">
        {/* Format selection */}
        <div>
          <label className="text-sm font-semibold text-slate-700 block mb-3">
            Output Format
          </label>
          <div className="grid grid-cols-2 gap-3">
            {(["docx", "pdf"] as Format[]).map((f) => (
              <button
                key={f}
                onClick={() => setFormat(f)}
                disabled={generating}
                className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                  format === f
                    ? "border-primary-500 bg-primary-50"
                    : "border-slate-200 hover:border-slate-300"
                } ${generating ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                {f === "docx" ? (
                  <FileText className="size-5 text-blue-500" />
                ) : (
                  <FileType className="size-5 text-red-500" />
                )}
                <div className="text-left">
                  <p className="text-sm font-semibold text-slate-700 uppercase">
                    {f}
                  </p>
                  <p className="text-xs text-slate-400">
                    {f === "docx" ? "Editable Word doc" : "Print-ready PDF"}
                  </p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Fast mode toggle */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-700">Fast Mode</p>
            <p className="text-xs text-slate-400">
              Quicker generation with slightly less optimization
            </p>
          </div>
          <button
            onClick={() => setFastMode(!fastMode)}
            disabled={generating}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              fastMode ? "bg-primary-500" : "bg-slate-300"
            } ${generating ? "opacity-50 cursor-not-allowed" : ""}`}
          >
            <span
              className={`inline-block h-4 w-4 rounded-full bg-white transition-transform shadow-sm ${
                fastMode ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>

        {/* Generate button */}
        {!downloadUrl && (
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={onBack}
              disabled={generating}
              className="sm:w-auto px-4 py-3 rounded-xl border border-slate-200 text-slate-600 font-medium text-sm hover:bg-slate-50 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
            >
              <ArrowLeft className="size-4" />
              Back
            </button>
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="flex-1 py-3.5 rounded-xl bg-gradient-to-r from-primary-600 to-accent-600 text-white font-semibold text-sm hover:from-primary-700 hover:to-accent-700 disabled:opacity-60 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 shadow-lg shadow-primary-200"
            >
              {generating ? (
                <>
                  <Loader2 className="size-4 animate-spin" /> Generating…
                </>
              ) : (
                <>
                  <Zap className="size-4" /> Generate Resume
                </>
              )}
            </button>
          </div>
        )}

        {/* Generation progress */}
        <AnimatePresence>
          {generating && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="bg-primary-50 rounded-xl p-5 border border-primary-100"
            >
              <div className="space-y-3">
                {GENERATION_STEPS.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex items-center gap-3 text-sm transition-all duration-300 ${
                      i < genStep
                        ? "text-success-600"
                        : i === genStep
                          ? "text-primary-700 font-medium"
                          : "text-slate-300"
                    }`}
                  >
                    {i < genStep ? (
                      <CheckCircle2 className="size-4 shrink-0" />
                    ) : i === genStep ? (
                      <Loader2 className="size-4 shrink-0 animate-spin" />
                    ) : (
                      <div className="size-4 shrink-0 rounded-full border-2 border-slate-200" />
                    )}
                    {msg}
                  </div>
                ))}
              </div>
              <p className="text-xs text-primary-400 mt-3 text-center">
                This usually takes 15–30 seconds
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error with retry */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="bg-danger-400/10 text-danger-600 rounded-xl px-4 py-3 text-sm flex items-center justify-between"
            >
              <span>{error}</span>
              <button
                onClick={handleGenerate}
                className="ml-3 px-3 py-1 bg-danger-500 text-white text-xs font-medium rounded-lg hover:bg-danger-600 transition-colors"
              >
                Retry
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Success / Download */}
        <AnimatePresence>
          {downloadUrl && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-success-400/10 rounded-xl p-6 text-center space-y-4"
            >
              <CheckCircle2 className="size-12 text-success-500 mx-auto" />
              <p className="text-base font-semibold text-success-600">
                Resume generated successfully!
              </p>

              {/* ATS Validation Badge */}
              {atsResult && (
                <div
                  className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
                    atsResult.atsCompatible
                      ? "bg-success-100 text-success-700"
                      : "bg-warning-100 text-warning-700"
                  }`}
                >
                  {atsResult.atsCompatible ? (
                    <ShieldCheck className="size-4" />
                  ) : (
                    <AlertTriangle className="size-4" />
                  )}
                  ATS Compatibility: {atsResult.atsScore}/100
                  {atsResult.atsIssues > 0 && (
                    <span className="text-xs opacity-75">
                      ({atsResult.atsIssues} issue
                      {atsResult.atsIssues > 1 ? "s" : ""})
                    </span>
                  )}
                </div>
              )}

              <div className="flex flex-col sm:flex-row gap-2 justify-center pt-2">
                <a
                  href={downloadUrl}
                  download={`ATS_Resume.${format}`}
                  className="inline-flex items-center justify-center gap-2 px-6 py-2.5 bg-success-500 text-white rounded-xl text-sm font-medium hover:bg-success-600 transition-colors shadow-sm"
                >
                  <Download className="size-4" /> Download Again
                </a>
                <button
                  onClick={() => {
                    setDownloadUrl(null);
                    setAtsResult(null);
                    setError(null);
                  }}
                  className="inline-flex items-center justify-center gap-2 px-6 py-2.5 bg-white border border-slate-200 text-slate-600 rounded-xl text-sm font-medium hover:bg-slate-50 transition-colors"
                >
                  <Zap className="size-4" /> Re-generate
                </button>
                <button
                  onClick={onReset}
                  className="inline-flex items-center justify-center gap-2 px-6 py-2.5 bg-white border border-slate-200 text-slate-600 rounded-xl text-sm font-medium hover:bg-slate-50 transition-colors"
                >
                  <RotateCcw className="size-4" /> New Resume
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Cover Letter section — always visible */}
      <div className="mt-6">
        <CoverLetter sessionId={sessionId} jobDescription={jobDescription} />
      </div>
    </motion.div>
  );
}
