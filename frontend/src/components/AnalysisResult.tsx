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
  FileWarning,
  BarChart3,
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

function GradeBadge({ grade }: { grade: string }) {
  const colors: Record<string, string> = {
    "A+": "bg-success-500 text-white",
    A: "bg-success-500 text-white",
    "B+": "bg-success-400 text-white",
    B: "bg-warning-400 text-white",
    "C+": "bg-warning-500 text-white",
    C: "bg-orange-500 text-white",
    D: "bg-danger-500 text-white",
    F: "bg-danger-600 text-white",
  };

  return (
    <span
      className={`inline-flex items-center justify-center size-10 rounded-full text-lg font-bold ${colors[grade] ?? "bg-slate-400 text-white"}`}
    >
      {grade}
    </span>
  );
}

function severityColor(sev: string) {
  if (sev === "critical") return "text-danger-500";
  if (sev === "warning") return "text-warning-500";
  return "text-slate-400";
}

function severityIcon(sev: string) {
  if (sev === "critical") return <XCircle className="size-3.5 mt-0.5 shrink-0" />;
  if (sev === "warning") return <AlertTriangle className="size-3.5 mt-0.5 shrink-0" />;
  return <FileWarning className="size-3.5 mt-0.5 shrink-0" />;
}

export default function AnalysisResult({ analysis, onGenerate, loading }: Props) {
  const breakdown = analysis.score_breakdown ?? {};

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-4xl mx-auto space-y-6"
    >
      {/* Score header */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <Target className="size-5 text-primary-500" />
            ATS Compatibility Score
          </h2>
          <GradeBadge grade={analysis.grade} />
        </div>

        <div className="flex flex-wrap justify-center gap-6 sm:gap-10">
          <ScoreRing score={analysis.overall_score} label="Overall" />
          <ScoreRing score={breakdown.keyword_match ?? 0} label="Keywords (40%)" />
          <ScoreRing score={breakdown.content_quality ?? 0} label="Content (30%)" />
          <ScoreRing score={breakdown.completeness ?? 0} label="Sections (20%)" />
          <ScoreRing score={breakdown.formatting ?? 0} label="Format (10%)" />
        </div>

        {/* Keyword match stat */}
        <div className="mt-5 text-center">
          <span className="text-sm text-slate-500">
            Keyword Match:{" "}
            <span className="font-semibold text-slate-700">
              {analysis.keyword_match_percentage?.toFixed(0) ?? 0}%
            </span>
            {" · "}
            Bullets w/ Metrics:{" "}
            <span className="font-semibold text-slate-700">
              {analysis.bullets_with_metrics_pct?.toFixed(0) ?? 0}%
            </span>
            {" · "}
            Action Verbs:{" "}
            <span className="font-semibold text-slate-700">
              {analysis.bullets_with_action_verbs_pct?.toFixed(0) ?? 0}%
            </span>
          </span>
        </div>
      </div>

      {/* Two-column grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Matched keywords */}
        {analysis.matched_keywords?.length > 0 && (
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
        {analysis.missing_keywords?.length > 0 && (
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

        {/* Format issues */}
        {analysis.format_issues?.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-warning-500 flex items-center gap-1.5 mb-3">
              <AlertTriangle className="size-4" />
              Format Issues ({analysis.format_issues.length})
            </h3>
            <ul className="space-y-2">
              {analysis.format_issues.map((issue, i) => (
                <li key={i} className="text-sm flex items-start gap-2">
                  <span className={severityColor(issue.severity)}>
                    {severityIcon(issue.severity)}
                  </span>
                  <div>
                    <span className="text-slate-700">{issue.message}</span>
                    {issue.suggestion && (
                      <p className="text-xs text-slate-400 mt-0.5">{issue.suggestion}</p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Skill gaps */}
        {analysis.skill_gaps?.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-600 flex items-center gap-1.5 mb-3">
              <BarChart3 className="size-4" />
              Skill Gaps ({analysis.skill_gaps.length})
            </h3>
            <ul className="space-y-2">
              {analysis.skill_gaps.map((gap, i) => (
                <li key={i} className="text-sm">
                  <span className="font-medium text-slate-700">{gap.skill}</span>
                  <span
                    className={`ml-1.5 text-xs px-1.5 py-0.5 rounded-full ${
                      gap.importance === "critical"
                        ? "bg-danger-100 text-danger-600"
                        : gap.importance === "high"
                          ? "bg-warning-100 text-warning-600"
                          : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {gap.importance}
                  </span>
                  {gap.suggestion && (
                    <p className="text-xs text-slate-400 mt-0.5">{gap.suggestion}</p>
                  )}
                  {gap.related_skills?.length > 0 && (
                    <p className="text-xs text-primary-500 mt-0.5">
                      Related skills you have: {gap.related_skills.join(", ")}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Top recommendations */}
        {analysis.top_recommendations?.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm md:col-span-2">
            <h3 className="text-sm font-semibold text-accent-600 flex items-center gap-1.5 mb-3">
              <Lightbulb className="size-4" />
              Top Recommendations
            </h3>
            <ul className="space-y-1.5">
              {analysis.top_recommendations.map((r, i) => (
                <li key={i} className="text-sm text-slate-600 flex items-start gap-2">
                  <span className="size-5 shrink-0 rounded-full bg-accent-100 text-accent-600 text-xs flex items-center justify-center font-bold mt-0.5">
                    {i + 1}
                  </span>
                  {r}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Bullet quality summary */}
        {analysis.bullet_analyses?.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm md:col-span-2">
            <h3 className="text-sm font-semibold text-primary-600 flex items-center gap-1.5 mb-3">
              <TrendingUp className="size-4" />
              Bullet Quality (Top 5)
            </h3>
            <ul className="space-y-3">
              {analysis.bullet_analyses.slice(0, 5).map((b, i) => (
                <li key={i} className="text-sm border-l-2 border-primary-200 pl-3">
                  <p className="text-slate-500 line-through text-xs">{b.original}</p>
                  {b.improved && (
                    <p className="text-slate-700 mt-0.5">{b.improved}</p>
                  )}
                  <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                    <span>Score: {b.score}/100</span>
                    {b.has_metrics && (
                      <span className="text-success-500">✓ Has metrics</span>
                    )}
                    {b.has_action_verb && (
                      <span className="text-success-500">✓ Action verb</span>
                    )}
                    {!b.has_action_verb && b.action_verb_suggestion && (
                      <span className="text-warning-500">
                        Try: {b.action_verb_suggestion}
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
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
