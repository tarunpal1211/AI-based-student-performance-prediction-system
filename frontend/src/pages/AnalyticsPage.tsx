import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getClassAnalytics,
  getTrends,
  getModelMetrics,
  getCohortAnalytics,
} from "../api/services";
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
} from "recharts";
import {
  BarChart2,
  Table as TableIcon,
  Layers,
  Users,
  CheckCircle2,
  Target,
} from "lucide-react";

const CATEGORY_COLORS: Record<string, string> = {
  "At-Risk": "#ef4444",
  "Needs Improvement": "#eab308",
  "Performing Well": "#22c55e",
};

const CLASS_METRICS_INFO: Record<string, { subtitle: string; role: string; color: string; tier: string }> = {
  "At-Risk": {
    subtitle: "Safety Intervention",
    role: "High sensitivity (80%+) catches vulnerable students early so counselors can deploy academic recovery plans.",
    color: "#ef4444",
    tier: "Safety Bias",
  },
  "Needs Improvement": {
    subtitle: "Targeted Reinforcement",
    role: "High precision (94%+) avoids alert fatigue, focusing tutoring strictly on students genuinely needing support.",
    color: "#f59e0b",
    tier: "High Precision",
  },
  "Performing Well": {
    subtitle: "Autonomous Benchmark",
    role: "Near-perfect recall (98%+) confirms stable learners without generating advisor overhead.",
    color: "#22c55e",
    tier: "Optimal Stability",
  },
};

const AnalyticsPage: React.FC = () => {
  const [selectedModelTab, setSelectedModelTab] = useState<"early" | "mid">("early");

  const analytics = useQuery({ queryKey: ["class-analytics"], queryFn: getClassAnalytics });
  const trends = useQuery({ queryKey: ["trends"], queryFn: getTrends });
  const metrics = useQuery({ queryKey: ["model-metrics"], queryFn: getModelMetrics });
  const cohorts = useQuery({ queryKey: ["cohort-analytics"], queryFn: getCohortAnalytics });

  // Bar chart data
  const barData = analytics.data
    ? [
        { name: "At-Risk", count: analytics.data.at_risk_count, pct: analytics.data.at_risk_pct },
        { name: "Needs Improvement", count: analytics.data.needs_improvement_count, pct: analytics.data.needs_improvement_pct },
        { name: "Performing Well", count: analytics.data.performing_well_count, pct: analytics.data.performing_well_pct },
      ]
    : [];

  // Trend line data
  const trendByDate: Record<string, Record<string, number>> = {};
  (trends.data ?? []).forEach(({ date, category, count }) => {
    if (!trendByDate[date]) trendByDate[date] = {};
    trendByDate[date][category] = count;
  });
  const trendData = Object.entries(trendByDate)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, cats]) => ({ date, ...cats }));

  // Active Model Metric Data
  const activeMetric = (metrics.data ?? []).find((m) => m.feature_set === selectedModelTab);

  // Model comparison bar data
  const metricsBarData = (metrics.data ?? []).map((m) => ({
    name: m.feature_set === "early" ? "Early (G1)" : "Mid (G1+G2)",
    Accuracy: +(m.accuracy * 100).toFixed(1),
    "Macro F1": +(m.macro_f1 * 100).toFixed(1),
    "At-Risk Recall": +(m.at_risk_recall * 100).toFixed(1),
  }));

  const classNames = ["At-Risk", "Needs Improvement", "Performing Well"];

  return (
    <div className="page-container space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <BarChart2 className="text-primary-400" size={28} />
            Institutional Analytics & Model Evaluation
          </h1>
          <p className="page-subtitle">
            Comprehensive diagnostic distributions, algorithm validation matrices, and cohort comparative analytics.
          </p>
        </div>
      </div>

      {/* Summary KPI Banner */}
      {analytics.data && (
        <div className="analytics-kpi-grid">
          <div className="card">
            <div className="text-xs text-neutral-400 font-medium">Total Predictions</div>
            <div className="text-2xl font-bold text-neutral-100 mt-1">{analytics.data.total_predictions}</div>
            <div className="text-xs text-neutral-500 mt-1">Institutional records</div>
          </div>

          <div className="card">
            <div className="text-xs text-neutral-400 font-medium">Average Confidence</div>
            <div className="text-2xl font-bold text-primary-400 mt-1">
              {(analytics.data.avg_confidence * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-neutral-500 mt-1">Mean model certainty</div>
          </div>

          <div className="card">
            <div className="text-xs text-neutral-400 font-medium">At-Risk Rate</div>
            <div className="text-2xl font-bold text-rose-400 mt-1">{analytics.data.at_risk_pct}%</div>
            <div className="text-xs text-neutral-500 mt-1">{analytics.data.at_risk_count} flagged students</div>
          </div>

          <div className="card">
            <div className="text-xs text-neutral-400 font-medium">Performing Well Rate</div>
            <div className="text-2xl font-bold text-emerald-400 mt-1">
              {analytics.data.performing_well_pct}%
            </div>
            <div className="text-xs text-neutral-500 mt-1">{analytics.data.performing_well_count} students on target</div>
          </div>
        </div>
      )}

      {/* Category Distribution & Model Overview */}
      <div className="analytics-charts-grid">
        {/* Distribution Bar Chart */}
        <div className="card">
          <h3 className="card-title text-sm mb-4">Class Performance Category Distribution</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={barData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#a3a3a3" }} />
              <YAxis tick={{ fontSize: 11, fill: "#a3a3a3" }} />
              <Tooltip
                contentStyle={{ backgroundColor: "#171717", borderColor: "#404040", borderRadius: 8 }}
                formatter={(v) => [`${v} students`, "Count"]}
              />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {barData.map((entry) => (
                  <Cell key={entry.name} fill={CATEGORY_COLORS[entry.name] ?? "#6b7280"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Model Metrics Grouped Bar */}
        <div className="card">
          <h3 className="card-title text-sm mb-4">Overall Model Evaluation Metrics (%)</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={metricsBarData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#a3a3a3" }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#a3a3a3" }} />
              <Tooltip contentStyle={{ backgroundColor: "#171717", borderColor: "#404040", borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />
              <Bar dataKey="Accuracy" fill="#6366f1" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Macro F1" fill="#06b6d4" radius={[4, 4, 0, 0]} />
              <Bar dataKey="At-Risk Recall" fill="#ef4444" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Model Diagnostic Deep-Dive (Confusion Matrix & CV Comparison) */}
      <div className="card">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6 pb-4 border-b border-neutral-800">
          <div>
            <h3 className="card-title text-base flex items-center gap-2">
              <TableIcon size={18} className="text-primary-400" />
              Detailed Model Validation & Confusion Matrix
            </h3>
            <p className="text-xs text-neutral-400 mt-0.5">
              Scientific validation on 20% holdout test set (n=209 verified benchmark records with ground truth final grades).
            </p>
          </div>

          <div className="model-selector-pill">
            <button
              type="button"
              className={`pill-btn ${selectedModelTab === "early" ? "active" : ""}`}
              onClick={() => setSelectedModelTab("early")}
            >
              Early Model (G1)
            </button>
            <button
              type="button"
              className={`pill-btn ${selectedModelTab === "mid" ? "active" : ""}`}
              onClick={() => setSelectedModelTab("mid")}
            >
              Mid-Term Model (G1+G2)
            </button>
          </div>
        </div>

        {activeMetric ? (
          <div>
            <div className="model-deep-dive-grid">
              {/* Confusion Matrix Panel (Left Side) */}
              <div className="matrix-panel">
                <div className="matrix-header-box">
                  <div className="matrix-title">
                    <TableIcon size={15} className="text-primary-400" />
                    Confusion Matrix (Actual vs Predicted)
                  </div>
                  <div className="matrix-subtitle">
                    Row = Actual Ground Truth | Col = Predicted Category (Holdout Test Set, n=209)
                  </div>
                </div>

                {activeMetric.confusion_matrix ? (
                  <div className="matrix-table-wrapper">
                    <table className="confusion-matrix-table">
                      <thead>
                        <tr>
                          <th className="axis-corner">Actual \ Pred</th>
                          {classNames.map((c) => (
                            <th key={c}>
                              <span style={{ color: CATEGORY_COLORS[c] ?? "#e4e4e7" }}>
                                {c === "Needs Improvement" ? "Needs Impr." : c === "Performing Well" ? "Perf. Well" : c}
                              </span>
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {activeMetric.confusion_matrix.map((row, rIdx) => {
                          const rowTotal = row.reduce((a, b) => a + b, 0);
                          const shortName =
                            classNames[rIdx] === "Needs Improvement"
                              ? "Needs Impr."
                              : classNames[rIdx] === "Performing Well"
                              ? "Perf. Well"
                              : classNames[rIdx];
                          return (
                            <tr key={rIdx}>
                              <td className="matrix-row-header">
                                <div>{shortName}</div>
                                <div style={{ fontSize: "9px", color: "#71717a", fontWeight: "normal" }}>
                                  n = {rowTotal}
                                </div>
                              </td>
                              {row.map((val, cIdx) => {
                                const isDiagonal = rIdx === cIdx;
                                const cellPct = rowTotal > 0 ? ((val / rowTotal) * 100).toFixed(1) : "0.0";
                                if (isDiagonal) {
                                  return (
                                    <td key={cIdx} className="matrix-cell matrix-cell-diagonal">
                                      <div className="matrix-cell-val">{val}</div>
                                      <div className="matrix-cell-pct">{cellPct}% hit</div>
                                    </td>
                                  );
                                }
                                if (val > 0) {
                                  return (
                                    <td key={cIdx} className="matrix-cell matrix-cell-error">
                                      <div className="matrix-cell-val">{val}</div>
                                      <div className="matrix-cell-pct">{cellPct}% error</div>
                                    </td>
                                  );
                                }
                                return (
                                  <td key={cIdx} className="matrix-cell matrix-cell-zero">
                                    <div className="matrix-cell-val">0</div>
                                    <div className="matrix-cell-pct" style={{ opacity: 0.3 }}>0%</div>
                                  </td>
                                );
                              })}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-xs text-neutral-500 py-6">Confusion matrix not generated for this model.</p>
                )}

                <div className="matrix-legend">
                  <div className="matrix-legend-row">
                    <div className="matrix-legend-swatch diag" />
                    <span><strong>Diagonal (Purple):</strong> True Positives — correctly classified holdout students</span>
                  </div>
                  <div className="matrix-legend-row">
                    <div className="matrix-legend-swatch err" />
                    <span><strong>Off-Diagonal (Red):</strong> Discrepancies — cross-category misclassifications</span>
                  </div>
                </div>
              </div>

              {/* Per-Class Classification Metrics Panel (Right Side) */}
              <div className="detailed-metrics-panel">
                <div className="detailed-metrics-header">
                  <div className="detailed-metrics-title">
                    <Target size={15} className="text-primary-400" />
                    Per-Class Classification Metrics & Clinical Diagnostic Role
                  </div>
                  <div className="detailed-metrics-subtitle">
                    Class-level sensitivity, precision, and operational impact on holdout test set (n=209).
                  </div>
                </div>

                {activeMetric.per_class ? (() => {
                  const perClassEntries = Object.entries(activeMetric.per_class);
                  const totalSupport = perClassEntries.reduce((sum, [, m]: any) => sum + (m.support || 0), 0);
                  const macroPrecision = perClassEntries.length > 0
                    ? perClassEntries.reduce((sum, [, m]: any) => sum + (m.precision || 0), 0) / perClassEntries.length
                    : 0;
                  const macroRecall = perClassEntries.length > 0
                    ? perClassEntries.reduce((sum, [, m]: any) => sum + (m.recall || 0), 0) / perClassEntries.length
                    : 0;

                  return (
                    <div className="detailed-metrics-table-wrapper">
                      <table className="detailed-metrics-table">
                        <thead>
                          <tr>
                            <th>Category</th>
                            <th>Precision</th>
                            <th>Recall</th>
                            <th>F1-Score</th>
                            <th>Support</th>
                            <th>Clinical Diagnostic Role</th>
                          </tr>
                        </thead>
                        <tbody>
                          {perClassEntries.map(([className, m]: any) => {
                            const info = CLASS_METRICS_INFO[className] || {
                              subtitle: "Academic Category",
                              role: "Standard multi-class categorization metric.",
                              color: "#6366f1",
                              tier: "Standard",
                            };
                            const precPct = (m.precision * 100).toFixed(1);
                            const recPct = (m.recall * 100).toFixed(1);
                            const f1Pct = (m.f1 * 100).toFixed(1);
                            const supportPct = totalSupport > 0 ? ((m.support / totalSupport) * 100).toFixed(1) : "0.0";
                            const badgeClass =
                              className === "At-Risk"
                                ? "badge-at-risk"
                                : className === "Needs Improvement"
                                ? "badge-needs-improvement"
                                : "badge-performing-well";

                            return (
                              <tr key={className}>
                                <td>
                                  <div className="metric-category-cell">
                                    <span className={`badge ${badgeClass}`}>{className}</span>
                                    <span className="metric-category-sub">{info.subtitle}</span>
                                  </div>
                                </td>
                                <td>
                                  <div className="metric-bar-cell">
                                    <div className="metric-bar-val">
                                      <span>{precPct}%</span>
                                      <span className="text-[10px] text-neutral-500 font-normal">PPV</span>
                                    </div>
                                    <div className="metric-bar-track">
                                      <div
                                        className="metric-bar-fill"
                                        style={{ width: `${precPct}%`, backgroundColor: info.color }}
                                      />
                                    </div>
                                  </div>
                                </td>
                                <td>
                                  <div className="metric-bar-cell">
                                    <div className="metric-bar-val">
                                      <span style={{ color: info.color }}>{recPct}%</span>
                                      <span className="text-[10px] text-neutral-500 font-normal">Sens</span>
                                    </div>
                                    <div className="metric-bar-track">
                                      <div
                                        className="metric-bar-fill"
                                        style={{ width: `${recPct}%`, backgroundColor: info.color }}
                                      />
                                    </div>
                                  </div>
                                </td>
                                <td>
                                  <div className="metric-f1-cell">{f1Pct}%</div>
                                  <div className="metric-f1-tier">{info.tier}</div>
                                </td>
                                <td>
                                  <div className="metric-support-cell">{m.support}</div>
                                  <div className="metric-support-sub">{supportPct}% cohort</div>
                                </td>
                                <td>
                                  <div className="metric-role-desc">{info.role}</div>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                        <tfoot>
                          <tr>
                            <td>
                              <div className="font-bold text-neutral-200">Macro Average</div>
                              <div className="metric-category-sub">Unweighted Mean</div>
                            </td>
                            <td>
                              <div className="metric-bar-cell">
                                <div className="metric-bar-val">
                                  <span>{(macroPrecision * 100).toFixed(1)}%</span>
                                </div>
                                <div className="metric-bar-track">
                                  <div
                                    className="metric-bar-fill"
                                    style={{ width: `${macroPrecision * 100}%`, backgroundColor: "#818cf8" }}
                                  />
                                </div>
                              </div>
                            </td>
                            <td>
                              <div className="metric-bar-cell">
                                <div className="metric-bar-val">
                                  <span className="text-primary-300">{(macroRecall * 100).toFixed(1)}%</span>
                                </div>
                                <div className="metric-bar-track">
                                  <div
                                    className="metric-bar-fill"
                                    style={{ width: `${macroRecall * 100}%`, backgroundColor: "#818cf8" }}
                                  />
                                </div>
                              </div>
                            </td>
                            <td>
                              <div className="metric-f1-cell text-primary-300">
                                {(activeMetric.macro_f1 * 100).toFixed(1)}%
                              </div>
                              <div className="metric-f1-tier text-emerald-400">Institutional F1</div>
                            </td>
                            <td>
                              <div className="metric-support-cell text-neutral-200">{totalSupport}</div>
                              <div className="metric-support-sub">100% Holdout Set</div>
                            </td>
                            <td>
                              <div className="metric-role-desc text-neutral-400">
                                Multi-class diagnostic balance with safety-net recall prioritizing early intervention.
                              </div>
                            </td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  );
                })() : (
                  <p className="text-xs text-neutral-500 py-6">Per-class metrics not available.</p>
                )}
              </div>
            </div>

            {/* 5-Fold Cross Validation Algorithm Comparison */}
            {activeMetric.cv_summary && activeMetric.cv_summary.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-neutral-300 mb-3 flex items-center gap-1.5">
                  <Layers size={14} className="text-primary-400" />
                  Algorithm 5-Fold Cross-Validation Comparison
                </h4>
                <div className="overflow-x-auto">
                  <table className="table-styled">
                    <thead>
                      <tr>
                        <th>Algorithm</th>
                        <th>CV Accuracy (Mean ± Std)</th>
                        <th>Macro F1 (Mean ± Std)</th>
                        <th>At-Risk Recall (Mean ± Std)</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {activeMetric.cv_summary.map((cvItem: any) => {
                        const isBest = cvItem.model === activeMetric.best_model;
                        return (
                          <tr key={cvItem.model} className={isBest ? "bg-primary-950/30" : ""}>
                            <td className="font-bold text-neutral-200 flex items-center gap-2">
                              {cvItem.model}
                              {isBest && (
                                <span className="badge badge-performing-well text-[10px] py-0.5">
                                  Production Model
                                </span>
                              )}
                            </td>
                            <td>
                              {(cvItem.cv_accuracy * 100).toFixed(1)}% ± {(cvItem.cv_accuracy_std * 100).toFixed(1)}%
                            </td>
                            <td>
                              {(cvItem.cv_f1_macro * 100).toFixed(1)}% ± {(cvItem.cv_f1_macro_std * 100).toFixed(1)}%
                            </td>
                            <td className="font-semibold text-rose-400">
                              {(cvItem.cv_at_risk_recall * 100).toFixed(1)}% ± {(cvItem.cv_at_risk_recall_std * 100).toFixed(1)}%
                            </td>
                            <td>
                              {isBest ? (
                                <span className="text-emerald-400 font-semibold text-xs flex items-center gap-1">
                                  <CheckCircle2 size={13} /> Selected
                                </span>
                              ) : (
                                <span className="text-neutral-500 text-xs">Evaluated</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-neutral-500 text-xs">
            Metric details loading or not found.
          </div>
        )}
      </div>

      {/* Cross-Cohort / Section Analytics */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="card-title text-base flex items-center gap-2">
              <Users size={18} className="text-primary-400" />
              Cohort & Section Cross-Sectional Analytics
            </h3>
            <p className="text-xs text-neutral-400 mt-0.5">
              Risk breakdown and performance rate comparisons across class cohorts and academic groups.
            </p>
          </div>
          {cohorts.data && (
            <span className="text-xs text-neutral-400">
              Total Cohort Students: <strong>{cohorts.data.total_students}</strong>
            </span>
          )}
        </div>

        {cohorts.isLoading ? (
          <div className="text-center py-8 text-xs text-neutral-400">Loading cohort metrics...</div>
        ) : cohorts.data && cohorts.data.cohorts.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="table-styled">
              <thead>
                <tr>
                  <th>Cohort / Section</th>
                  <th>Total Enrolled</th>
                  <th>At-Risk Count</th>
                  <th>At-Risk %</th>
                  <th>Needs Improvement %</th>
                  <th>Performing Well %</th>
                  <th>Mean Confidence</th>
                  <th>Risk Tier</th>
                </tr>
              </thead>
              <tbody>
                {cohorts.data.cohorts.map((c) => (
                  <tr key={c.cohort_name}>
                    <td className="font-bold text-neutral-200">{c.cohort_name}</td>
                    <td>{c.total_students}</td>
                    <td className="text-rose-400 font-bold">{c.at_risk_count}</td>
                    <td className="text-rose-400 font-semibold">{c.at_risk_pct}%</td>
                    <td className="text-amber-400">{c.needs_improvement_pct}%</td>
                    <td className="text-emerald-400 font-semibold">{c.performing_well_pct}%</td>
                    <td>{(c.avg_confidence * 100).toFixed(1)}%</td>
                    <td>
                      {c.at_risk_pct > 25 ? (
                        <span className="badge badge-at-risk text-[10px]">High Attention</span>
                      ) : c.at_risk_pct > 15 ? (
                        <span className="badge badge-needs-improvement text-[10px]">Moderate</span>
                      ) : (
                        <span className="badge badge-performing-well text-[10px]">Stable</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-6 text-xs text-neutral-500">
            No cohort breakdowns available.
          </div>
        )}
      </div>

      {/* Historical Trend Chart */}
      <div className="card">
        <h3 className="card-title text-sm mb-4">Historical Prediction Volume & Trajectory Trends</h3>
        {trendData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trendData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#a3a3a3" }} />
              <YAxis tick={{ fontSize: 11, fill: "#a3a3a3" }} />
              <Tooltip contentStyle={{ backgroundColor: "#171717", borderColor: "#404040", borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />
              {Object.entries(CATEGORY_COLORS).map(([cat, color]) => (
                <Line key={cat} type="monotone" dataKey={cat} stroke={color} dot={false} strokeWidth={2} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-center py-8 text-xs text-neutral-500">No trend data available yet.</p>
        )}
      </div>
    </div>
  );
};

export default AnalyticsPage;
