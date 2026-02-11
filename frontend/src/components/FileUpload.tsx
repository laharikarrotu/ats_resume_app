import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  Type,
  Loader2,
} from "lucide-react";
import { uploadResumeFile, uploadResumeText } from "../api/client";
import type { UploadResponse } from "../types";

interface Props {
  onUploaded: (data: UploadResponse) => void;
  setLoading: (v: boolean) => void;
  setError: (v: string | null) => void;
  loading: boolean;
  error: string | null;
}

type Mode = "file" | "text";

export default function FileUpload({
  onUploaded,
  setLoading,
  setError,
  loading,
  error,
}: Props) {
  const [mode, setMode] = useState<Mode>("file");
  const [pasteText, setPasteText] = useState("");

  const onDrop = useCallback(
    async (accepted: File[]) => {
      if (!accepted.length) return;
      setLoading(true);
      setError(null);
      try {
        const data = await uploadResumeFile(accepted[0]);
        onUploaded(data);
      } catch (e: any) {
        setError(e.message ?? "Upload failed");
      } finally {
        setLoading(false);
      }
    },
    [onUploaded, setLoading, setError],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
    },
    maxFiles: 1,
    disabled: loading,
  });

  const handleTextSubmit = async () => {
    if (!pasteText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await uploadResumeText(pasteText);
      onUploaded(data);
    } catch (e: any) {
      setError(e.message ?? "Parsing failed");
    } finally {
      setLoading(false);
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
        <h1 className="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-primary-600 to-accent-600 bg-clip-text text-transparent">
          Optimize Your Resume
        </h1>
        <p className="mt-3 text-slate-500 text-sm sm:text-base max-w-md mx-auto">
          Upload your resume and we'll tailor it to any job description — maximizing
          your ATS score with AI.
        </p>
      </div>

      {/* Mode tabs */}
      <div className="flex bg-slate-100 rounded-xl p-1 mb-6 max-w-xs mx-auto">
        {(["file", "text"] as Mode[]).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-sm font-medium transition-all ${
              mode === m
                ? "bg-white text-primary-700 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {m === "file" ? <Upload className="size-3.5" /> : <Type className="size-3.5" />}
            {m === "file" ? "Upload File" : "Paste Text"}
          </button>
        ))}
      </div>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-4 flex items-start gap-2 bg-danger-400/10 text-danger-600 rounded-xl px-4 py-3 text-sm"
          >
            <AlertCircle className="size-4 mt-0.5 shrink-0" />
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {/* File drop zone */}
      {mode === "file" ? (
        <div
          {...getRootProps()}
          className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all ${
            isDragActive
              ? "border-primary-400 bg-primary-50"
              : "border-slate-300 hover:border-primary-300 hover:bg-slate-50"
          } ${loading ? "pointer-events-none opacity-60" : ""}`}
        >
          <input {...getInputProps()} />

          {loading ? (
            <div className="flex flex-col items-center gap-3">
              <Loader2 className="size-10 text-primary-500 animate-spin" />
              <p className="text-sm text-slate-500">Parsing your resume…</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div
                className={`size-14 rounded-2xl flex items-center justify-center transition-colors ${
                  isDragActive
                    ? "bg-primary-100 text-primary-600"
                    : "bg-slate-100 text-slate-400"
                }`}
              >
                <Upload className="size-6" />
              </div>
              <div>
                <p className="font-semibold text-slate-700">
                  {isDragActive ? "Drop it here!" : "Drag & drop your resume"}
                </p>
                <p className="text-sm text-slate-400 mt-1">
                  or <span className="text-primary-500 underline">browse files</span>{" "}
                  — PDF, DOCX, or TXT
                </p>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Text paste */
        <div className="space-y-4">
          <textarea
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            placeholder="Paste your resume text here…"
            rows={10}
            className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-300 focus:border-primary-300 resize-y placeholder:text-slate-400"
          />
          <button
            onClick={handleTextSubmit}
            disabled={loading || !pasteText.trim()}
            className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-primary-600 text-white font-medium text-sm hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="size-4 animate-spin" /> Parsing…
              </>
            ) : (
              <>
                <CheckCircle2 className="size-4" /> Parse Resume
              </>
            )}
          </button>
        </div>
      )}

      {/* Format hints */}
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        {["PDF", "DOCX", "TXT"].map((fmt) => (
          <span
            key={fmt}
            className="inline-flex items-center gap-1 bg-slate-100 text-slate-500 text-xs font-medium px-2.5 py-1 rounded-lg"
          >
            <FileText className="size-3" />
            {fmt}
          </span>
        ))}
        <span className="text-xs text-slate-400">Max 10MB</span>
      </div>
    </motion.div>
  );
}
