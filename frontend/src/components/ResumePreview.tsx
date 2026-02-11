import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronDown,
  ChevronUp,
  GraduationCap,
  Briefcase,
  Code2,
  Award,
  Wrench,
  MapPin,
  Phone,
  Mail,
  Linkedin,
  Github,
  Loader2,
} from "lucide-react";
import { getResumeData } from "../api/client";

interface Props {
  sessionId: string;
}

export default function ResumePreview({ sessionId }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!expanded || data) return;
    setLoading(true);
    getResumeData(sessionId)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [expanded, sessionId, data]);

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Toggle header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-5 py-3 hover:bg-slate-50 transition-colors text-left"
      >
        <span className="text-sm font-semibold text-slate-600 flex items-center gap-2">
          <Code2 className="size-4 text-primary-500" />
          Parsed Resume Data
        </span>
        {expanded ? (
          <ChevronUp className="size-4 text-slate-400" />
        ) : (
          <ChevronDown className="size-4 text-slate-400" />
        )}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 border-t border-slate-100 pt-4 space-y-5">
              {loading ? (
                <div className="flex items-center justify-center py-8 text-sm text-slate-400">
                  <Loader2 className="size-5 animate-spin mr-2" />
                  Loading parsed data…
                </div>
              ) : data ? (
                <>
                  {/* Contact */}
                  <Section icon={<Mail className="size-4" />} title="Contact">
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-600">
                      {data.email && (
                        <span className="flex items-center gap-1">
                          <Mail className="size-3 text-slate-400" />
                          {data.email}
                        </span>
                      )}
                      {data.phone && (
                        <span className="flex items-center gap-1">
                          <Phone className="size-3 text-slate-400" />
                          {data.phone}
                        </span>
                      )}
                      {data.location && (
                        <span className="flex items-center gap-1">
                          <MapPin className="size-3 text-slate-400" />
                          {data.location}
                        </span>
                      )}
                      {data.linkedin && (
                        <span className="flex items-center gap-1">
                          <Linkedin className="size-3 text-slate-400" />
                          <span className="truncate max-w-[200px]">
                            {data.linkedin}
                          </span>
                        </span>
                      )}
                      {data.github && (
                        <span className="flex items-center gap-1">
                          <Github className="size-3 text-slate-400" />
                          <span className="truncate max-w-[200px]">
                            {data.github}
                          </span>
                        </span>
                      )}
                    </div>
                  </Section>

                  {/* Experience */}
                  {data.experience?.length > 0 && (
                    <Section
                      icon={<Briefcase className="size-4" />}
                      title={`Experience (${data.experience.length})`}
                    >
                      <div className="space-y-3">
                        {data.experience.map((exp: any, i: number) => (
                          <div key={i} className="border-l-2 border-primary-200 pl-3">
                            <p className="text-sm font-semibold text-slate-700">
                              {exp.title}
                            </p>
                            <p className="text-xs text-slate-500">
                              {exp.company}
                              {exp.dates && ` · ${exp.dates}`}
                            </p>
                            {exp.bullets?.length > 0 && (
                              <ul className="mt-1 space-y-0.5">
                                {exp.bullets
                                  .slice(0, 3)
                                  .map((b: string, j: number) => (
                                    <li
                                      key={j}
                                      className="text-xs text-slate-500 truncate"
                                    >
                                      • {b}
                                    </li>
                                  ))}
                                {exp.bullets.length > 3 && (
                                  <li className="text-xs text-slate-400 italic">
                                    +{exp.bullets.length - 3} more bullets
                                  </li>
                                )}
                              </ul>
                            )}
                          </div>
                        ))}
                      </div>
                    </Section>
                  )}

                  {/* Education */}
                  {data.education?.length > 0 && (
                    <Section
                      icon={<GraduationCap className="size-4" />}
                      title={`Education (${data.education.length})`}
                    >
                      <div className="space-y-2">
                        {data.education.map((edu: any, i: number) => (
                          <div key={i}>
                            <p className="text-sm font-medium text-slate-700">
                              {edu.degree}
                            </p>
                            <p className="text-xs text-slate-500">
                              {edu.university}
                              {edu.dates && ` · ${edu.dates}`}
                              {edu.gpa && ` · GPA: ${edu.gpa}`}
                            </p>
                          </div>
                        ))}
                      </div>
                    </Section>
                  )}

                  {/* Skills */}
                  {Object.keys(data.skills || {}).length > 0 && (
                    <Section
                      icon={<Wrench className="size-4" />}
                      title="Skills"
                    >
                      <div className="space-y-2">
                        {Object.entries(data.skills).map(
                          ([cat, skills]: [string, any]) => (
                            <div key={cat}>
                              <p className="text-xs font-semibold text-slate-500 mb-1">
                                {cat}
                              </p>
                              <div className="flex flex-wrap gap-1">
                                {skills.map((s: string) => (
                                  <span
                                    key={s}
                                    className="px-2 py-0.5 bg-primary-50 text-primary-600 text-xs rounded-md"
                                  >
                                    {s}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ),
                        )}
                      </div>
                    </Section>
                  )}

                  {/* Projects */}
                  {data.projects?.length > 0 && (
                    <Section
                      icon={<Code2 className="size-4" />}
                      title={`Projects (${data.projects.length})`}
                    >
                      <div className="space-y-2">
                        {data.projects.map((p: any, i: number) => (
                          <div key={i}>
                            <p className="text-sm font-medium text-slate-700">
                              {p.name}
                            </p>
                            {p.technologies?.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-0.5">
                                {p.technologies.map((t: string) => (
                                  <span
                                    key={t}
                                    className="px-1.5 py-0.5 bg-slate-100 text-slate-500 text-xs rounded"
                                  >
                                    {t}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </Section>
                  )}

                  {/* Certifications */}
                  {data.certifications?.length > 0 && (
                    <Section
                      icon={<Award className="size-4" />}
                      title={`Certifications (${data.certifications.length})`}
                    >
                      <div className="space-y-1">
                        {data.certifications.map((c: any, i: number) => (
                          <p key={i} className="text-sm text-slate-600">
                            {c.name}
                            {c.issuer && (
                              <span className="text-slate-400">
                                {" "}
                                — {c.issuer}
                              </span>
                            )}
                            {c.year && (
                              <span className="text-slate-400">
                                {" "}
                                ({c.year})
                              </span>
                            )}
                          </p>
                        ))}
                      </div>
                    </Section>
                  )}
                </>
              ) : (
                <p className="text-sm text-slate-400 text-center py-4">
                  Unable to load resume data
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Section({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
        <span className="text-primary-400">{icon}</span>
        {title}
      </h4>
      {children}
    </div>
  );
}
