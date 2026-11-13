import React, { useState, useEffect } from "react";
import {
  TrendingUp,
  Search,
  FileDown,
  Calendar,
  Layers,
  ArrowRight,
  TrendingDown,
  Minus,
  AlertCircle,
  Eye,
  User,
} from "lucide-react";
import { getStudentProgress, downloadStudentPdf, type PredictionHistoryItem } from "../api/services";
import StudentDetailModal from "../components/StudentDetailModal";
import toast from "react-hot-toast";

const ProgressPage: React.FC = () => {
  const [studentCodeInput, setStudentCodeInput] = useState<string>("R23EF001");
  const [activeCode, setActiveCode] = useState<string>("R23EF001");
  const [loading, setLoading] = useState<boolean>(false);
  const [history, setHistory] = useState<PredictionHistoryItem[]>([]);
  const [downloadingPdf, setDownloadingPdf] = useState<boolean>(false);
  const [selectedPredictionId, setSelectedPredictionId] = useState<string | null>(null);

  const fetchStudentData = async (code: string) => {
    if (!code.trim()) return;
    setLoading(true);
    try {
      const data = await getStudentProgress(code.trim());
      setHistory(data);
      setActiveCode(code.trim());
      if (data.length === 0) {
        toast("No prediction records found for this student code.", { icon: "ℹ️" });
      }
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to load student progress.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudentData("R23EF001");
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchStudentData(studentCodeInput);
  };

  const handleDownloadPdf = async () => {
    if (!activeCode) return;
    setDownloadingPdf(true);
    try {
      const blob = await downloadStudentPdf(activeCode);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `gradematrix_report_${activeCode}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success(`PDF report downloaded for ${activeCode}`);
    } catch (err) {
      toast.error("Failed to download PDF diagnostic report.");
    } finally {
      setDownloadingPdf(false);
    }
  };

  const getCategoryClass = (cat: string) => {
    if (cat === "At-Risk") return "badge-at-risk";
    if (cat === "Needs Improvement") return "badge-needs-improvement";
    return "badge-performing-well";
  };

  // Trajectory direction computation
  const rank = (c: string) => (c === "At-Risk" ? 0 : c === "Needs Improvement" ? 1 : 2);
  const first = history.length > 0 ? history[0] : null;
  const latest = history.length > 0 ? history[history.length - 1] : null;

  let trajectory: "improved" | "deteriorated" | "stable" = "stable";
  if (first && latest && history.length > 1) {
    if (rank(latest.category) > rank(first.category)) trajectory = "improved";
    else if (rank(latest.category) < rank(first.category)) trajectory = "deteriorated";
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <TrendingUp className="text-primary-400" size={28} />
            Student Progress Tracking
          </h1>
          <p className="page-subtitle">
            Longitudinal assessment timeline, category transitions, and performance trajectory across academic periods.
          </p>
        </div>

        {/* Action Button: Download Diagnostic PDF */}
        {history.length > 0 && (
          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            className="btn btn-primary flex items-center gap-2"
          >
            <FileDown size={16} />
            {downloadingPdf ? "Generating PDF..." : "Download Diagnostic PDF Report"}
          </button>
        )}
      </div>

      {/* Student Search & Filter Bar */}
      <div className="card mb-6">
        <form onSubmit={handleSearch} className="flex flex-wrap items-center gap-4">
          <div className="flex-1 min-w-[240px] relative">
            <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-neutral-400" />
            <input
              type="text"
              value={studentCodeInput}
              onChange={(e) => setStudentCodeInput(e.target.value)}
              placeholder="Enter Student Code (e.g. R23EF001, R23EF005) or Student UUID..."
              className="form-input pl-10"
            />
          </div>
          <button type="submit" disabled={loading} className="btn btn-primary flex items-center gap-2">
            <Search size={16} />
            {loading ? "Searching..." : "Track Student"}
          </button>

          {/* Quick presets */}
          <div className="flex items-center gap-2 text-xs text-neutral-400">
            <span>Quick:</span>
            {["R23EF001", "R23EF002", "R23EF003", "R23EF005"].map((code) => (
              <button
                key={code}
                type="button"
                onClick={() => {
                  setStudentCodeInput(code);
                  fetchStudentData(code);
                }}
                className="btn-xs-tag"
              >
                {code}
              </button>
            ))}
          </div>
        </form>
      </div>

      {loading ? (
        <div className="card text-center py-16 text-neutral-400">
          <div className="animate-spin text-primary-400 mb-2 inline-block">⌛</div>
          <div>Loading student progression timeline...</div>
        </div>
      ) : history.length === 0 ? (
        <div className="card text-center py-16 text-neutral-400">
          <AlertCircle size={36} className="mx-auto mb-3 text-neutral-500" />
          <h3 className="text-base font-semibold text-neutral-200">No Assessment History Found</h3>
          <p className="text-sm mt-1 max-w-md mx-auto text-neutral-400">
            No predictions are currently linked to student code <strong>"{activeCode}"</strong>. Make a single or batch prediction with this student code to populate their timeline.
          </p>
        </div>
      ) : (
        <>
          {/* Summary KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="card">
              <div className="text-xs text-neutral-400 mb-1 flex items-center gap-1.5">
                <User size={14} className="text-primary-400" />
                Active Student
              </div>
              <div className="text-lg font-bold text-neutral-100">{activeCode}</div>
              <div className="text-xs text-neutral-500 mt-1">Code / Registration ID</div>
            </div>

            <div className="card">
              <div className="text-xs text-neutral-400 mb-1">Baseline Assessment</div>
              <div className="flex items-center gap-2 mt-1">
                <span className={`badge ${getCategoryClass(first?.category || "")}`}>
                  {first?.category}
                </span>
                <span className="text-xs text-neutral-400 font-medium">
                  {((first?.confidence || 0) * 100).toFixed(0)}%
                </span>
              </div>
              <div className="text-xs text-neutral-500 mt-1">
                {first?.predicted_at ? new Date(first.predicted_at).toLocaleDateString() : ""}
              </div>
            </div>

            <div className="card">
              <div className="text-xs text-neutral-400 mb-1">Latest Assessment</div>
              <div className="flex items-center gap-2 mt-1">
                <span className={`badge ${getCategoryClass(latest?.category || "")}`}>
                  {latest?.category}
                </span>
                <span className="text-xs text-neutral-400 font-medium">
                  {((latest?.confidence || 0) * 100).toFixed(0)}%
                </span>
              </div>
              <div className="text-xs text-neutral-500 mt-1">
                {latest?.predicted_at ? new Date(latest.predicted_at).toLocaleDateString() : ""}
              </div>
            </div>

            <div className="card">
              <div className="text-xs text-neutral-400 mb-1">Overall Trajectory</div>
              <div className="flex items-center gap-2 mt-1">
                {trajectory === "improved" ? (
                  <div className="shift-pill improved">
                    <TrendingUp size={16} /> Improved
                  </div>
                ) : trajectory === "deteriorated" ? (
                  <div className="shift-pill worsened">
                    <TrendingDown size={16} /> Deteriorated
                  </div>
                ) : (
                  <div className="shift-pill unchanged">
                    <Minus size={16} /> Consistent
                  </div>
                )}
              </div>
              <div className="text-xs text-neutral-500 mt-1">
                {history.length} assessment record{history.length > 1 ? "s" : ""}
              </div>
            </div>
          </div>

          {/* Visual Trajectory Graph Card */}
          <div className="card mb-6">
            <div className="card-header flex items-center justify-between">
              <div className="card-title flex items-center gap-2">
                <Layers size={18} className="text-primary-400" />
                Performance Category & Confidence Trajectory
              </div>
              <span className="text-xs text-neutral-400">
                Chronological sequence from earliest to most recent
              </span>
            </div>

            {/* Trajectory Milestone Strip */}
            <div className="trajectory-strip">
              {history.map((item, idx) => (
                <React.Fragment key={item.id}>
                  <div className="trajectory-node-box">
                    <div className="text-[11px] text-neutral-400 font-medium mb-1">
                      Assessment #{idx + 1}
                    </div>
                    <div className={`status-badge-sm ${getCategoryClass(item.category)}`}>
                      {item.category}
                    </div>
                    <div className="text-xs font-semibold text-neutral-200 mt-2">
                      {(item.confidence * 100).toFixed(1)}% Conf.
                    </div>
                    <div className="text-[10px] text-neutral-500 mt-0.5">
                      {new Date(item.predicted_at).toLocaleDateString()}
                    </div>
                    <button
                      type="button"
                      onClick={() => setSelectedPredictionId(item.id)}
                      className="btn btn-secondary btn-xs mt-3 flex items-center gap-1 mx-auto"
                    >
                      <Eye size={12} /> View
                    </button>
                  </div>
                  {idx < history.length - 1 && (
                    <div className="trajectory-connector">
                      <ArrowRight size={18} className="text-neutral-600" />
                    </div>
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Timeline Details List */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-neutral-300 uppercase tracking-wider">
              Assessment Chronology & Clinical Detail
            </h3>

            {history.map((p, idx) => (
              <div key={p.id} className="card hover:border-neutral-700 transition-colors">
                <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-neutral-800">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-primary-400 bg-primary-950/60 px-2 py-1 rounded border border-primary-800/40">
                      Assessment #{idx + 1}
                    </span>
                    <span className={`badge ${getCategoryClass(p.category)}`}>
                      {p.category}
                    </span>
                    <span className="text-xs text-neutral-400">
                      Confidence: <strong className="text-neutral-200">{(p.confidence * 100).toFixed(1)}%</strong>
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-xs text-neutral-400">
                    <span className="flex items-center gap-1">
                      <Calendar size={13} />
                      {new Date(p.predicted_at).toLocaleString()}
                    </span>
                    <button
                      type="button"
                      onClick={() => setSelectedPredictionId(p.id)}
                      className="btn btn-secondary btn-sm flex items-center gap-1"
                    >
                      <Eye size={13} /> View Full Diagnostic
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-3 mt-3 text-xs">
                  <div className="bg-surface-900 p-2.5 rounded border border-neutral-800">
                    <span className="text-neutral-400 block mb-0.5">Model Phase</span>
                    <span className="font-semibold text-neutral-200 uppercase">{p.feature_set} Model</span>
                  </div>
                  <div className="bg-surface-900 p-2.5 rounded border border-neutral-800">
                    <span className="text-neutral-400 block mb-0.5">First Period (G1)</span>
                    <span className="font-semibold text-neutral-200">{p.input_features?.G1 ?? "N/A"}/20</span>
                  </div>
                  {p.feature_set === "mid" && (
                    <div className="bg-surface-900 p-2.5 rounded border border-neutral-800">
                      <span className="text-neutral-400 block mb-0.5">Second Period (G2)</span>
                      <span className="font-semibold text-neutral-200">{p.input_features?.G2 ?? "N/A"}/20</span>
                    </div>
                  )}
                  <div className="bg-surface-900 p-2.5 rounded border border-neutral-800">
                    <span className="text-neutral-400 block mb-0.5">Absences</span>
                    <span className="font-semibold text-neutral-200">{p.input_features?.absences ?? 0} days</span>
                  </div>
                  <div className="bg-surface-900 p-2.5 rounded border border-neutral-800">
                    <span className="text-neutral-400 block mb-0.5">Study Time</span>
                    <span className="font-semibold text-neutral-200">Level {p.input_features?.studytime ?? "N/A"}</span>
                  </div>
                  <div className="bg-surface-900 p-2.5 rounded border border-neutral-800">
                    <span className="text-neutral-400 block mb-0.5">Past Failures</span>
                    <span className="font-semibold text-neutral-200">{p.input_features?.failures ?? 0}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Detail Modal */}
      {selectedPredictionId && (
        <StudentDetailModal
          predictionId={selectedPredictionId}
          onClose={() => setSelectedPredictionId(null)}
        />
      )}
    </div>
  );
};

export default ProgressPage;
