import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Sliders,
  Sparkles,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Info,
  CheckCircle2,
  Layers,
  UserCheck,
} from "lucide-react";
import {
  simulateWhatIf,
  getHistory,
  type WhatIfResponse,
  type PredictionHistoryItem,
} from "../api/services";
import toast from "react-hot-toast";

const SimulatorPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const urlPredId = searchParams.get("prediction_id") || searchParams.get("id") || "";

  // History query to allow selecting any evaluated student as baseline
  const historyQuery = useQuery({
    queryKey: ["simulator-history-students"],
    queryFn: () => getHistory({ limit: 100 }),
  });

  const [selectedPredictionId, setSelectedPredictionId] = useState<string>(urlPredId);
  const [featureSet, setFeatureSet] = useState<"early" | "mid">("early");

  // Interactive slider states
  const [absences, setAbsences] = useState<number>(14);
  const [studytime, setStudytime] = useState<number>(1);
  const [failures, setFailures] = useState<number>(2);
  const [g1, setG1] = useState<number>(7);
  const [g2, setG2] = useState<number>(8);
  const [assignmentRate, setAssignmentRate] = useState<number>(55);
  const [assessmentTrend, setAssessmentTrend] = useState<number>(-1);

  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<WhatIfResponse | null>(null);

  // Selected student object from history
  const selectedStudent: PredictionHistoryItem | undefined = historyQuery.data?.find(
    (p) => p.id === selectedPredictionId
  );

  // Default hypothetical fallback baseline
  const defaultBaseline = {
    absences: 14,
    studytime: 1,
    failures: 2,
    G1: 7,
    ...(featureSet === "mid" ? { G2: 8 } : {}),
    assignment_rate: 55,
    assessment_trend: -1,
  };

  // Compute active baseline inputs
  const activeBaselineInputs = selectedStudent
    ? {
        absences: Number(selectedStudent.input_features?.absences ?? 14),
        studytime: Number(selectedStudent.input_features?.studytime ?? 1),
        failures: Number(selectedStudent.input_features?.failures ?? 2),
        G1: Number(selectedStudent.input_features?.G1 ?? 7),
        ...(selectedStudent.feature_set === "mid"
          ? { G2: Number(selectedStudent.input_features?.G2 ?? 8) }
          : {}),
        assignment_rate: Number(selectedStudent.input_features?.assignment_rate ?? 75),
        assessment_trend: Number(selectedStudent.input_features?.assessment_trend ?? 0),
      }
    : defaultBaseline;

  // Sync sliders when a student is selected
  const handleStudentSelect = (predId: string) => {
    setSelectedPredictionId(predId);
    if (!predId) {
      // Revert to default hypothetical baseline
      setAbsences(14);
      setStudytime(1);
      setFailures(2);
      setG1(7);
      setG2(8);
      setAssignmentRate(55);
      setAssessmentTrend(-1);
      toast("Switched to Default Hypothetical Baseline", { icon: "📊" });
      return;
    }

    const st = historyQuery.data?.find((p) => p.id === predId);
    if (st) {
      const inputs = st.input_features || {};
      const fSet = (st.feature_set as "early" | "mid") || "early";
      setFeatureSet(fSet);
      setAbsences(Number(inputs.absences ?? 0));
      setStudytime(Number(inputs.studytime ?? 2));
      setFailures(Number(inputs.failures ?? 0));
      setG1(Number(inputs.G1 ?? 10));
      if (inputs.G2 !== undefined) {
        setG2(Number(inputs.G2));
      }
      setAssignmentRate(Number(inputs.assignment_rate ?? 75));
      setAssessmentTrend(Number(inputs.assessment_trend ?? 0));
      toast.success(`Loaded ${st.student_code || st.student_id || "Student"}'s baseline stats`);
    }
  };

  // If URL contains prediction_id, select it once history is loaded
  useEffect(() => {
    if (urlPredId && historyQuery.data && !selectedPredictionId) {
      handleStudentSelect(urlPredId);
    }
  }, [urlPredId, historyQuery.data]);

  const runSimulation = async () => {
    setLoading(true);
    try {
      const overrides: Record<string, any> = {
        absences,
        studytime,
        failures,
        G1: g1,
        assignment_rate: assignmentRate,
        assessment_trend: assessmentTrend,
      };
      if (featureSet === "mid") {
        overrides.G2 = g2;
      }

      const res = await simulateWhatIf({
        base_prediction_id: selectedPredictionId || undefined,
        feature_set: featureSet,
        student_inputs: selectedPredictionId ? undefined : activeBaselineInputs,
        overrides,
      });
      setResult(res);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Simulation failed to compute.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runSimulation();
  }, [featureSet, selectedPredictionId]);

  const resetToBaseline = () => {
    setAbsences(activeBaselineInputs.absences);
    setStudytime(activeBaselineInputs.studytime);
    setFailures(activeBaselineInputs.failures);
    setG1(activeBaselineInputs.G1);
    if (featureSet === "mid") {
      setG2((activeBaselineInputs as any).G2 ?? 10);
    }
    setAssignmentRate(activeBaselineInputs.assignment_rate);
    setAssessmentTrend(activeBaselineInputs.assessment_trend);
    toast(
      selectedStudent
        ? `Reset sliders to ${selectedStudent.student_code || "student"}'s baseline`
        : "Reset parameters to default baseline",
      { icon: "🔄" }
    );
  };

  const getCategoryColor = (cat: string) => {
    if (cat === "At-Risk") return "badge-at-risk";
    if (cat === "Needs Improvement") return "badge-needs-improvement";
    return "badge-performing-well";
  };

  const riskDir = result?.risk_change || result?.risk_direction || "unchanged";

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Sliders className="text-primary-400" size={28} />
            What-If Academic Simulator
          </h1>
          <p className="page-subtitle">
            Load any student's actual baseline or test hypothetical interventions to compare against live ML model predictions.
          </p>
        </div>

        {/* Model Toggle */}
        <div className="model-selector-pill">
          <button
            type="button"
            className={`pill-btn ${featureSet === "early" ? "active" : ""}`}
            onClick={() => setFeatureSet("early")}
          >
            Early Model (G1)
          </button>
          <button
            type="button"
            className={`pill-btn ${featureSet === "mid" ? "active" : ""}`}
            onClick={() => setFeatureSet("mid")}
          >
            Mid-Term Model (G1+G2)
          </button>
        </div>
      </div>

      {/* Student Baseline Selector Bar */}
      <div className="card mb-4" style={{ padding: "14px 20px" }}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <UserCheck size={18} className="text-primary-400" />
            <span className="text-sm font-semibold text-neutral-200">Baseline Student Selection:</span>
          </div>

          <div className="flex-1 max-w-md">
            <select
              value={selectedPredictionId}
              onChange={(e) => handleStudentSelect(e.target.value)}
              className="form-input text-xs w-full"
            >
              <option value="">Default Hypothetical Student (Sandbox Mode)</option>
              {(historyQuery.data ?? []).map((item) => (
                <option key={item.id} value={item.id}>
                  {item.student_code || item.student_id || "Student"} — {item.category} ({((item.confidence || 0) * 100).toFixed(1)}%) [{item.feature_set.toUpperCase()} • {new Date(item.predicted_at).toLocaleDateString()}]
                </option>
              ))}
            </select>
          </div>

          {selectedStudent ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-primary-300 font-medium bg-primary-950/70 border border-primary-800/60 px-3 py-1 rounded-md">
                Active Baseline: <strong>{selectedStudent.student_code || selectedStudent.student_id}</strong> ({selectedStudent.category})
              </span>
              <button
                type="button"
                onClick={() => handleStudentSelect("")}
                className="btn btn-secondary btn-sm text-xs"
                title="Switch back to generic sandbox"
              >
                Clear
              </button>
            </div>
          ) : (
            <span className="text-xs text-neutral-400 italic">
              Showing generic starting baseline. Choose an analyzed student to test their specific profile.
            </span>
          )}
        </div>
      </div>

      {/* Notice Banner */}
      <div className="simulator-disclaimer-banner">
        <Info size={18} className="text-primary-400 flex-shrink-0" />
        <div className="text-xs text-neutral-300 leading-relaxed">
          <strong>WHAT-IF COMPARISON:</strong> The left panel adjusts candidate parameters (absences, study hours, grades). The right panel projects how the live model's classification shifts relative to the <strong>Original Baseline</strong>.
        </div>
      </div>

      <div className="simulator-grid">
        {/* Left: Interactive Controls */}
        <div className="card simulator-controls-card">
          <div className="card-header flex items-center justify-between">
            <div className="card-title flex items-center gap-2">
              <Layers size={18} className="text-accent-400" />
              Adjust What-If Parameters
            </div>
            <button
              type="button"
              onClick={resetToBaseline}
              className="btn btn-secondary btn-sm flex items-center gap-1"
              title="Reset sliders to baseline values"
            >
              <RefreshCw size={14} />
              Reset
            </button>
          </div>

          <div className="simulator-sliders-list">
            {/* Absences */}
            <div className="slider-group">
              <div className="slider-label-row">
                <span className="slider-name">School Absences</span>
                <span className="slider-value badge-neutral">{absences} days</span>
              </div>
              <input
                type="range"
                min={0}
                max={50}
                value={absences}
                onChange={(e) => setAbsences(Number(e.target.value))}
                className="custom-range-slider"
              />
              <div className="slider-hints">
                <span>0 days (Perfect)</span>
                <span>25 days</span>
                <span>50 days (Debarment)</span>
              </div>
            </div>

            {/* Study Time */}
            <div className="slider-group">
              <div className="slider-label-row">
                <span className="slider-name">Weekly Study Time</span>
                <span className="slider-value badge-neutral">Level {studytime} / 4</span>
              </div>
              <input
                type="range"
                min={1}
                max={4}
                step={1}
                value={studytime}
                onChange={(e) => setStudytime(Number(e.target.value))}
                className="custom-range-slider"
              />
              <div className="slider-hints">
                <span>1 (&lt;2 hrs)</span>
                <span>2 (2-5 hrs)</span>
                <span>3 (5-10 hrs)</span>
                <span>4 (&gt;10 hrs)</span>
              </div>
            </div>

            {/* Past Failures */}
            <div className="slider-group">
              <div className="slider-label-row">
                <span className="slider-name">Past Course Failures</span>
                <span className="slider-value badge-neutral">{failures} failures</span>
              </div>
              <input
                type="range"
                min={0}
                max={4}
                step={1}
                value={failures}
                onChange={(e) => setFailures(Number(e.target.value))}
                className="custom-range-slider"
              />
              <div className="slider-hints">
                <span>0 (Clean)</span>
                <span>1</span>
                <span>2</span>
                <span>3</span>
                <span>4+</span>
              </div>
            </div>

            {/* G1 Grade */}
            <div className="slider-group">
              <div className="slider-label-row">
                <span className="slider-name">First Period Grade (G1)</span>
                <span className="slider-value badge-neutral">{g1} / 20</span>
              </div>
              <input
                type="range"
                min={0}
                max={20}
                value={g1}
                onChange={(e) => setG1(Number(e.target.value))}
                className="custom-range-slider"
              />
              <div className="slider-hints">
                <span>0 (Fail)</span>
                <span>10 (Passing)</span>
                <span>20 (Perfect)</span>
              </div>
            </div>

            {/* G2 Grade (Mid-Term Model Only) */}
            {featureSet === "mid" && (
              <div className="slider-group">
                <div className="slider-label-row">
                  <span className="slider-name">Second Period Grade (G2)</span>
                  <span className="slider-value badge-neutral">{g2} / 20</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={20}
                  value={g2}
                  onChange={(e) => setG2(Number(e.target.value))}
                  className="custom-range-slider"
                />
                <div className="slider-hints">
                  <span>0 (Fail)</span>
                  <span>10 (Passing)</span>
                  <span>20 (Perfect)</span>
                </div>
              </div>
            )}

            {/* Assessment Score Trend */}
            <div className="slider-group">
              <div className="slider-label-row">
                <span className="slider-name">Quiz & Assessment Trend</span>
                <span className="slider-value badge-neutral">
                  {assessmentTrend === 1
                    ? "Improving (+1)"
                    : assessmentTrend === -1
                    ? "Declining (-1)"
                    : "Stable (0)"}
                </span>
              </div>
              <input
                type="range"
                min={-1}
                max={1}
                step={1}
                value={assessmentTrend}
                onChange={(e) => setAssessmentTrend(Number(e.target.value))}
                className="custom-range-slider"
              />
              <div className="slider-hints">
                <span>-1 (Worsening)</span>
                <span>0 (Stable)</span>
                <span>+1 (Improving)</span>
              </div>
            </div>

            {/* Assignment Completion Rate */}
            <div className="slider-group">
              <div className="slider-label-row">
                <span className="slider-name">Assignment Completion Rate</span>
                <span className="slider-value badge-neutral">{assignmentRate}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={assignmentRate}
                onChange={(e) => setAssignmentRate(Number(e.target.value))}
                className="custom-range-slider"
              />
              <div className="slider-hints">
                <span>0%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
            </div>

            <button
              type="button"
              onClick={runSimulation}
              disabled={loading}
              className="btn btn-primary w-full flex items-center justify-center gap-2 mt-4"
            >
              {loading ? (
                <>
                  <RefreshCw size={16} className="animate-spin" />
                  Calculating ML Predictions...
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  Simulate What-If Prediction
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right: Comparative Results */}
        <div className="simulator-results-col">
          {result ? (
            <>
              {/* Transition Banner */}
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="card-title text-sm">Simulated Category Transition</h3>
                  <div
                    className={`risk-shift-badge ${
                      riskDir === "improved"
                        ? "shift-improved"
                        : riskDir === "worsened"
                        ? "shift-worsened"
                        : "shift-neutral"
                    }`}
                  >
                    {riskDir === "improved" ? (
                      <>
                        <TrendingUp size={16} /> Improved Academic Outlook
                      </>
                    ) : riskDir === "worsened" ? (
                      <>
                        <TrendingDown size={16} /> Heightened Academic Risk
                      </>
                    ) : (
                      <>
                        <Minus size={16} /> Unchanged Category
                      </>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 items-center relative">
                  {/* Baseline Side */}
                  <div className="comparison-box baseline-box">
                    <div className="text-xs text-neutral-400 font-medium mb-1 flex items-center justify-between">
                      <span>Original Baseline</span>
                      {selectedStudent && (
                        <span className="text-[11px] text-primary-300 font-mono">
                          {selectedStudent.student_code || selectedStudent.student_id}
                        </span>
                      )}
                    </div>
                    <div className={`status-badge-lg ${getCategoryColor(result.original.category)}`}>
                      {result.original.category}
                    </div>
                    <div className="mt-3 text-sm text-neutral-300">
                      Confidence: <strong>{(result.original.confidence * 100).toFixed(1)}%</strong>
                    </div>
                    <div className="mt-2 text-xs text-neutral-400 space-y-1">
                      <div>Absences: <strong>{result.original.inputs.absences} days</strong></div>
                      <div>Study Time: <strong>Level {result.original.inputs.studytime}</strong></div>
                      <div>G1 Grade: <strong>{result.original.inputs.G1}/20</strong></div>
                      {result.original.inputs.G2 !== undefined && (
                        <div>G2 Grade: <strong>{result.original.inputs.G2}/20</strong></div>
                      )}
                      <div>Homework: <strong>{result.original.inputs.assignment_rate ?? 75}%</strong></div>
                    </div>
                  </div>

                  {/* Simulated Side */}
                  <div className="comparison-box simulated-box">
                    <div className="text-xs text-primary-300 font-medium mb-1 flex items-center gap-1">
                      <Sparkles size={13} />
                      Simulated What-If
                    </div>
                    <div className={`status-badge-lg ${getCategoryColor(result.simulated.category)}`}>
                      {result.simulated.category}
                    </div>
                    <div className="mt-3 text-sm text-neutral-300">
                      Confidence: <strong>{(result.simulated.confidence * 100).toFixed(1)}%</strong>
                    </div>
                    <div className="mt-2 text-xs text-neutral-400 space-y-1">
                      <div>Absences: <strong>{result.simulated.inputs.absences} days</strong></div>
                      <div>Study Time: <strong>Level {result.simulated.inputs.studytime}</strong></div>
                      <div>G1 Grade: <strong>{result.simulated.inputs.G1}/20</strong></div>
                      {result.simulated.inputs.G2 !== undefined && (
                        <div>G2 Grade: <strong>{result.simulated.inputs.G2}/20</strong></div>
                      )}
                      <div>Homework: <strong>{result.simulated.inputs.assignment_rate ?? 75}%</strong></div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Confidence Delta Metric Card */}
              <div className="card">
                <h3 className="card-title text-sm mb-3">Model Confidence Shift</h3>
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-neutral-400">Baseline Confidence ({result.original.category})</span>
                      <span className="font-semibold text-neutral-200">{(result.original.confidence * 100).toFixed(1)}%</span>
                    </div>
                    <div className="progress-bar-bg">
                      <div
                        className="progress-bar-fill bg-neutral-500"
                        style={{ width: `${result.original.confidence * 100}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-primary-300 font-medium">Simulated Confidence ({result.simulated.category})</span>
                      <span className="font-semibold text-primary-300">{(result.simulated.confidence * 100).toFixed(1)}%</span>
                    </div>
                    <div className="progress-bar-bg">
                      <div
                        className={`progress-bar-fill ${
                          result.simulated.category === "Performing Well"
                            ? "bg-emerald-500"
                            : result.simulated.category === "At-Risk"
                            ? "bg-rose-500"
                            : "bg-amber-500"
                        }`}
                        style={{ width: `${result.simulated.confidence * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Actionable Interpretation */}
              <div className="card bg-surface-900 border border-neutral-700/60">
                <h3 className="card-title text-sm mb-2 flex items-center gap-2">
                  <CheckCircle2 size={16} className="text-emerald-400" />
                  Key Observation & Sensitivity Notes
                </h3>
                <p className="text-xs text-neutral-300 leading-relaxed">
                  {riskDir === "improved" ? (
                    <>
                      Adjusting input factors (e.g. lowering absences to <strong>{absences}</strong> and increasing study time) produced a favorable shift from <strong>{result.original.category}</strong> to <strong>{result.simulated.category}</strong> with <strong>{(result.simulated.confidence * 100).toFixed(1)}%</strong> model confidence. This demonstrates the high sensitivity of the trained model to consistent attendance and regular study habits.
                    </>
                  ) : riskDir === "worsened" ? (
                    <>
                      Increasing risk-inducing behaviors (higher absences or lower academic scores) increased the student's failure probability, shifting classification to <strong>{result.simulated.category}</strong>. Targeted early interventions should prioritize arresting these factors.
                    </>
                  ) : (
                    <>
                      The simulated modifications kept the student in the <strong>{result.simulated.category}</strong> category. More significant interventions in core grades and attendance recovery may be necessary to cross the classification boundary.
                    </>
                  )}
                </p>
              </div>
            </>
          ) : (
            <div className="card flex items-center justify-center p-12 text-neutral-500 text-sm">
              Adjust parameters on the left and click "Simulate What-If Prediction".
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SimulatorPage;
