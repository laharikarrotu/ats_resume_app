import { motion } from "framer-motion";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  Target,
  Lightbulb,
  Zap,
} from "lucide-react";
import type { AnalysisResponse } from "../types";

interface Props {
  analysis: AnalysisResponse;
  onGenerate: () => void;
  loading: boolean;
}

function ScoreRing({ score, label }: { score: number; label: string }) {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color =
    score >= 75
      ? "text-success-500"
      : score >= 50
        ? "text-warning-500"
        : "text-danger-500";
  const bgColor =
    score >= 75
      ? "stroke-success-500"
      : score >= 50
        ? "stroke-warning-500"
        : "stroke-danger-500";

  return (
    <div className="flex flex-col items-center">
      <div className="relative size-24 sm:size-28">
        <svg className="size-full -rotate-90" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke="currentColor"
            className="text-slate-100"
            strokeWidth="8"
          />
          <motion.circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            className={bgColor}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1, ease: "easeOut" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-2xl sm:text-3xl font-bold ${color}`}>{score}</span>
        </div>
      </div>
      <span className="text-xs text-slate-500 mt-1 font-medium">{label}</span>
    </div>
  );
}

export default function AnalysisResult({ analysis, onGenerate, loading }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-4xl mx-auto space-y-6"
    >
      {/* Score cards */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <h2 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
          <Target className="size-5 text-primary-500" />
          ATS Compatibility Score
        </h2>

        <div className="flex flex-wrap justify-center gap-6 sm:gap-10">
          <ScoreRing score={analysis.overall_score} label="Overall" />
          <ScoreRing score={analysis.keyword_match_score} label="Keywords" />
          <ScoreRing score={analysis.format_score} label="Format" />
          <ScoreRing score={analysis.experience_score} label="Experience" />
        </div>
      </div>

      {/* Two-column grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Matched keywords */}
        {analysis.matched_keywords.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-success-600 flex items-center gap-1.5 mb-3">
              <CheckCircle2 className="size-4" />
              Matched Keywords ({analysis.matched_keywords.length})
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {analysis.matched_keywords.map((kw) => (
                <span
                  key={kw}
                  className="px-2 py-0.5 bg-success-400/10 text-success-600 text-xs rounded-md font-medium"
                >
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Missing keywords */}
        {analysis.missing_keywords.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-danger-500 flex items-center gap-1.5 mb-3">
              <XCircle className="size-4" />
              Missing Keywords ({analysis.missing_keywords.length})
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {analysis.missing_keywords.map((kw) => (
                <span
                  key={kw}
                  className="px-2 py-0.5 bg-danger-400/10 text-danger-500 text-xs rounded-md font-medium"
                >
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Strengths */}
        {analysis.strengths.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-primary-600 flex items-center gap-1.5 mb-3">
              <TrendingUp className="size-4" />
              Strengths
            </h3>
            <ul className="space-y-1.5">
              {analysis.strengths.map((s, i) => (
                <li key={i} className="text-sm text-slate-600 flex items-start gap-2">
                  <Zap className="size-3.5 text-primary-400 mt-0.5 shrink-0" />
                  {s}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recommendations */}
        {analysis.recommendations.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-accent-600 flex items-center gap-1.5 mb-3">
              <Lightbulb className="size-4" />
              Recommendations
            </h3>
            <ul className="space-y-1.5">
              {analysis.recommendations.map((r, i) => (
                <li key={i} className="text-sm text-slate-600 flex items-start gap-2">
                  <span className="size-4 shrink-0 rounded-full bg-accent-100 text-accent-600 text-xs flex items-center justify-center font-bold mt-0.5">
                    {i + 1}
                  </span>
                  {r}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Format issues */}
        {analysis.format_issues.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-warning-500 flex items-center gap-1.5 mb-3">
              <AlertTriangle className="size-4" />
              Format Issues
            </h3>
            <ul className="space-y-1.5">
              {analysis.format_issues.map((issue, i) => (
                <li key={i} className="text-sm text-slate-600 flex items-start gap-2">
                  <AlertTriangle className="size-3.5 text-warning-500 mt-0.5 shrink-0" />
                  {issue}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Skill gaps */}
        {analysis.skill_gaps.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-600 flex items-center gap-1.5 mb-3">
              <Target className="size-4" />
              Skill Gaps
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {analysis.skill_gaps.map((gap) => (
                <span
                  key={gap}
                  className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded-md font-medium"
                >
                  {gap}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* CTA */}
      <div className="flex flex-col sm:flex-row items-center gap-4 pt-2">
        <button
          onClick={onGenerate}
          disabled={loading}
          className="w-full sm:w-auto px-8 py-3 rounded-xl bg-gradient-to-r from-primary-600 to-accent-600 text-white font-semibold text-sm hover:from-primary-700 hover:to-accent-700 transition-all flex items-center justify-center gap-2 shadow-lg shadow-primary-200"
        >
          <Zap className="size-4" />
          Generate Optimized Resume
          <ArrowRight className="size-4" />
        </button>
        <p className="text-xs text-slate-400 text-center sm:text-left">
          AI will rewrite your resume to maximize the ATS score above
        </p>
      </div>
    </motion.div>
  );
}
