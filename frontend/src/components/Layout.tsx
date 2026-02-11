import { useState } from "react";
import {
  FileText,
  Menu,
  X,
  Github,
  Sparkles,
  RotateCcw,
} from "lucide-react";
import type { AppStep } from "../types";

interface Props {
  step: AppStep;
  onReset: () => void;
  children: React.ReactNode;
}

const STEPS: { key: AppStep; label: string; num: number }[] = [
  { key: "upload", label: "Upload", num: 1 },
  { key: "describe", label: "Job Description", num: 2 },
  { key: "analyze", label: "Analyze", num: 3 },
  { key: "generate", label: "Generate", num: 4 },
];

export default function Layout({ step, onReset, children }: Props) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const currentIdx = STEPS.findIndex((s) => s.key === step);

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Navbar ── */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-4 h-14 sm:h-16">
          {/* Logo */}
          <button onClick={onReset} className="flex items-center gap-2 group">
            <div className="size-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
              <FileText className="size-4 text-white" />
            </div>
            <span className="font-bold text-lg hidden sm:inline bg-gradient-to-r from-primary-600 to-accent-600 bg-clip-text text-transparent">
              ATS Resume
            </span>
          </button>

          {/* Desktop stepper */}
          <nav className="hidden md:flex items-center gap-1">
            {STEPS.map((s, i) => (
              <div key={s.key} className="flex items-center">
                <div
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                    i <= currentIdx
                      ? "bg-primary-50 text-primary-700"
                      : "text-slate-400"
                  } ${i === currentIdx ? "ring-2 ring-primary-200" : ""}`}
                >
                  <span
                    className={`size-5 rounded-full text-xs flex items-center justify-center font-bold ${
                      i < currentIdx
                        ? "bg-primary-500 text-white"
                        : i === currentIdx
                          ? "bg-primary-500 text-white"
                          : "bg-slate-200 text-slate-500"
                    }`}
                  >
                    {i < currentIdx ? "✓" : s.num}
                  </span>
                  {s.label}
                </div>
                {i < STEPS.length - 1 && (
                  <div
                    className={`w-6 h-0.5 mx-1 rounded ${
                      i < currentIdx ? "bg-primary-400" : "bg-slate-200"
                    }`}
                  />
                )}
              </div>
            ))}
          </nav>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={onReset}
              className="hidden sm:flex items-center gap-1 text-sm text-slate-500 hover:text-primary-600 transition-colors"
            >
              <RotateCcw className="size-3.5" />
              Start Over
            </button>
            <a
              href="https://github.com/laharikarrotu/ats_resume_app"
              target="_blank"
              rel="noreferrer"
              className="size-8 flex items-center justify-center rounded-lg hover:bg-slate-100 transition-colors text-slate-500"
            >
              <Github className="size-4" />
            </a>
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden size-8 flex items-center justify-center rounded-lg hover:bg-slate-100"
            >
              {mobileOpen ? <X className="size-5" /> : <Menu className="size-5" />}
            </button>
          </div>
        </div>

        {/* Mobile stepper */}
        {mobileOpen && (
          <nav className="md:hidden border-t border-slate-100 px-4 py-3 space-y-1 bg-white">
            {STEPS.map((s, i) => (
              <div
                key={s.key}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm ${
                  i === currentIdx
                    ? "bg-primary-50 text-primary-700 font-semibold"
                    : i < currentIdx
                      ? "text-primary-500"
                      : "text-slate-400"
                }`}
              >
                <span
                  className={`size-6 rounded-full text-xs flex items-center justify-center font-bold ${
                    i < currentIdx
                      ? "bg-primary-500 text-white"
                      : i === currentIdx
                        ? "bg-primary-500 text-white"
                        : "bg-slate-200 text-slate-500"
                  }`}
                >
                  {i < currentIdx ? "✓" : s.num}
                </span>
                {s.label}
              </div>
            ))}
          </nav>
        )}
      </header>

      {/* ── Mobile progress bar ── */}
      <div className="md:hidden h-1 bg-slate-100">
        <div
          className="h-full bg-gradient-to-r from-primary-500 to-accent-500 transition-all duration-500"
          style={{ width: `${((currentIdx + 1) / STEPS.length) * 100}%` }}
        />
      </div>

      {/* ── Main content ── */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-6 sm:py-10">
        {children}
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-slate-200 bg-white">
        <div className="max-w-6xl mx-auto px-4 py-4 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-400">
          <div className="flex items-center gap-1">
            <Sparkles className="size-3" />
            Powered by AI — Gemini Flash + GPT-4o-mini
          </div>
          <div>ATS Resume Optimizer v2.0</div>
        </div>
      </footer>
    </div>
  );
}
