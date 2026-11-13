import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getPredictionDetail,
  getRecommendations,
  toggleRecommendation,
  downloadPredictionPdf,
} from "../api/services";
import type { PredictionHistoryItem } from "../api/services";
import {
  X,
  CheckCircle,
  AlertTriangle,
  TrendingUp,
  Lightbulb,
  BrainCircuit,
  Calendar,
  Layers,
  Sparkles,
  FileDown,
  CheckSquare,
  Square,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import toast from "react-hot-toast";

interface StudentDetailModalProps {
  predictionId: string | null;
  onClose: () => void;
  initialData?: Partial<PredictionHistoryItem> | null;
}

const CATEGORY_CONFIG: Record<string, { icon: React.ReactNode; color: string; bg: string }> = {
  "At-Risk": { icon: <AlertTriangle size={24} />, color: "#ef4444", bg: "#fef2f2" },
  "Needs Improvement": { icon: <TrendingUp size={24} />, color: "#f59e0b", bg: "#fffbeb" },
  "Performing Well": { icon: <CheckCircle size={24} />, color: "#22c55e", bg: "#f0fdf4" },
};

const StudentDetailModal: React.FC<StudentDetailModalProps> = ({
  predictionId,
  onClose,
  initialData,
}) => {
  const queryClient = useQueryClient();
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const detailQuery = useQuery({
    queryKey: ["prediction-detail", predictionId],
    queryFn: () => getPredictionDetail(predictionId!),
    enabled: !!predictionId,
  });

  const recQuery = useQuery({
    queryKey: ["recommendations", predictionId],
    queryFn: () => getRecommendations(predictionId!),
    enabled: !!predictionId,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ idx }: { idx: number }) => toggleRecommendation(predictionId!, idx),
    onSuccess: (data) => {
      queryClient.setQueryData(["recommendations", predictionId], data);
      toast.success("Intervention status updated");
    },
    onError: () => {
      toast.error("Failed to update status");
    },
  });

  if (!predictionId) return null;

  const data = detailQuery.data || initialData;
  const category = data?.category || "Performing Well";
  const cfg = CATEGORY_CONFIG[category] || CATEGORY_CONFIG["Performing Well"];
  const inputs = (data as any)?.input_features || {};
  const studentDisplay = (data as any)?.student_code || data?.student_id || "Student Profile";
  const explanation = (data as any)?.explanation;

  const handleDownloadPdf = async () => {
    if (!predictionId) return;
    setDownloadingPdf(true);
    try {
      const blob = await downloadPredictionPdf(predictionId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `gradematrix_diagnostic_${studentDisplay}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Diagnostic PDF report downloaded");
    } catch {
      toast.error("Failed to download PDF report");
    } finally {
      setDownloadingPdf(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="details-modal max-w-3xl" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div>
            <div className="flex items-center gap-2">
              <span className="ai-badge-header">
                <Sparkles size={11} /> Academic Diagnostic
              </span>
              <h3 className="text-lg font-bold text-neutral-100 m-0">
                {studentDisplay}
              </h3>
            </div>
            <div className="flex items-center gap-3 mt-1 text-xs text-neutral-400">
              {data?.model_name && (
                <span className="inline-flex items-center gap-1">
                  <Layers size={13} /> {data.model_name} ({data.feature_set} model)
                </span>
              )}
              {data?.predicted_at && (
                <span className="inline-flex items-center gap-1">
                  <Calendar size={13} /> {new Date(data.predicted_at).toLocaleString()}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleDownloadPdf}
              disabled={downloadingPdf}
              className="btn btn-secondary btn-sm flex items-center gap-1.5"
              title="Download institutional publication-ready PDF report"
            >
              <FileDown size={14} />
              {downloadingPdf ? "Generating..." : "Download PDF"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 text-neutral-400 hover:text-white rounded-lg transition-colors"
              title="Close"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="modal-body space-y-5">
          {detailQuery.isLoading && !initialData ? (
            <div className="py-12 text-center">
              <div className="spinner mx-auto mb-3" />
              <p className="text-xs text-neutral-400">Loading student diagnostic data...</p>
            </div>
          ) : (
            <>
              {/* Prediction Outcome Banner */}
              <div
                style={{
                  background: cfg.bg,
                  border: `1px solid ${cfg.color}`,
                  borderRadius: 12,
                  padding: "16px 20px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <div className="flex items-center gap-3">
                  <div style={{ color: cfg.color }}>{cfg.icon}</div>
                  <div>
                    <div style={{ fontSize: 11, textTransform: "uppercase", fontWeight: 700, color: cfg.color }}>
                      Predicted Academic Category
                    </div>
                    <div style={{ fontSize: 20, fontWeight: 800, color: cfg.color, marginTop: 2 }}>
                      {category}
                    </div>
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-[11px] text-neutral-500 uppercase font-semibold">
                    Confidence
                  </div>
                  <div style={{ fontSize: 22, fontWeight: 800, color: cfg.color }}>
                    {data?.confidence !== undefined ? `${(data.confidence * 100).toFixed(1)}%` : "—"}
                  </div>
                </div>
              </div>

              {/* Explainable AI Narrative & Directional Attribution */}
              {explanation ? (
                <div className="card bg-surface-900 border border-neutral-700/60 p-4 rounded-xl">
                  <h4 className="text-xs uppercase font-bold text-primary-400 tracking-wider mb-2 flex items-center gap-1.5">
                    <Sparkles size={14} /> Explainable AI (XAI) Attributions
                  </h4>

                  {/* Summary Narrative */}
                  {explanation.summary && (
                    <p className="text-xs text-neutral-200 leading-relaxed bg-surface-950/70 p-3 rounded-lg border border-neutral-800 mb-4">
                      {explanation.summary}
                    </p>
                  )}

                  {/* Directional Factors Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {/* Risk Factors */}
                    <div className="bg-rose-950/20 border border-rose-900/40 rounded-lg p-3">
                      <div className="text-xs font-semibold text-rose-400 flex items-center gap-1.5 mb-2">
                        <ShieldAlert size={14} /> Risk-Increasing Factors
                      </div>
                      {explanation.risk_factors && explanation.risk_factors.length > 0 ? (
                        <div className="space-y-1.5">
                          {explanation.risk_factors.map((f: any, i: number) => (
                            <div key={i} className="text-xs text-neutral-300 flex items-start gap-1.5">
                              <span className="text-rose-400 font-bold">•</span>
                              <div>
                                <span className="font-semibold text-neutral-200">{f.label || f.feature}:</span>{" "}
                                <span className="text-neutral-300">{f.description || `Increased failure risk`}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-xs text-neutral-400 italic">No primary risk factors identified.</div>
                      )}
                    </div>

                    {/* Protective Factors */}
                    <div className="bg-emerald-950/20 border border-emerald-900/40 rounded-lg p-3">
                      <div className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5 mb-2">
                        <ShieldCheck size={14} /> Protective / Mitigating Factors
                      </div>
                      {explanation.protective_factors && explanation.protective_factors.length > 0 ? (
                        <div className="space-y-1.5">
                          {explanation.protective_factors.map((f: any, i: number) => (
                            <div key={i} className="text-xs text-neutral-300 flex items-start gap-1.5">
                              <span className="text-emerald-400 font-bold">•</span>
                              <div>
                                <span className="font-semibold text-neutral-200">{f.label || f.feature}:</span>{" "}
                                <span className="text-neutral-300">{f.description || `Positively sustained performance`}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-xs text-neutral-400 italic">No prominent protective factors found.</div>
                      )}
                    </div>
                  </div>
                </div>
              ) : null}

              {/* Input Attributes */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300 mb-2.5 flex items-center gap-1.5">
                  <BrainCircuit size={15} className="text-primary-400" />
                  Academic Input Parameters
                </h4>
                <div className="inputs-grid">
                  <div className="input-metric">
                    <div className="k">G1 (Period 1)</div>
                    <div className="v">{inputs.G1 !== undefined ? `${inputs.G1} / 20` : "—"}</div>
                  </div>
                  {inputs.G2 !== undefined && (
                    <div className="input-metric">
                      <div className="k">G2 (Period 2)</div>
                      <div className="v">{inputs.G2} / 20</div>
                    </div>
                  )}
                  <div className="input-metric">
                    <div className="k">Absences</div>
                    <div className="v">{inputs.absences ?? "—"} days</div>
                  </div>
                  <div className="input-metric">
                    <div className="k">Study Time</div>
                    <div className="v">
                      {inputs.studytime === 1
                        ? "< 2 hrs"
                        : inputs.studytime === 2
                        ? "2–5 hrs"
                        : inputs.studytime === 3
                        ? "5–10 hrs"
                        : inputs.studytime === 4
                        ? "> 10 hrs"
                        : inputs.studytime ?? "—"}
                    </div>
                  </div>
                  <div className="input-metric">
                    <div className="k">Past Failures</div>
                    <div className="v">{inputs.failures ?? "—"}</div>
                  </div>
                  {inputs.assignment_rate !== undefined && (
                    <div className="input-metric">
                      <div className="k">Assignment Rate</div>
                      <div className="v">{inputs.assignment_rate}%</div>
                    </div>
                  )}
                  {inputs.assessment_trend !== undefined && (
                    <div className="input-metric">
                      <div className="k">Assessment Trend</div>
                      <div className="v">
                        {inputs.assessment_trend > 0 ? `+${inputs.assessment_trend}` : inputs.assessment_trend}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Personalized Recommendations with Completion Toggle */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300 mb-2.5 flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Lightbulb size={15} className="text-primary-400" />
                    Actionable Interventions & Completion Tracking
                  </span>
                  <span className="text-[11px] text-neutral-400 normal-case">
                    Click checkbox to toggle intervention status
                  </span>
                </h4>

                {recQuery.isLoading ? (
                  <div className="skeleton-card h-28" />
                ) : recQuery.data && recQuery.data.recommendations.length > 0 ? (
                  <div className="space-y-2.5">
                    {recQuery.data.recommendations.map((rec: any, i: number) => {
                      const priority = (rec.priority || "medium").toLowerCase();
                      const area = rec.area || rec.category || "ACADEMIC INTERVENTION";
                      const title = rec.title || rec.tip || "Recommended Action";
                      const description = rec.description || rec.tip;
                      const action = rec.action;
                      const isCompleted = !!rec.completed;

                      return (
                        <div
                          key={i}
                          className={`p-3.5 rounded-xl border transition-all ${
                            isCompleted
                              ? "bg-surface-950/40 border-neutral-800 opacity-75"
                              : "bg-surface-900 border-neutral-700/80 hover:border-neutral-600"
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            {/* Toggle Completion Checkbox */}
                            <button
                              type="button"
                              onClick={() => toggleMutation.mutate({ idx: i })}
                              disabled={toggleMutation.isPending}
                              className="mt-0.5 text-primary-400 hover:text-primary-300 transition-colors flex-shrink-0"
                              title={isCompleted ? "Mark as pending" : "Mark as completed"}
                            >
                              {isCompleted ? (
                                <CheckSquare size={19} className="text-emerald-400" />
                              ) : (
                                <Square size={19} className="text-neutral-400" />
                              )}
                            </button>

                            <div className="flex-1">
                              <div className="flex items-center justify-between gap-2">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-400">
                                  {area}
                                </span>
                                <div className="flex items-center gap-2">
                                  {isCompleted && (
                                    <span className="text-[10px] text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/40 font-semibold">
                                      Completed
                                    </span>
                                  )}
                                  <span className={`badge ${priority === "high" ? "badge-at-risk" : "badge-needs-improvement"}`}>
                                    {rec.priority || "MEDIUM"}
                                  </span>
                                </div>
                              </div>

                              <div className={`font-semibold text-sm mt-1 ${isCompleted ? "line-through text-neutral-400" : "text-neutral-100"}`}>
                                {title}
                              </div>

                              {description && description !== title && (
                                <div className="text-xs text-neutral-300 mt-1 leading-relaxed">
                                  {description}
                                </div>
                              )}

                              {action && (
                                <div className="text-xs font-semibold text-primary-400 mt-2">
                                  → Action Plan: {action}
                                </div>
                              )}

                              {isCompleted && rec.completed_at && (
                                <div className="text-[10px] text-neutral-500 mt-2">
                                  Marked completed on {new Date(rec.completed_at).toLocaleDateString()}
                                  {rec.completed_by ? ` by ${rec.completed_by}` : ""}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="p-4 bg-surface-900 rounded-lg border border-neutral-800 text-center text-xs text-neutral-400">
                    No specific interventions logged. Student is tracking in standard curriculum pathway.
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="modal-footer flex items-center justify-between">
          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            className="btn btn-primary btn-sm flex items-center gap-2"
          >
            <FileDown size={14} />
            {downloadingPdf ? "Generating PDF..." : "Export Official PDF Report"}
          </button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default StudentDetailModal;
