import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAtRiskStudents, downloadPredictionPdf } from "../api/services";
import { AlertTriangle, Eye, Sparkles, FileDown } from "lucide-react";
import StudentDetailModal from "../components/StudentDetailModal";
import toast from "react-hot-toast";

const AtRiskPage: React.FC = () => {
  const [selectedPredictionId, setSelectedPredictionId] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["at-risk-full"],
    queryFn: () => getAtRiskStudents(200),
  });

  const students = query.data ?? [];

  const handleDownloadPdf = async (predictionId: string, studentCode: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDownloadingId(predictionId);
    try {
      const blob = await downloadPredictionPdf(predictionId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `gradematrix_diagnostic_${studentCode}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success(`PDF downloaded for ${studentCode}`);
    } catch {
      toast.error("Failed to download PDF report");
    } finally {
      setDownloadingId(null);
    }
  };

  const getFactorLabel = (f: any): string => {
    if (typeof f === "string") return f;
    if (typeof f === "object" && f !== null) {
      return f.label || f.feature || f.factor || JSON.stringify(f);
    }
    return String(f);
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <div className="ai-badge-header">
            <Sparkles size={12} /> Early Warning System
          </div>
          <h1 className="page-title flex items-center gap-2 mt-1">
            <AlertTriangle size={24} className="text-rose-500" />
            At-Risk Cohort Intelligence
          </h1>
          <p className="page-subtitle">
            Students flagged as requiring immediate academic intervention based on machine learning predictions.
          </p>
        </div>
      </div>

      <div className="card">
        {query.isLoading ? (
          <div className="skeleton-table" />
        ) : students.length === 0 ? (
          <div className="text-center py-12 text-neutral-400">
            <p className="text-base font-semibold text-neutral-200">🎉 No at-risk students currently flagged!</p>
            <p className="text-xs text-neutral-500 mt-1">All evaluated cohorts are performing above the intervention threshold.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table-styled">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Student Code / ID</th>
                  <th>Confidence</th>
                  <th>Top Contributing Factors</th>
                  <th>Predicted At</th>
                  <th style={{ textAlign: "center" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {students.map((s, i) => {
                  const displayCode = s.student_code || s.student_id || "N/A";
                  return (
                    <tr key={s.prediction_id} className="hover:bg-rose-950/20 transition-colors">
                      <td className="text-neutral-500 text-xs">{i + 1}</td>
                      <td>
                        <strong
                          className="cursor-pointer text-primary-400 hover:text-primary-300 font-semibold text-sm"
                          onClick={() => setSelectedPredictionId(s.prediction_id)}
                          title="Click to view detailed diagnostic report"
                        >
                          {displayCode}
                        </strong>
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <div className="w-20 bg-neutral-800 rounded-full h-2 overflow-hidden">
                            <div
                              className="bg-rose-500 h-full rounded-full"
                              style={{ width: `${s.confidence * 100}%` }}
                            />
                          </div>
                          <span className="text-xs font-semibold text-rose-400">
                            {(s.confidence * 100).toFixed(1)}%
                          </span>
                        </div>
                      </td>
                      <td>
                        <div className="flex flex-wrap gap-1.5">
                          {(s.top_factors ?? []).slice(0, 3).map((f, idx) => {
                            const label = getFactorLabel(f);
                            return (
                              <span key={idx} className="badge badge-at-risk text-[11px] py-0.5">
                                {label}
                              </span>
                            );
                          })}
                        </div>
                      </td>
                      <td className="text-xs text-neutral-400">
                        {new Date(s.predicted_at).toLocaleDateString()}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <div className="inline-flex items-center gap-2">
                          <button
                            type="button"
                            className="btn btn-secondary btn-xs flex items-center gap-1"
                            onClick={() => setSelectedPredictionId(s.prediction_id)}
                          >
                            <Eye size={12} /> View
                          </button>
                          <button
                            type="button"
                            className="btn btn-primary btn-xs flex items-center gap-1"
                            disabled={downloadingId === s.prediction_id}
                            onClick={(e) => handleDownloadPdf(s.prediction_id, displayCode, e)}
                            title="Download PDF Diagnostic"
                          >
                            <FileDown size={12} />
                            {downloadingId === s.prediction_id ? "..." : "PDF"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Student Detail Modal */}
      {selectedPredictionId && (
        <StudentDetailModal
          predictionId={selectedPredictionId}
          onClose={() => setSelectedPredictionId(null)}
        />
      )}
    </div>
  );
};

export default AtRiskPage;
