import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  Loader2,
  Copy,
  Check,
  Download,
  Sparkles,
  Building2,
  Briefcase,
  Palette,
} from "lucide-react";
import { generateCoverLetter } from "../api/client";

interface Props {
  sessionId: string;
  jobDescription: string;
}

const TONES = [
  { value: "professional", label: "Professional", icon: "💼" },
  { value: "enthusiastic", label: "Enthusiastic", icon: "🚀" },
  { value: "conversational", label: "Conversational", icon: "💬" },
  { value: "formal", label: "Formal", icon: "🎩" },
];

const LOADING_MESSAGES = [
  "Analyzing job requirements…",
  "Matching your experience…",
  "Crafting compelling narrative…",
  "Polishing final draft…",
];

export default function CoverLetter({ sessionId, jobDescription }: Props) {
  const [companyName, setCompanyName] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [tone, setTone] = useState("professional");
  const [loading, setLoading] = useState(false);
  const [loadingMsg, setLoadingMsg] = useState(LOADING_MESSAGES[0]);
  const [coverLetter, setCoverLetter] = useState<string | null>(null);
  const [keyPoints, setKeyPoints] = useState<string[]>([]);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Cycle loading messages
  useEffect(() => {
    if (!loading) return;
    let idx = 0;
    const interval = setInterval(() => {
      idx = (idx + 1) % LOADING_MESSAGES.length;
      setLoadingMsg(LOADING_MESSAGES[idx]);
    }, 2500);
    return () => clearInterval(interval);
  }, [loading]);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setCoverLetter(null);
    try {
      const result = await generateCoverLetter(
        sessionId,
        jobDescription,
        companyName || undefined,
        jobTitle || undefined,
        tone,
      );
      setCoverLetter(result.cover_letter);
      setKeyPoints(result.key_points || []);
    } catch (e: any) {
      setError(e.message ?? "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!coverLetter) return;
    await navigator.clipboard.writeText(coverLetter);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!coverLetter) return;
    const blob = new Blob([coverLetter], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Cover_Letter${companyName ? `_${companyName.replace(/\s+/g, "_")}` : ""}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      {/* Collapsed form when cover letter exists */}
      {!coverLetter ? (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-sm space-y-5"
        >
          <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
            <FileText className="size-5 text-accent-500" />
            Generate Cover Letter
          </h3>

          {/* Company & Job Title */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-500 mb-1 block">
                <Building2 className="size-3 inline mr-1" />
                Company Name
                <span className="text-slate-300 ml-1">(optional)</span>
              </label>
              <input
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="e.g. Google"
                className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent-300 focus:border-accent-300 placeholder:text-slate-400 transition-shadow"
                disabled={loading}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 mb-1 block">
                <Briefcase className="size-3 inline mr-1" />
                Job Title
                <span className="text-slate-300 ml-1">(optional)</span>
              </label>
              <input
                type="text"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                placeholder="e.g. Senior Software Engineer"
                className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent-300 focus:border-accent-300 placeholder:text-slate-400 transition-shadow"
                disabled={loading}
              />
            </div>
          </div>

          {/* Tone selector */}
          <div>
            <label className="text-xs font-medium text-slate-500 mb-2 block">
              <Palette className="size-3 inline mr-1" />
              Tone
            </label>
            <div className="flex flex-wrap gap-2">
              {TONES.map((t) => (
                <button
                  key={t.value}
                  onClick={() => setTone(t.value)}
                  disabled={loading}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    tone === t.value
                      ? "bg-accent-100 text-accent-700 ring-2 ring-accent-200"
                      : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                  } ${loading ? "opacity-50 cursor-not-allowed" : ""}`}
                >
                  {t.icon} {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Generate button */}
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-accent-500 to-primary-500 text-white font-semibold text-sm hover:from-accent-600 hover:to-primary-600 disabled:opacity-60 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 shadow-lg shadow-accent-200"
          >
            {loading ? (
              <>
                <Loader2 className="size-4 animate-spin" /> {loadingMsg}
              </>
            ) : (
              <>
                <Sparkles className="size-4" /> Generate Cover Letter
              </>
            )}
          </button>

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
        </motion.div>
      ) : (
        /* Cover letter result */
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden"
        >
          {/* Header bar */}
          <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100 bg-slate-50">
            <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
              <FileText className="size-4 text-accent-500" />
              Cover Letter
              {companyName && (
                <span className="text-slate-400 font-normal">
                  — {companyName}
                </span>
              )}
            </h3>
            <div className="flex items-center gap-1">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-500 hover:bg-slate-200 transition-colors"
              >
                {copied ? (
                  <>
                    <Check className="size-3 text-success-500" /> Copied
                  </>
                ) : (
                  <>
                    <Copy className="size-3" /> Copy
                  </>
                )}
              </button>
              <button
                onClick={handleDownload}
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-500 hover:bg-slate-200 transition-colors"
              >
                <Download className="size-3" /> Save
              </button>
            </div>
          </div>

          {/* Letter content */}
          <div className="px-5 py-4 sm:px-6 sm:py-5">
            <div className="prose prose-sm max-w-none text-slate-700 whitespace-pre-wrap leading-relaxed">
              {coverLetter}
            </div>
          </div>

          {/* Key points */}
          {keyPoints.length > 0 && (
            <div className="px-5 py-4 border-t border-slate-100 bg-accent-50/30">
              <p className="text-xs font-semibold text-accent-600 mb-2">
                Key Points Highlighted
              </p>
              <ul className="space-y-1">
                {keyPoints.map((point, i) => (
                  <li
                    key={i}
                    className="text-xs text-slate-600 flex items-start gap-1.5"
                  >
                    <span className="text-accent-500 mt-0.5">•</span>
                    {point}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Regenerate */}
          <div className="px-5 py-3 border-t border-slate-100 flex gap-2">
            <button
              onClick={() => setCoverLetter(null)}
              className="px-4 py-2 rounded-lg text-xs font-medium text-slate-500 hover:bg-slate-100 transition-colors"
            >
              Edit Options & Regenerate
            </button>
          </div>
        </motion.div>
      )}
    </div>
  );
}
