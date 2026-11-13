import React, { useState, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  predictSingle,
  getRecommendations,
  uploadAndValidate,
  processBatch,
  downloadTemplate,
  exportBatchResults,
  getHistory,
} from "../api/services";
import type {
  SinglePredictRequest,
  PredictionResponse,
  UploadValidateResponse,
  BatchProcessResponse,
  BatchStudentResult,
  PreviewRow,
  BatchStudentInput,
  PredictionHistoryItem,
} from "../api/services";
import toast from "react-hot-toast";
import {
  BrainCircuit,
  CheckCircle,
  AlertTriangle,
  TrendingUp,
  Lightbulb,
  UploadCloud,
  FileSpreadsheet,
  FileText,
  Download,
  Trash2,
  ArrowLeft,
  ShieldAlert,
  Search,
  Eye,
  X,
  AlertCircle,
  FileCheck,
  Check,
  Sparkles,
} from "lucide-react";

const CATEGORY_CONFIG: Record<string, { icon: React.ReactNode; color: string; bg: string }> = {
  "At-Risk": { icon: <AlertTriangle size={24} />, color: "#ef4444", bg: "#fef2f2" },
  "Needs Improvement": { icon: <TrendingUp size={24} />, color: "#f59e0b", bg: "#fffbeb" },
  "Performing Well": { icon: <CheckCircle size={24} />, color: "#22c55e", bg: "#f0fdf4" },
};

const PredictPage: React.FC = () => {
  const qc = useQueryClient();

  // Mode Selection: "manual" (Single) or "bulk" (Batch Upload)
  const [mode, setMode] = useState<"manual" | "bulk">("manual");

  // ---------------------------------------------------------------------------
  // Option A: Manual Prediction State
  // ---------------------------------------------------------------------------
  const [manualFeatureSet, setManualFeatureSet] = useState<"early" | "mid">("early");
  const [manualForm, setManualForm] = useState({
    student_id: "",
    absences: 0,
    G1: 10,
    failures: 0,
    studytime: 2,
    G2: 10,
    assignment_rate: 75,
    assessment_trend: 0,
  });
  const [manualResult, setManualResult] = useState<PredictionResponse | null>(null);

  // Autocomplete recommendations from saved history
  const [showSuggestions, setShowSuggestions] = useState(false);
  const historyQuery = useQuery({
    queryKey: ["history", "suggestions"],
    queryFn: () => getHistory({ limit: 100 }),
  });

  const savedStudents = React.useMemo(() => {
    const list = historyQuery.data || [];
    const map = new Map<string, PredictionHistoryItem>();
    for (const item of list) {
      if (item.student_id && item.student_id.trim()) {
        const key = item.student_id.trim().toUpperCase();
        if (!map.has(key)) {
          map.set(key, item);
        }
      }
    }
    return Array.from(map.values());
  }, [historyQuery.data]);

  const filteredSuggestions = React.useMemo(() => {
    const q = manualForm.student_id.trim().toLowerCase();
    if (!q) return [];
    return savedStudents
      .filter((s) => (s.student_id || "").toLowerCase().includes(q))
      .slice(0, 6);
  }, [manualForm.student_id, savedStudents]);

  const handleSelectSuggestion = (student: PredictionHistoryItem) => {
    const feat = student.input_features || {};
    setManualForm({
      student_id: student.student_id || "",
      G1: feat.G1 !== undefined ? Number(feat.G1) : 10,
      G2: feat.G2 !== undefined ? Number(feat.G2) : 10,
      absences: feat.absences !== undefined ? Number(feat.absences) : 0,
      failures: feat.failures !== undefined ? Number(feat.failures) : 0,
      studytime: feat.studytime !== undefined ? Number(feat.studytime) : 2,
      assignment_rate: feat.assignment_rate !== undefined ? Number(feat.assignment_rate) : 75,
      assessment_trend: feat.assessment_trend !== undefined ? Number(feat.assessment_trend) : 0,
    });
    if (student.feature_set === "mid" || feat.G2 !== undefined) {
      setManualFeatureSet("mid");
    }
    setShowSuggestions(false);
    toast.success(`Loaded record for ${student.student_id}!`);
  };

  const resultsRef = useRef<HTMLDivElement>(null);

  const manualMutation = useMutation({
    mutationFn: (req: SinglePredictRequest) => predictSingle(req),
    onSuccess: (data) => {
      setManualResult(data);
      toast.success("Prediction complete!");
      qc.invalidateQueries({ queryKey: ["history"] });
      qc.invalidateQueries({ queryKey: ["class-analytics"] });
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail;
      let msg = "Prediction failed. Check inputs.";
      if (typeof detail === "string") {
        msg = detail;
      } else if (Array.isArray(detail)) {
        msg = detail.map((d: any) => d.msg || JSON.stringify(d)).join("; ");
      }
      toast.error(msg);
    },
  });

  const recQuery = useQuery({
    queryKey: ["recommendations", manualResult?.id],
    queryFn: () => getRecommendations(manualResult!.id),
    enabled: !!manualResult?.id,
  });

  const handleManualChange = (key: string, value: string | number) => {
    setManualForm((f) => ({ ...f, [key]: value }));
  };

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const req: SinglePredictRequest = {
      feature_set: manualFeatureSet,
      student_id: manualForm.student_id || undefined,
      absences: Number(manualForm.absences),
      G1: Number(manualForm.G1),
      failures: Number(manualForm.failures),
      studytime: Number(manualForm.studytime),
      assignment_rate: Number(manualForm.assignment_rate),
      assessment_trend: Number(manualForm.assessment_trend),
      ...(manualFeatureSet === "mid" ? { G2: Number(manualForm.G2) } : {}),
    };
    setManualResult(null);
    manualMutation.mutate(req);
  };

  // ---------------------------------------------------------------------------
  // Option B: Bulk Upload State
  // ---------------------------------------------------------------------------
  const [bulkStep, setBulkStep] = useState<1 | 2 | 3>(1);
  const [bulkFeatureSet, setBulkFeatureSet] = useState<"early" | "mid">("early");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [validationReport, setValidationReport] = useState<UploadValidateResponse | null>(null);
  const [previewRows, setPreviewRows] = useState<PreviewRow[]>([]);
  const [previewFilter, setPreviewFilter] = useState<"all" | "valid" | "invalid">("all");
  const [previewSearch, setPreviewSearch] = useState("");

  const [batchResponse, setBatchResponse] = useState<BatchProcessResponse | null>(null);
  const [resultCategoryFilter, setResultCategoryFilter] = useState<string>("all");
  const [resultSearch, setResultSearch] = useState("");
  const [resultSort, setResultSort] = useState<"id" | "conf_desc" | "conf_asc">("id");
  const [selectedStudentDetail, setSelectedStudentDetail] = useState<BatchStudentResult | null>(null);

  // Download template helper
  const handleDownloadTemplate = async (format: "csv" | "xlsx") => {
    try {
      toast.loading(`Generating ${format.toUpperCase()} template...`, { id: "tpl" });
      const blob = await downloadTemplate(bulkFeatureSet, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `gradematrix_student_template_${bulkFeatureSet}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success(`Template downloaded (${format.toUpperCase()})`, { id: "tpl" });
    } catch {
      toast.error("Failed to download template.", { id: "tpl" });
    }
  };

  // Drag & drop handlers
  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      handleFileSelected(file);
    }
  };

  const handleFileSelected = (file: File) => {
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    if (![".csv", ".xlsx", ".xls"].includes(ext)) {
      toast.error("Please upload a CSV or Excel (.xlsx, .xls) file.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast.error("File size exceeds 10 MB limit.");
      return;
    }
    setSelectedFile(file);
  };

  // Step 1 -> Step 2: Validate file
  const validateMutation = useMutation({
    mutationFn: () => {
      if (!selectedFile) throw new Error("No file selected");
      return uploadAndValidate(selectedFile, bulkFeatureSet);
    },
    onSuccess: (data) => {
      setValidationReport(data);
      setPreviewRows(data.preview_rows);
      setBulkStep(2);
      toast.success(data.message || "File validated successfully!");
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || err.message || "Validation failed";
      toast.error(msg);
    },
  });

  // Remove individual row in preview
  const handleRemovePreviewRow = (rowIndex: number) => {
    setPreviewRows((prev) => prev.filter((r) => r.row_index !== rowIndex));
    toast.success("Row removed from batch.");
  };

  // Step 2 -> Step 3: Run Batch Prediction
  const batchProcessMutation = useMutation({
    mutationFn: () => {
      const validRecords: BatchStudentInput[] = previewRows
        .filter((r) => r.is_valid)
        .map((r) => ({
          row_index: r.row_index,
          student_id: r.student_id,
          G1: Number(r.cleaned_data.G1),
          absences: Number(r.cleaned_data.absences),
          studytime: Number(r.cleaned_data.studytime),
          failures: Number(r.cleaned_data.failures),
          ...(bulkFeatureSet === "mid" ? { G2: Number(r.cleaned_data.G2) } : {}),
          assignment_rate:
            r.cleaned_data.assignment_rate !== undefined
              ? Number(r.cleaned_data.assignment_rate)
              : undefined,
          assessment_trend:
            r.cleaned_data.assessment_trend !== undefined
              ? Number(r.cleaned_data.assessment_trend)
              : undefined,
        }));

      if (validRecords.length === 0) {
        throw new Error("No valid student records found to process.");
      }

      return processBatch(bulkFeatureSet, validRecords);
    },
    onSuccess: (data) => {
      setBatchResponse(data);
      setBulkStep(3);
      toast.success(`Batch processed: ${data.processed_rows} predictions generated!`);
      qc.invalidateQueries({ queryKey: ["history"] });
      qc.invalidateQueries({ queryKey: ["class-analytics"] });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || err.message || "Batch processing failed.";
      toast.error(msg);
    },
  });

  // Export batch results
  const handleExportResults = async (format: "csv" | "xlsx") => {
    if (!batchResponse || !batchResponse.results.length) return;
    try {
      toast.loading(`Exporting batch results as ${format.toUpperCase()}...`, { id: "exp" });
      const blob = await exportBatchResults(batchResponse.results, format, bulkFeatureSet);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `gradematrix_predictions_${bulkFeatureSet}_${new Date().toISOString().slice(0, 10)}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success(`Export ready (${format.toUpperCase()})`, { id: "exp" });
    } catch {
      toast.error("Failed to export batch results.", { id: "exp" });
    }
  };

  // Reset bulk upload wizard
  const handleResetBulk = () => {
    setBulkStep(1);
    setSelectedFile(null);
    setValidationReport(null);
    setPreviewRows([]);
    setBatchResponse(null);
    setSelectedStudentDetail(null);
  };

  // Filtered rows for Preview (Step 2)
  const filteredPreviewRows = previewRows.filter((r) => {
    if (previewFilter === "valid" && !r.is_valid) return false;
    if (previewFilter === "invalid" && r.is_valid) return false;
    if (previewSearch.trim()) {
      const term = previewSearch.toLowerCase();
      const sId = (r.student_id || "").toLowerCase();
      const rowNum = String(r.row_index + 1);
      return sId.includes(term) || rowNum.includes(term);
    }
    return true;
  });

  const validPreviewCount = previewRows.filter((r) => r.is_valid).length;
  const invalidPreviewCount = previewRows.filter((r) => !r.is_valid).length;

  // Filtered and sorted results for Batch Dashboard (Step 3)
  const filteredBatchResults = (batchResponse?.results || [])
    .filter((r) => {
      if (resultCategoryFilter !== "all" && r.category !== resultCategoryFilter) return false;
      if (resultSearch.trim()) {
        const term = resultSearch.toLowerCase();
        return r.student_id.toLowerCase().includes(term);
      }
      return true;
    })
    .sort((a, b) => {
      if (resultSort === "conf_desc") return b.confidence - a.confidence;
      if (resultSort === "conf_asc") return a.confidence - b.confidence;
      return a.student_id.localeCompare(b.student_id);
    });

  const manualCfg = manualResult ? CATEGORY_CONFIG[manualResult.category] : null;

  return (
    <div className="page">
      <div className="page-header">
        <div className="ai-badge-header">
          <Sparkles size={13} />
          <span>AI Decision Support Engine</span>
        </div>
        <h2 className="predict-page-title">Predict Student Performance</h2>
        <p className="predict-page-subtitle">Assess student academic trajectory using trained AI machine learning models</p>
      </div>

      {/* Mode Switcher */}
      <div className="predict-mode-toggle">
        <button
          type="button"
          className={`mode-btn${mode === "manual" ? " active" : ""}`}
          onClick={() => setMode("manual")}
        >
          <BrainCircuit size={18} />
          Option A — Manual Prediction
        </button>
        <button
          type="button"
          className={`mode-btn${mode === "bulk" ? " active" : ""}`}
          onClick={() => setMode("bulk")}
        >
          <UploadCloud size={18} />
          Option B — Bulk Student Upload
        </button>
      </div>

      {/* =======================================================================
          OPTION A: MANUAL PREDICTION
      ======================================================================= */}
      {mode === "manual" && (
        <div className="predict-layout">
          {/* Form */}
          <div className="card predict-form-card">
            <form onSubmit={handleManualSubmit}>
              {/* Feature Set Toggle */}
              <div className="field-group">
                <label>Model / Feature Set</label>
                <div className="toggle-group">
                  {(["early", "mid"] as const).map((fs) => (
                    <button
                      key={fs}
                      type="button"
                      className={`toggle-btn${manualFeatureSet === fs ? " active" : ""}`}
                      onClick={() => setManualFeatureSet(fs)}
                    >
                      {fs === "early" ? "Early (G1 only)" : "Mid-term (G1 + G2)"}
                    </button>
                  ))}
                </div>
                <small className="hint">
                  {manualFeatureSet === "early"
                    ? "Uses first period grade only — best for early intervention."
                    : "Uses first & second period grades — more accurate prediction."}
                </small>
              </div>

              <div className="form-grid">
                <div className="field-group" style={{ position: "relative" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <label>Student ID (optional)</label>
                    {savedStudents.length > 0 && (
                      <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                        {savedStudents.length} saved
                      </span>
                    )}
                  </div>
                  <input
                    type="text"
                    value={manualForm.student_id}
                    onChange={(e) => {
                      handleManualChange("student_id", e.target.value);
                      setShowSuggestions(true);
                    }}
                    onFocus={() => setShowSuggestions(true)}
                    onBlur={() => setTimeout(() => setShowSuggestions(false), 220)}
                    placeholder="e.g. R23EF001 (start typing for suggestions...)"
                    autoComplete="off"
                  />

                  {/* Autocomplete suggestions dropdown */}
                  {showSuggestions && filteredSuggestions.length > 0 && (
                    <div
                      style={{
                        position: "absolute",
                        top: "100%",
                        left: 0,
                        right: 0,
                        marginTop: 4,
                        background: "var(--surface)",
                        border: "1px solid var(--border)",
                        borderRadius: 8,
                        boxShadow: "0 10px 25px -5px rgba(0,0,0,0.15)",
                        zIndex: 100,
                        maxHeight: 220,
                        overflowY: "auto",
                      }}
                    >
                      <div
                        style={{
                          padding: "6px 12px",
                          fontSize: 11,
                          fontWeight: 600,
                          color: "var(--text-muted)",
                          background: "rgba(0,0,0,0.02)",
                          borderBottom: "1px solid var(--border)",
                          display: "flex",
                          justifyContent: "space-between",
                        }}
                      >
                        <span>RECOMMENDED STUDENTS</span>
                        <span>Click to auto-fill</span>
                      </div>
                      {filteredSuggestions.map((item) => (
                        <div
                          key={item.id}
                          onMouseDown={() => handleSelectSuggestion(item)}
                          style={{
                            padding: "8px 12px",
                            cursor: "pointer",
                            borderBottom: "1px solid var(--border)",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                          }}
                        >
                          <div>
                            <strong style={{ fontSize: 13, color: "var(--text)" }}>
                              {item.student_id}
                            </strong>
                            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                              G1: {item.input_features?.G1 ?? "-"} | Absences: {item.input_features?.absences ?? "-"} | Failures: {item.input_features?.failures ?? "-"}
                            </div>
                          </div>
                          <span
                            className={`badge ${item.category === "At-Risk" ? "badge-risk" : item.category === "Needs Improvement" ? "badge-warn" : "badge-good"}`}
                            style={{ fontSize: 11, padding: "2px 8px" }}
                          >
                            {item.category}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="field-group">
                  <label>
                    G1 — First Period Grade <span className="required">*</span>
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={20}
                    step={1}
                    value={manualForm.G1}
                    onChange={(e) => handleManualChange("G1", e.target.value)}
                    required
                  />
                  <small className="hint">0–5: Very Bad &bull; 6–10: Bad &bull; 11–15: Average &bull; 16–20: Strong</small>
                </div>

                {manualFeatureSet === "mid" && (
                  <div className="field-group">
                    <label>
                      G2 — Second Period Grade <span className="required">*</span>
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={20}
                      step={1}
                      value={manualForm.G2}
                      onChange={(e) => handleManualChange("G2", e.target.value)}
                      required
                    />
                    <small className="hint">0–5: Very Bad &bull; 6–10: Bad &bull; 11–15: Average &bull; 16–20: Strong</small>
                  </div>
                )}

                <div className="field-group">
                  <label>
                    Absences <span className="required">*</span>
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={93}
                    step={1}
                    value={manualForm.absences}
                    onChange={(e) => handleManualChange("absences", e.target.value)}
                    required
                  />
                </div>

                <div className="field-group">
                  <label>
                    Study Time (hrs/week) <span className="required">*</span>
                  </label>
                  <select
                    value={manualForm.studytime}
                    onChange={(e) => handleManualChange("studytime", e.target.value)}
                  >
                    <option value={1}>1 — &lt; 2 hours</option>
                    <option value={2}>2 — 2 to 5 hours</option>
                    <option value={3}>3 — 5 to 10 hours</option>
                    <option value={4}>4 — &gt; 10 hours</option>
                  </select>
                </div>

                <div className="field-group">
                  <label>
                    Past Failures <span className="required">*</span>
                  </label>
                  <select
                    value={manualForm.failures}
                    onChange={(e) => handleManualChange("failures", e.target.value)}
                  >
                    <option value={0}>0</option>
                    <option value={1}>1</option>
                    <option value={2}>2</option>
                    <option value={3}>3+</option>
                  </select>
                </div>

                <div className="field-group">
                  <label>
                    Assignment Completion Rate (%)
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    step={1}
                    value={manualForm.assignment_rate}
                    onChange={(e) => handleManualChange("assignment_rate", e.target.value)}
                  />
                </div>

                <div className="field-group">
                  <label>
                    Recent Assessment Trend
                  </label>
                  <select
                    value={manualForm.assessment_trend}
                    onChange={(e) => handleManualChange("assessment_trend", e.target.value)}
                  >
                    <option value={1}>Improving (+1)</option>
                    <option value={0}>Stable / Neutral (0)</option>
                    <option value={-1}>Declining (-1)</option>
                  </select>
                </div>
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-lg"
                disabled={manualMutation.isPending}
              >
                <BrainCircuit size={18} />
                {manualMutation.isPending ? "Predicting…" : "Run Prediction"}
              </button>
            </form>
          </div>

          {/* Result Panel */}
          {manualResult && manualCfg && (
            <div className="predict-results" ref={resultsRef}>
              <div
                className="card result-card"
                style={{ background: manualCfg.bg, borderColor: manualCfg.color }}
              >
                <div className="result-icon" style={{ color: manualCfg.color }}>
                  {manualCfg.icon}
                </div>
                <div className="result-category" style={{ color: manualCfg.color }}>
                  {manualResult.category}
                </div>
                <div className="result-confidence">
                  Confidence: <strong>{(manualResult.confidence * 100).toFixed(1)}%</strong>
                </div>
                <div className="confidence-bar-wrap">
                  <div
                    className="confidence-bar"
                    style={{
                      width: `${manualResult.confidence * 100}%`,
                      background: manualCfg.color,
                    }}
                  />
                </div>
                <div className="result-meta">
                  Model: {manualResult.model_name} · Feature set: {manualResult.feature_set}
                </div>
              </div>

              <div className="predict-results-grid">
                {manualResult.top_factors && manualResult.top_factors.length > 0 && (
                  <div className="card" style={{ marginBottom: 0 }}>
                    <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Sparkles size={16} color="var(--primary)" />
                      Key Contributing Factors
                    </h3>
                    <div className="factors-list" style={{ marginTop: 14 }}>
                      {manualResult.top_factors.map((f: any, idx: number) => {
                        const featName = typeof f === "string" ? f : (f?.feature ?? `Factor ${idx + 1}`);
                        const featImp = typeof f === "object" && typeof f?.importance === "number" ? f.importance : null;
                        return (
                          <div key={idx} className="factor-row">
                            <span className="factor-name" style={{ flex: 1 }}>{featName}</span>
                            {featImp !== null && (
                              <>
                                <div className="factor-bar-wrap">
                                  <div
                                    className="factor-bar"
                                    style={{ width: `${Math.min(100, Math.abs(featImp) * 100)}%` }}
                                  />
                                </div>
                                <span className="factor-val">{featImp.toFixed(3)}</span>
                              </>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                <div className="card" style={{ marginBottom: 0 }}>
                  <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <Lightbulb size={16} color="var(--primary)" />
                    Targeted Interventions & Recommendations
                  </h3>
                  {recQuery.isLoading ? (
                    <div className="skeleton-card" style={{ height: 160 }} />
                  ) : recQuery.data && recQuery.data.recommendations && recQuery.data.recommendations.length > 0 ? (
                    <div className="recs-list" style={{ marginTop: 14 }}>
                      {recQuery.data.recommendations.map((r: any, i: number) => {
                        const priority = (r.priority || "medium").toLowerCase();
                        const area = r.area || r.category || "ACADEMIC INTERVENTION";
                        const title = r.title || r.tip || "Recommended Action";
                        const description = r.description || r.tip;
                        const action = r.action;

                        return (
                          <div
                            key={i}
                            className={`rec-item priority-${priority}`}
                            style={{
                              padding: "14px 16px",
                              borderRadius: 10,
                              background: priority === "high" ? "#fff5f5" : priority === "medium" ? "#fffbeb" : "#f0fdf4",
                              border: `1px solid ${priority === "high" ? "#fecaca" : priority === "medium" ? "#fde68a" : "#bbf7d0"}`,
                              marginBottom: 10,
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                              <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5, color: "var(--text-muted)" }}>
                                {area}
                              </span>
                              <span className="rec-badge" style={{ position: "static", textTransform: "uppercase", fontSize: 10, fontWeight: 700 }}>
                                {r.priority || "MEDIUM"}
                              </span>
                            </div>

                            <div style={{ fontWeight: 700, fontSize: 14, color: "var(--text)", marginBottom: 4 }}>
                              {title}
                            </div>

                            {description && (
                              <div style={{ fontSize: 13, color: "var(--text-muted)", lineHeight: 1.45, marginBottom: 8 }}>
                                {description}
                              </div>
                            )}

                            {action && (
                              <div style={{ fontSize: 12.5, color: "var(--primary)", fontWeight: 600, background: "rgba(99, 102, 241, 0.08)", padding: "7px 12px", borderRadius: 6, display: "flex", alignItems: "center", gap: 6 }}>
                                <span>👉</span>
                                <span><strong>Action:</strong> {action}</span>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="empty">No specific intervention required. Student is tracking well.</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* =======================================================================
          OPTION B: BULK STUDENT UPLOAD & BATCH PREDICTION
      ======================================================================= */}
      {mode === "bulk" && (
        <div>
          {/* Stepper Header */}
          <div className="bulk-stepper">
            <div className={`step-item ${bulkStep === 1 ? "active" : bulkStep > 1 ? "completed" : ""}`}>
              <div className="step-circle">{bulkStep > 1 ? <Check size={16} /> : "1"}</div>
              <span className="step-title">Upload & Model</span>
            </div>
            <div className={`step-divider ${bulkStep > 1 ? "filled" : ""}`} />
            <div className={`step-item ${bulkStep === 2 ? "active" : bulkStep > 2 ? "completed" : ""}`}>
              <div className="step-circle">{bulkStep > 2 ? <Check size={16} /> : "2"}</div>
              <span className="step-title">Validate & Preview</span>
            </div>
            <div className={`step-divider ${bulkStep > 2 ? "filled" : ""}`} />
            <div className={`step-item ${bulkStep === 3 ? "active" : ""}`}>
              <div className="step-circle">3</div>
              <span className="step-title">Batch Results</span>
            </div>
          </div>

          {/* STEP 1: Upload and Configuration */}
          {bulkStep === 1 && (
            <div style={{ maxWidth: 840, margin: "0 auto" }}>
              {/* Template Download Bar */}
              <div className="template-bar">
                <div className="template-info">
                  <FileText size={18} color="var(--primary)" />
                  <span>
                    Need the formatted schema? Download a ready-to-fill sample template for the selected model:
                  </span>
                </div>
                <div className="template-actions">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => handleDownloadTemplate("csv")}
                  >
                    <Download size={14} /> CSV Template
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => handleDownloadTemplate("xlsx")}
                  >
                    <Download size={14} /> Excel Template (.xlsx)
                  </button>
                </div>
              </div>

              {/* Model Selection Card */}
              <div className="card" style={{ marginBottom: 20 }}>
                <div className="field-group">
                  <label style={{ fontSize: 15, fontWeight: 700, marginBottom: 8 }}>
                    1. Select Target Prediction Model
                  </label>
                  <div className="toggle-group" style={{ marginBottom: 10 }}>
                    <button
                      type="button"
                      className={`toggle-btn${bulkFeatureSet === "early" ? " active" : ""}`}
                      onClick={() => setBulkFeatureSet("early")}
                    >
                      Early Prediction (G1 only)
                    </button>
                    <button
                      type="button"
                      className={`toggle-btn${bulkFeatureSet === "mid" ? " active" : ""}`}
                      onClick={() => setBulkFeatureSet("mid")}
                    >
                      Mid-term Prediction (G1 + G2)
                    </button>
                  </div>
                  <div style={{ fontSize: 13, color: "var(--text-muted)", lineHeight: 1.5 }}>
                    {bulkFeatureSet === "early" ? (
                      <div>
                        <strong>Required Columns:</strong> <code>student_id</code> (optional), <code>G1</code> (0–20), <code>absences</code>, <code>studytime</code> (1–4), <code>failures</code> (0–4).
                      </div>
                    ) : (
                      <div>
                        <strong>Required Columns:</strong> <code>student_id</code> (optional), <code>G1</code> (0–20), <code>G2</code> (0–20), <code>absences</code>, <code>studytime</code> (1–4), <code>failures</code> (0–4).
                        <div style={{ color: "var(--warn)", marginTop: 4, fontWeight: 500 }}>
                          * Notice: The Mid-term model strictly requires the second period grade (G2).
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* File Dropzone Card */}
              <div className="card" style={{ marginBottom: 20 }}>
                <label style={{ fontSize: 15, fontWeight: 700, marginBottom: 12, display: "block" }}>
                  2. Upload Student Dataset
                </label>

                <div
                  className={`dropzone-container ${isDragging ? "drag-over" : ""}`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragging(true);
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleFileDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv,.xlsx,.xls"
                    style={{ display: "none" }}
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        handleFileSelected(e.target.files[0]);
                      }
                    }}
                  />

                  <div className="dropzone-icon-wrap">
                    <UploadCloud size={32} />
                  </div>
                  <div className="dropzone-title">
                    Drag and drop your student dataset here, or browse files
                  </div>
                  <div className="dropzone-subtitle">
                    Supported formats: CSV (<code>.csv</code>) or Excel (<code>.xlsx</code>, <code>.xls</code>)
                  </div>
                  <div className="dropzone-meta">
                    <span>Max file size: 10 MB</span>
                    <span>•</span>
                    <span>Max batch size: 5,000 rows</span>
                  </div>

                  {selectedFile && (
                    <div className="selected-file-chip" onClick={(e) => e.stopPropagation()}>
                      <FileCheck size={18} />
                      <span>{selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)</span>
                      <button
                        type="button"
                        onClick={() => setSelectedFile(null)}
                        style={{
                          background: "none",
                          border: "none",
                          cursor: "pointer",
                          color: "var(--text-muted)",
                          padding: 4,
                          display: "flex",
                          alignItems: "center",
                        }}
                        title="Remove file"
                      >
                        <X size={16} />
                      </button>
                    </div>
                  )}
                </div>

                <div style={{ marginTop: 20, display: "flex", justifyContent: "flex-end" }}>
                  <button
                    type="button"
                    className="btn btn-primary btn-lg"
                    disabled={!selectedFile || validateMutation.isPending}
                    onClick={() => validateMutation.mutate()}
                  >
                    <FileCheck size={18} />
                    {validateMutation.isPending ? "Parsing & Validating..." : "Analyze & Validate File"}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: Validation & Data Preview */}
          {bulkStep === 2 && validationReport && (
            <div>
              {/* Summary Metric Chips */}
              <div className="validation-stats">
                <div className="stat-pill">
                  <span className="label">Total Records</span>
                  <span className="value">{previewRows.length}</span>
                </div>
                <div className="stat-pill success">
                  <span className="label">Valid Records</span>
                  <span className="value">{validPreviewCount}</span>
                </div>
                <div className={`stat-pill ${invalidPreviewCount > 0 ? "danger" : ""}`}>
                  <span className="label">Invalid / Issues</span>
                  <span className="value">{invalidPreviewCount}</span>
                </div>
                <div className={`stat-pill ${validationReport.duplicate_student_ids.length > 0 ? "warn" : ""}`}>
                  <span className="label">Duplicate IDs</span>
                  <span className="value">{validationReport.duplicate_student_ids.length}</span>
                </div>
              </div>

              {/* Missing Required Columns or Special Notes */}
              {validationReport.unmapped_required.length > 0 && (
                <div className="alert-box alert-danger">
                  <ShieldAlert size={20} />
                  <div>
                    <strong>Required Columns Missing:</strong>{" "}
                    The uploaded dataset is missing the following column(s) expected by the <strong>{bulkFeatureSet.toUpperCase()}</strong> model:{" "}
                    <code>{validationReport.unmapped_required.join(", ")}</code>.
                    {bulkFeatureSet === "mid" && validationReport.unmapped_required.includes("G2") && (
                      <div style={{ marginTop: 6 }}>
                        <em>The Mid-term model requires second-period grade <code>G2</code>. If you only have first-period grades, switch to the Early prediction model.</em>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {validationReport.special_notes.length > 0 && (
                <div className="alert-box alert-warn">
                  <AlertCircle size={20} />
                  <div>
                    {validationReport.special_notes.map((note, idx) => (
                      <div key={idx}>{note}</div>
                    ))}
                  </div>
                </div>
              )}

              {/* Table Toolbar */}
              <div className="card" style={{ padding: "16px 20px", marginBottom: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button
                      type="button"
                      className={`btn-secondary${previewFilter === "all" ? " active" : ""}`}
                      style={{ background: previewFilter === "all" ? "var(--primary-light)" : undefined }}
                      onClick={() => setPreviewFilter("all")}
                    >
                      All Rows ({previewRows.length})
                    </button>
                    <button
                      type="button"
                      className={`btn-secondary${previewFilter === "valid" ? " active" : ""}`}
                      style={{ background: previewFilter === "valid" ? "var(--primary-light)" : undefined }}
                      onClick={() => setPreviewFilter("valid")}
                    >
                      Valid Only ({validPreviewCount})
                    </button>
                    <button
                      type="button"
                      className={`btn-secondary${previewFilter === "invalid" ? " active" : ""}`}
                      style={{ background: previewFilter === "invalid" ? "var(--primary-light)" : undefined }}
                      onClick={() => setPreviewFilter("invalid")}
                    >
                      Invalid Only ({invalidPreviewCount})
                    </button>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <Search size={16} color="var(--text-muted)" />
                    <input
                      type="text"
                      placeholder="Search Student ID..."
                      value={previewSearch}
                      onChange={(e) => setPreviewSearch(e.target.value)}
                      style={{ padding: "6px 12px", fontSize: 13, borderRadius: 8, width: 200 }}
                    />
                  </div>
                </div>
              </div>

              {/* Preview Table */}
              <div className="data-table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th style={{ width: 50 }}>#</th>
                      <th>Student ID</th>
                      <th>G1 (0-20)</th>
                      {bulkFeatureSet === "mid" && <th>G2 (0-20)</th>}
                      <th>Absences</th>
                      <th>Study Time</th>
                      <th>Failures</th>
                      <th>Status</th>
                      <th>Validation Issues</th>
                      <th style={{ width: 80, textAlign: "center" }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredPreviewRows.length === 0 ? (
                      <tr>
                        <td colSpan={bulkFeatureSet === "mid" ? 10 : 9} style={{ textAlign: "center", padding: 32, color: "var(--text-muted)" }}>
                          No records match the current filter.
                        </td>
                      </tr>
                    ) : (
                      filteredPreviewRows.map((row) => (
                        <tr key={row.row_index} className={!row.is_valid ? "row-invalid" : ""}>
                          <td>{row.row_index + 1}</td>
                          <td>
                            <strong>{row.student_id || `Row #${row.row_index + 1}`}</strong>
                          </td>
                          <td>{row.cleaned_data?.G1 ?? row.raw_data?.G1 ?? "-"}</td>
                          {bulkFeatureSet === "mid" && (
                            <td>{row.cleaned_data?.G2 ?? row.raw_data?.G2 ?? "-"}</td>
                          )}
                          <td>{row.cleaned_data?.absences ?? row.raw_data?.absences ?? "-"}</td>
                          <td>{row.cleaned_data?.studytime ?? row.raw_data?.studytime ?? "-"}</td>
                          <td>{row.cleaned_data?.failures ?? row.raw_data?.failures ?? "-"}</td>
                          <td>
                            {row.is_valid ? (
                              <span className="badge-valid">
                                <Check size={12} /> Valid
                              </span>
                            ) : (
                              <span className="badge-invalid">
                                <AlertTriangle size={12} /> Invalid
                              </span>
                            )}
                          </td>
                          <td>
                            {row.errors && row.errors.length > 0 ? (
                              row.errors.map((err, ei) => (
                                <span key={ei} className="error-tag">
                                  {err}
                                </span>
                              ))
                            ) : (
                              <span style={{ color: "var(--text-muted)", fontSize: 12 }}>Ready for model</span>
                            )}
                          </td>
                          <td style={{ textAlign: "center" }}>
                            <button
                              type="button"
                              onClick={() => handleRemovePreviewRow(row.row_index)}
                              style={{
                                background: "none",
                                border: "none",
                                cursor: "pointer",
                                color: "var(--danger)",
                                padding: 6,
                                borderRadius: 6,
                              }}
                              title="Remove row from batch"
                            >
                              <Trash2 size={16} />
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Action Footer */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 24 }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setBulkStep(1)}
                >
                  <ArrowLeft size={16} /> Back to Upload
                </button>

                <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                  {invalidPreviewCount > 0 && (
                    <span style={{ fontSize: 13, color: "var(--warn)" }}>
                      * {invalidPreviewCount} invalid record(s) will be excluded.
                    </span>
                  )}

                  <button
                    type="button"
                    className="btn btn-primary btn-lg"
                    disabled={validPreviewCount === 0 || batchProcessMutation.isPending}
                    onClick={() => batchProcessMutation.mutate()}
                  >
                    <BrainCircuit size={18} />
                    {batchProcessMutation.isPending
                      ? "Running Batch Predictions..."
                      : `Confirm & Run Predictions (${validPreviewCount} Students)`}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: Batch Results Dashboard */}
          {bulkStep === 3 && batchResponse && (
            <div>
              {/* Header Action Bar */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
                <div>
                  <h3 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>
                    Batch Prediction Insights
                  </h3>
                  <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "4px 0 0" }}>
                    Trained model: <strong>{bulkFeatureSet.toUpperCase()} Feature Set</strong> · Job ID: <code>{batchResponse.job_id.slice(0, 8)}</code>
                  </p>
                </div>

                <div style={{ display: "flex", gap: 10 }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleResetBulk}
                  >
                    <UploadCloud size={16} /> Upload Another File
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => handleExportResults("csv")}
                  >
                    <Download size={16} /> Export CSV
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => handleExportResults("xlsx")}
                  >
                    <FileSpreadsheet size={16} /> Export Excel (.xlsx)
                  </button>
                </div>
              </div>

              {/* Metric Summary Cards */}
              <div className="validation-stats" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))" }}>
                <div className="stat-pill">
                  <span className="label">Total Processed</span>
                  <span className="value">{batchResponse.processed_rows}</span>
                </div>
                <div className="stat-pill">
                  <span className="label">Avg Confidence</span>
                  <span className="value">{(batchResponse.avg_confidence * 100).toFixed(1)}%</span>
                </div>
                <div className="stat-pill danger">
                  <span className="label">At-Risk Students</span>
                  <span className="value">
                    {batchResponse.category_distribution["At-Risk"] || 0}
                    <small style={{ fontSize: 13, fontWeight: 500, marginLeft: 6 }}>
                      ({batchResponse.category_percentages["At-Risk"] || 0}%)
                    </small>
                  </span>
                </div>
                <div className="stat-pill warn">
                  <span className="label">Needs Improvement</span>
                  <span className="value">
                    {batchResponse.category_distribution["Needs Improvement"] || 0}
                    <small style={{ fontSize: 13, fontWeight: 500, marginLeft: 6 }}>
                      ({batchResponse.category_percentages["Needs Improvement"] || 0}%)
                    </small>
                  </span>
                </div>
                <div className="stat-pill success">
                  <span className="label">Performing Well</span>
                  <span className="value">
                    {batchResponse.category_distribution["Performing Well"] || 0}
                    <small style={{ fontSize: 13, fontWeight: 500, marginLeft: 6 }}>
                      ({batchResponse.category_percentages["Performing Well"] || 0}%)
                    </small>
                  </span>
                </div>
              </div>

              {/* Stacked Risk Distribution Bar */}
              <div className="card" style={{ padding: "16px 20px", marginBottom: 20 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, fontWeight: 600 }}>
                  <span style={{ color: "var(--danger)" }}>
                    At-Risk: {batchResponse.category_distribution["At-Risk"] || 0} ({batchResponse.category_percentages["At-Risk"] || 0}%)
                  </span>
                  <span style={{ color: "var(--warn)" }}>
                    Needs Improvement: {batchResponse.category_distribution["Needs Improvement"] || 0} ({batchResponse.category_percentages["Needs Improvement"] || 0}%)
                  </span>
                  <span style={{ color: "var(--success)" }}>
                    Performing Well: {batchResponse.category_distribution["Performing Well"] || 0} ({batchResponse.category_percentages["Performing Well"] || 0}%)
                  </span>
                </div>

                <div className="distribution-stacked-bar">
                  <div
                    className="dist-segment at-risk"
                    style={{ width: `${batchResponse.category_percentages["At-Risk"] || 0}%` }}
                    title={`At-Risk: ${batchResponse.category_percentages["At-Risk"] || 0}%`}
                  />
                  <div
                    className="dist-segment needs-improvement"
                    style={{ width: `${batchResponse.category_percentages["Needs Improvement"] || 0}%` }}
                    title={`Needs Improvement: ${batchResponse.category_percentages["Needs Improvement"] || 0}%`}
                  />
                  <div
                    className="dist-segment performing-well"
                    style={{ width: `${batchResponse.category_percentages["Performing Well"] || 0}%` }}
                    title={`Performing Well: ${batchResponse.category_percentages["Performing Well"] || 0}%`}
                  />
                </div>
              </div>

              {/* Search, Filter & Sort Toolbar */}
              <div className="card" style={{ padding: "16px 20px", marginBottom: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
                  <div style={{ display: "flex", gap: 8 }}>
                    {["all", "At-Risk", "Needs Improvement", "Performing Well"].map((cat) => (
                      <button
                        key={cat}
                        type="button"
                        className={`btn-secondary${resultCategoryFilter === cat ? " active" : ""}`}
                        style={{
                          background: resultCategoryFilter === cat ? "var(--primary-light)" : undefined,
                          borderColor: resultCategoryFilter === cat ? "var(--primary)" : undefined,
                        }}
                        onClick={() => setResultCategoryFilter(cat)}
                      >
                        {cat === "all" ? "All Outcomes" : cat}
                      </button>
                    ))}
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <Search size={16} color="var(--text-muted)" />
                      <input
                        type="text"
                        placeholder="Search student ID..."
                        value={resultSearch}
                        onChange={(e) => setResultSearch(e.target.value)}
                        style={{ padding: "6px 12px", fontSize: 13, borderRadius: 8, width: 180 }}
                      />
                    </div>

                    <select
                      value={resultSort}
                      onChange={(e) => setResultSort(e.target.value as any)}
                      style={{ padding: "6px 10px", fontSize: 13, borderRadius: 8, width: "auto" }}
                    >
                      <option value="id">Sort by Student ID</option>
                      <option value="conf_desc">Confidence: High to Low</option>
                      <option value="conf_asc">Confidence: Low to High</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Batch Results Table */}
              <div className="data-table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Student ID</th>
                      <th>Predicted Outcome</th>
                      <th>Confidence</th>
                      <th>Key Factors</th>
                      <th>Primary Recommendation</th>
                      <th style={{ width: 100, textAlign: "center" }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredBatchResults.length === 0 ? (
                      <tr>
                        <td colSpan={6} style={{ textAlign: "center", padding: 32, color: "var(--text-muted)" }}>
                          No students found matching your criteria.
                        </td>
                      </tr>
                    ) : (
                      filteredBatchResults.map((item) => {
                        const cfg = CATEGORY_CONFIG[item.category] || CATEGORY_CONFIG["Performing Well"];
                        return (
                          <tr key={item.student_id}>
                            <td>
                              <strong>{item.student_id}</strong>
                            </td>
                            <td>
                              <span
                                style={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: 6,
                                  fontWeight: 600,
                                  color: cfg.color,
                                  background: cfg.bg,
                                  padding: "3px 10px",
                                  borderRadius: 99,
                                  fontSize: 12,
                                }}
                              >
                                {item.category}
                              </span>
                            </td>
                            <td>
                              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                <div style={{ width: 50, height: 6, background: "var(--border)", borderRadius: 99, overflow: "hidden" }}>
                                  <div style={{ height: "100%", width: `${item.confidence * 100}%`, background: cfg.color }} />
                                </div>
                                <span style={{ fontSize: 12, fontWeight: 600 }}>
                                  {(item.confidence * 100).toFixed(0)}%
                                </span>
                              </div>
                            </td>
                            <td>
                              <div className="factor-tags">
                                {item.top_factors && item.top_factors.length > 0 ? (
                                  item.top_factors.map((f, fi) => (
                                    <span key={fi} className="factor-tag">
                                      {f}
                                    </span>
                                  ))
                                ) : (
                                  <span style={{ color: "var(--text-muted)", fontSize: 12 }}>—</span>
                                )}
                              </div>
                            </td>
                            <td style={{ maxWidth: 260 }}>
                              {item.recommendations && item.recommendations.length > 0 ? (
                                <div style={{ fontSize: 12, color: "var(--text)" }}>
                                  <strong>{item.recommendations[0].title}:</strong> {item.recommendations[0].action}
                                </div>
                              ) : (
                                <span style={{ color: "var(--text-muted)", fontSize: 12 }}>Standard guidance</span>
                              )}
                            </td>
                            <td style={{ textAlign: "center" }}>
                              <button
                                type="button"
                                className="btn-secondary"
                                style={{ padding: "4px 10px", fontSize: 12 }}
                                onClick={() => setSelectedStudentDetail(item)}
                              >
                                <Eye size={13} /> View
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

              {/* Student Detail Modal */}
              {selectedStudentDetail && (
                <div className="modal-overlay" onClick={() => setSelectedStudentDetail(null)}>
                  <div className="details-modal" onClick={(e) => e.stopPropagation()}>
                    <div className="modal-header">
                      <div>
                        <h3 style={{ fontSize: 17, fontWeight: 700, margin: 0 }}>
                          Student Profile: {selectedStudentDetail.student_id}
                        </h3>
                        <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                          Model: {selectedStudentDetail.model_name} ({selectedStudentDetail.feature_set})
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setSelectedStudentDetail(null)}
                        style={{ background: "none", border: "none", cursor: "pointer", padding: 6 }}
                      >
                        <X size={20} />
                      </button>
                    </div>

                    <div className="modal-body">
                      {/* Prediction Outcome Banner */}
                      {(() => {
                        const cfg = CATEGORY_CONFIG[selectedStudentDetail.category] || CATEGORY_CONFIG["Performing Well"];
                        return (
                          <div
                            style={{
                              background: cfg.bg,
                              border: `1px solid ${cfg.color}`,
                              borderRadius: 12,
                              padding: 16,
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                            }}
                          >
                            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                              <div style={{ color: cfg.color }}>{cfg.icon}</div>
                              <div>
                                <div style={{ fontSize: 12, textTransform: "uppercase", fontWeight: 700, color: cfg.color }}>
                                  Predicted Trajectory
                                </div>
                                <div style={{ fontSize: 20, fontWeight: 800, color: cfg.color }}>
                                  {selectedStudentDetail.category}
                                </div>
                              </div>
                            </div>
                            <div style={{ textAlign: "right" }}>
                              <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>Model Confidence</div>
                              <div style={{ fontSize: 22, fontWeight: 800, color: cfg.color }}>
                                {(selectedStudentDetail.confidence * 100).toFixed(1)}%
                              </div>
                            </div>
                          </div>
                        );
                      })()}

                      {/* Inputs Grid */}
                      <div>
                        <h4 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>Input Attributes</h4>
                        <div className="inputs-grid">
                          <div className="input-metric">
                            <div className="k">G1 Grade</div>
                            <div className="v">{selectedStudentDetail.inputs.G1 ?? "-"} / 20</div>
                          </div>
                          {selectedStudentDetail.inputs.G2 !== undefined && (
                            <div className="input-metric">
                              <div className="k">G2 Grade</div>
                              <div className="v">{selectedStudentDetail.inputs.G2} / 20</div>
                            </div>
                          )}
                          <div className="input-metric">
                            <div className="k">Absences</div>
                            <div className="v">{selectedStudentDetail.inputs.absences ?? "-"}</div>
                          </div>
                          <div className="input-metric">
                            <div className="k">Study Time</div>
                            <div className="v">{selectedStudentDetail.inputs.studytime ?? "-"}</div>
                          </div>
                          <div className="input-metric">
                            <div className="k">Failures</div>
                            <div className="v">{selectedStudentDetail.inputs.failures ?? "-"}</div>
                          </div>
                          {selectedStudentDetail.inputs.assignment_rate !== undefined && (
                            <div className="input-metric">
                              <div className="k">Assignment Rate</div>
                              <div className="v">{selectedStudentDetail.inputs.assignment_rate}%</div>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Key Factors */}
                      {selectedStudentDetail.top_factors && selectedStudentDetail.top_factors.length > 0 && (
                        <div>
                          <h4 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>Top Contributing Factors</h4>
                          <div className="factor-tags">
                            {selectedStudentDetail.top_factors.map((f, i) => (
                              <span key={i} className="factor-tag" style={{ fontSize: 12, padding: "4px 10px" }}>
                                {f}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Recommendations */}
                      {selectedStudentDetail.recommendations && selectedStudentDetail.recommendations.length > 0 && (
                        <div>
                          <h4 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>
                            <Lightbulb size={16} style={{ verticalAlign: "middle", marginRight: 4 }} />
                            Actionable Interventions
                          </h4>
                          <div className="recs-list">
                            {selectedStudentDetail.recommendations.map((rec, i) => (
                              <div key={i} className={`rec-item priority-${(rec.priority || "medium").toLowerCase()}`}>
                                <div className="rec-area">{rec.category || "ACADEMIC INTERVENTION"}</div>
                                <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 2 }}>{rec.title}</div>
                                <div className="rec-tip">{rec.description}</div>
                                {rec.action && (
                                  <div style={{ marginTop: 6, fontSize: 12, color: "var(--primary)", fontWeight: 600 }}>
                                    → Action: {rec.action}
                                  </div>
                                )}
                                <span className="rec-badge">{rec.priority}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="modal-footer">
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => setSelectedStudentDetail(null)}
                      >
                        Close
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PredictPage;
