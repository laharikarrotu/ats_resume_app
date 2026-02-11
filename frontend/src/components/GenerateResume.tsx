import { useState } from "react";
import { motion } from "framer-motion";
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
} from "lucide-react";
import { generateResume } from "../api/client";
import type { GenerateResult } from "../api/client";

interface Props {
  sessionId: string;
  jobDescription: string;
  onReset: () => void;
}

type Format = "docx" | "pdf";

export default function GenerateResume({
  sessionId,
  jobDescription,
  onReset,
}: Props) {
  const [format, setFormat] = useState<Format>("docx");
  const [fastMode, setFastMode] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [atsResult, setAtsResult] = useState<Pick<GenerateResult, "atsCompatible" | "atsScore" | "atsIssues"> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    setDownloadUrl(null);
    setAtsResult(null);
    try {
      const result = await generateResume(sessionId, jobDescription, format, fastMode);
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
                className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                  format === f
                    ? "border-primary-500 bg-primary-50"
                    : "border-slate-200 hover:border-slate-300"
                }`}
              >
                {f === "docx" ? (
                  <FileText className="size-5 text-blue-500" />
                ) : (
                  <FileType className="size-5 text-red-500" />
                )}
                <div className="text-left">
                  <p className="text-sm font-semibold text-slate-700 uppercase">{f}</p>
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
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              fastMode ? "bg-primary-500" : "bg-slate-300"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 rounded-full bg-white transition-transform shadow-sm ${
                fastMode ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>

        {/* Generate button */}
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="w-full py-3.5 rounded-xl bg-gradient-to-r from-primary-600 to-accent-600 text-white font-semibold text-sm hover:from-primary-700 hover:to-accent-700 disabled:opacity-60 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 shadow-lg shadow-primary-200"
        >
          {generating ? (
            <>
              <Loader2 className="size-4 animate-spin" /> Generating your resume…
            </>
          ) : (
            <>
              <Zap className="size-4" /> Generate Resume
            </>
          )}
        </button>

        {/* Error */}
        {error && (
          <div className="bg-danger-400/10 text-danger-600 rounded-xl px-4 py-3 text-sm">
            {error}
          </div>
        )}

        {/* Success / Download */}
        {downloadUrl && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-success-400/10 rounded-xl p-5 text-center space-y-3"
          >
            <CheckCircle2 className="size-10 text-success-500 mx-auto" />
            <p className="text-sm font-semibold text-success-600">
              Resume generated successfully!
            </p>

            {/* ATS Validation Badge */}
            {atsResult && (
              <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
                atsResult.atsCompatible
                  ? "bg-success-100 text-success-700"
                  : "bg-warning-100 text-warning-700"
              }`}>
                {atsResult.atsCompatible ? (
                  <ShieldCheck className="size-4" />
                ) : (
                  <AlertTriangle className="size-4" />
                )}
                ATS Compatibility: {atsResult.atsScore}/100
                {atsResult.atsIssues > 0 && (
                  <span className="text-xs opacity-75">
                    ({atsResult.atsIssues} issue{atsResult.atsIssues > 1 ? "s" : ""})
                  </span>
                )}
              </div>
            )}

            <div className="flex flex-col sm:flex-row gap-2 justify-center">
              <a
                href={downloadUrl}
                download={`ATS_Resume.${format}`}
                className="inline-flex items-center justify-center gap-2 px-5 py-2 bg-success-500 text-white rounded-xl text-sm font-medium hover:bg-success-600 transition-colors"
              >
                <Download className="size-4" /> Download Again
              </a>
              <button
                onClick={onReset}
                className="inline-flex items-center justify-center gap-2 px-5 py-2 bg-white border border-slate-200 text-slate-600 rounded-xl text-sm font-medium hover:bg-slate-50 transition-colors"
              >
                <RotateCcw className="size-4" /> New Resume
              </button>
            </div>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
