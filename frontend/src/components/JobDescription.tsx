import { motion } from "framer-motion";
import {
  Search,
  ArrowRight,
  User,
  Mail,
  Briefcase,
  Sparkles,
  Loader2,
} from "lucide-react";
import type { SessionState } from "../types";

interface Props {
  session: SessionState;
  jobDescription: string;
  setJobDescription: (v: string) => void;
  onAnalyze: () => void;
  loading: boolean;
}

export default function JobDescription({
  session,
  jobDescription,
  setJobDescription,
  onAnalyze,
  loading,
}: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-3xl mx-auto"
    >
      {/* Resume summary card */}
      <div className="bg-gradient-to-br from-primary-50 to-accent-50 rounded-2xl p-4 sm:p-6 mb-8 border border-primary-100">
        <div className="flex items-start gap-4">
          <div className="size-12 rounded-xl bg-white shadow-sm flex items-center justify-center text-primary-500">
            <User className="size-5" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-slate-800 truncate">
              {session.resumeName || "Resume uploaded"}
            </h3>
            {session.resumeEmail && (
              <p className="text-sm text-slate-500 flex items-center gap-1 mt-0.5">
                <Mail className="size-3" />
                {session.resumeEmail}
              </p>
            )}
            <div className="flex flex-wrap gap-2 mt-2">
              <span className="inline-flex items-center gap-1 text-xs bg-white text-primary-600 px-2 py-0.5 rounded-md font-medium">
                <Briefcase className="size-3" />
                {session.experienceCount} roles
              </span>
              <span className="inline-flex items-center gap-1 text-xs bg-white text-accent-600 px-2 py-0.5 rounded-md font-medium">
                <Sparkles className="size-3" />
                {session.skillsCount} skills
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Job description input */}
      <div className="space-y-3">
        <label className="block">
          <span className="text-sm font-semibold text-slate-700">
            Job Description
          </span>
          <span className="text-xs text-slate-400 ml-2">
            Paste the full job posting for best results
          </span>
        </label>

        <textarea
          value={jobDescription}
          onChange={(e) => setJobDescription(e.target.value)}
          placeholder={`Example:\n\nSoftware Engineer — Acme Corp\n\nWe are looking for a Senior Software Engineer with experience in Python, React, and cloud services (AWS/GCP). You will lead backend architecture…`}
          rows={12}
          className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-primary-300 focus:border-primary-300 resize-y placeholder:text-slate-400"
        />

        {/* Character count */}
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-400">
            {jobDescription.length > 0
              ? `${jobDescription.split(/\s+/).filter(Boolean).length} words`
              : "Tip: Include required skills, responsibilities, and qualifications"}
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="mt-6 flex flex-col sm:flex-row gap-3">
        <button
          onClick={onAnalyze}
          disabled={loading || jobDescription.trim().length < 50}
          className="flex-1 sm:flex-none px-6 py-3 rounded-xl bg-primary-600 text-white font-medium text-sm hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 shadow-lg shadow-primary-200"
        >
          {loading ? (
            <>
              <Loader2 className="size-4 animate-spin" /> Analyzing…
            </>
          ) : (
            <>
              <Search className="size-4" /> Analyze ATS Match
              <ArrowRight className="size-4" />
            </>
          )}
        </button>

        {jobDescription.trim().length > 0 && jobDescription.trim().length < 50 && (
          <p className="text-xs text-warning-500 self-center">
            Add more detail for accurate analysis (min ~50 characters)
          </p>
        )}
      </div>
    </motion.div>
  );
}
