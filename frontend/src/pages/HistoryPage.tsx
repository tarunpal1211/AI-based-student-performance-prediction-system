import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getHistory, deleteHistory, downloadPredictionPdf } from "../api/services";
import type { PredictionHistoryItem } from "../api/services";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";
import {
  Trash2,
  ChevronLeft,
  ChevronRight,
  Eye,
  Sparkles,
  Search,
  FileDown,
  Download,
} from "lucide-react";
import StudentDetailModal from "../components/StudentDetailModal";

const CATEGORIES = ["", "At-Risk", "Needs Improvement", "Performing Well"];
const FEATURE_SETS = ["", "early", "mid"];

const BADGE_CLASS: Record<string, string> = {
  "At-Risk": "badge-at-risk",
  "Needs Improvement": "badge-needs-improvement",
  "Performing Well": "badge-performing-well",
};

const HistoryPage: React.FC = () => {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [skip, setSkip] = useState(0);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [featureSet, setFeatureSet] = useState("");
  const [selectedPrediction, setSelectedPrediction] = useState<PredictionHistoryItem | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const limit = 20;

  const query = useQuery({
    queryKey: ["history", skip, search, category, featureSet],
    queryFn: () =>
      getHistory({
        skip,
        limit,
        search: search.trim() || undefined,
        category: category || undefined,
        feature_set: featureSet || undefined,
      }),
  });

  const deleteMut = useMutation({
    mutationFn: deleteHistory,
    onSuccess: () => {
      toast.success("Prediction deleted.");
      qc.invalidateQueries({ queryKey: ["history"] });
    },
    onError: () => toast.error("Failed to delete."),
  });

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

  const handleExportCsv = async () => {
    const token = localStorage.getItem("gradematrix_token") || localStorage.getItem("token");
    try {
      const res = await fetch("/api/reports/export/csv", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "gradematrix_predictions.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Predictions exported as CSV");
    } catch {
      toast.error("Failed to export CSV");
    }
  };

  const handleExportExcel = async () => {
    const token = localStorage.getItem("gradematrix_token") || localStorage.getItem("token");
    try {
      const res = await fetch("/api/reports/export/excel", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "gradematrix_predictions.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Predictions exported as Excel");
    } catch {
      toast.error("Failed to export Excel");
    }
  };

  const data: PredictionHistoryItem[] = query.data ?? [];

  return (
    <div className="page-container space-y-6">
      <div className="page-header flex-wrap">
        <div>
          <div className="ai-badge-header">
            <Sparkles size={12} /> Prediction Archive
          </div>
          <h1 className="page-title mt-1">Prediction History</h1>
          <p className="page-subtitle">
            Comprehensive audit log of individual and bulk evaluations with search and diagnostic exports.
          </p>
        </div>

        {/* Global Export Buttons */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleExportCsv}
            className="btn btn-secondary btn-sm flex items-center gap-1.5"
            title="Download complete history as CSV"
          >
            <Download size={14} /> Export CSV
          </button>
          <button
            type="button"
            onClick={handleExportExcel}
            className="btn btn-secondary btn-sm flex items-center gap-1.5"
            title="Download complete history as Excel"
          >
            <Download size={14} /> Export Excel
          </button>
        </div>
      </div>

      {/* Advanced Filter Bar */}
      <div className="card p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-center">
          {/* Search Box */}
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setSkip(0);
              }}
              placeholder="Search Student Code, ID..."
              className="form-input pl-9 text-xs"
            />
          </div>

          {/* Category Filter */}
          <div>
            <select
              value={category}
              onChange={(e) => {
                setCategory(e.target.value);
                setSkip(0);
              }}
              className="form-input text-xs"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c ? `Category: ${c}` : "All Categories"}
                </option>
              ))}
            </select>
          </div>

          {/* Model Filter */}
          <div>
            <select
              value={featureSet}
              onChange={(e) => {
                setFeatureSet(e.target.value);
                setSkip(0);
              }}
              className="form-input text-xs"
            >
              {FEATURE_SETS.map((f) => (
                <option key={f} value={f}>
                  {f ? `${f.toUpperCase()} model` : "All Assessment Models"}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Data Table */}
      <div className="card">
        {query.isLoading ? (
          <div className="skeleton-table" />
        ) : data.length === 0 ? (
          <div className="text-center py-12 text-neutral-400">
            <p className="text-sm font-semibold text-neutral-200">No predictions found matching the criteria.</p>
            <p className="text-xs text-neutral-500 mt-1">Try broadening your search term or clearing filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table-styled">
              <thead>
                <tr>
                  <th>Student Code / ID</th>
                  <th>Model</th>
                  <th>Category</th>
                  <th>Confidence</th>
                  <th>G1 Grade</th>
                  <th>Absences</th>
                  <th>Failures</th>
                  <th>Evaluated At</th>
                  <th style={{ textAlign: "center" }}>Diagnostic Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row) => {
                  const displayCode = row.student_code || (row.student_id ? String(row.student_id).substring(0, 8) : "—");
                  return (
                    <tr key={row.id} className="hover:bg-neutral-800/40 transition-colors">
                      <td>
                        <strong
                          className="cursor-pointer text-primary-400 hover:text-primary-300 font-semibold text-sm"
                          onClick={() => setSelectedPrediction(row)}
                          title="Click to view detailed diagnostic report"
                        >
                          {displayCode}
                        </strong>
                      </td>
                      <td>
                        <span className="badge badge-neutral uppercase text-[10px]">
                          {row.feature_set}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${BADGE_CLASS[row.category] ?? "badge-neutral"}`}>
                          {row.category}
                        </span>
                      </td>
                      <td className="text-neutral-200 font-semibold">
                        {(row.confidence * 100).toFixed(1)}%
                      </td>
                      <td>{row.input_features?.G1 !== undefined ? `${row.input_features.G1}/20` : "—"}</td>
                      <td>{row.input_features?.absences ?? "—"}</td>
                      <td>{row.input_features?.failures ?? "—"}</td>
                      <td className="text-xs text-neutral-400">
                        {new Date(row.predicted_at).toLocaleDateString()}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            type="button"
                            className="btn btn-secondary btn-xs flex items-center gap-1"
                            onClick={() => setSelectedPrediction(row)}
                            title="Inspect full AI explanation and interventions"
                          >
                            <Eye size={12} /> View
                          </button>
                          <button
                            type="button"
                            className="btn btn-primary btn-xs flex items-center gap-1"
                            disabled={downloadingId === row.id}
                            onClick={(e) => handleDownloadPdf(row.id, displayCode, e)}
                            title="Download Official PDF Report"
                          >
                            <FileDown size={12} />
                            {downloadingId === row.id ? "..." : "PDF"}
                          </button>
                          {user?.role === "admin" && (
                            <button
                              type="button"
                              className="btn btn-secondary btn-xs text-rose-400 hover:bg-rose-950/40 p-1"
                              onClick={() => deleteMut.mutate(row.id)}
                              title="Delete record"
                              disabled={deleteMut.isPending}
                            >
                              <Trash2 size={13} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        <div className="flex items-center justify-between p-4 border-t border-neutral-800 text-xs text-neutral-400">
          <div>
            Showing records {skip + 1} – {skip + data.length}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="btn btn-secondary btn-xs flex items-center gap-1"
              disabled={skip === 0}
              onClick={() => setSkip(Math.max(0, skip - limit))}
            >
              <ChevronLeft size={14} /> Previous
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-xs flex items-center gap-1"
              disabled={data.length < limit}
              onClick={() => setSkip(skip + limit)}
            >
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Student Detail Modal */}
      {selectedPrediction && (
        <StudentDetailModal
          predictionId={selectedPrediction.id}
          initialData={selectedPrediction}
          onClose={() => setSelectedPrediction(null)}
        />
      )}
    </div>
  );
};

export default HistoryPage;
