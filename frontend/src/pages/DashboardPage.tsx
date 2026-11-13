import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  getClassAnalytics,
  getAtRiskStudents,
  getTrends,
  getModelMetrics,
} from "../api/services";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Legend,
} from "recharts";
import {
  Users, AlertTriangle, TrendingUp, Award, Target, BarChart2, Eye, Sparkles, ExternalLink,
} from "lucide-react";
import StudentDetailModal from "../components/StudentDetailModal";

const CATEGORY_COLORS: Record<string, string> = {
  "At-Risk": "#ef4444",
  "Needs Improvement": "#f59e0b",
  "Performing Well": "#22c55e",
};

const getCategoryBadgeClass = (category: string) => {
  switch (category) {
    case "At-Risk":
      return "badge-at-risk";
    case "Needs Improvement":
      return "badge-needs-improvement";
    case "Performing Well":
      return "badge-performing-well";
    default:
      return "badge-neutral";
  }
};

const StatCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
  isActive?: boolean;
  onClick?: () => void;
}> = ({ icon, label, value, sub, color, isActive, onClick }) => (
  <div
    className="stat-card"
    onClick={onClick}
    style={{
      borderTopColor: color,
      cursor: onClick ? "pointer" : "default",
      boxShadow: isActive ? `0 0 0 2px ${color}` : undefined,
      transform: isActive ? "translateY(-2px)" : undefined,
      transition: "all 0.15s ease",
    }}
    title={onClick ? `Filter table by ${label}` : undefined}
  >
    <div className="stat-icon" style={{ color }}>{icon}</div>
    <div>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  </div>
);

const DashboardPage: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const analytics = useQuery({ queryKey: ["class-analytics"], queryFn: getClassAnalytics });
  const studentList = useQuery({
    queryKey: ["dashboard-students", selectedCategory],
    queryFn: () => getAtRiskStudents(25, selectedCategory),
  });
  const trends = useQuery({ queryKey: ["trends"], queryFn: getTrends });
  const metrics = useQuery({ queryKey: ["model-metrics"], queryFn: getModelMetrics });
  const [selectedPredictionId, setSelectedPredictionId] = useState<string | null>(null);

  const d = analytics.data;

  // Build pie data
  const pieData = d
    ? [
        { name: "At-Risk", value: d.at_risk_count },
        { name: "Needs Improvement", value: d.needs_improvement_count },
        { name: "Performing Well", value: d.performing_well_count },
      ].filter((x) => x.value > 0)
    : [];

  // Build trend line data (group by date)
  const trendByDate: Record<string, Record<string, number>> = {};
  (trends.data ?? []).forEach(({ date, category, count }) => {
    if (!trendByDate[date]) trendByDate[date] = {};
    trendByDate[date][category] = count;
  });
  const trendData = Object.entries(trendByDate)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-30)
    .map(([date, cats]) => ({ date, ...cats }));

  return (
    <div className="page">
      <div className="page-header">
        <div className="ai-badge-header">
          <Sparkles size={12} /> Real-Time Analytics
        </div>
        <h2 className="predict-page-title">Executive Dashboard</h2>
        <p className="predict-page-subtitle">Overview of student cohort academic trajectory and active risk flags</p>
      </div>

      {/* Stat Cards */}
      {analytics.isLoading ? (
        <div className="skeleton-row">
          {[1, 2, 3, 4].map((i) => <div key={i} className="skeleton-card" />)}
        </div>
      ) : d ? (
        <div className="stats-grid">
          <StatCard
            icon={<Users size={22} />}
            label="Total Predictions"
            value={d.total_predictions}
            color="#4f46e5"
            isActive={selectedCategory === "all"}
            onClick={() => setSelectedCategory("all")}
          />
          <StatCard
            icon={<AlertTriangle size={22} />}
            label="At-Risk"
            value={`${d.at_risk_count} (${d.at_risk_pct}%)`}
            color="#ef4444"
            isActive={selectedCategory === "At-Risk"}
            onClick={() => setSelectedCategory("At-Risk")}
          />
          <StatCard
            icon={<TrendingUp size={22} />}
            label="Needs Improvement"
            value={`${d.needs_improvement_count} (${d.needs_improvement_pct}%)`}
            color="#f59e0b"
            isActive={selectedCategory === "Needs Improvement"}
            onClick={() => setSelectedCategory("Needs Improvement")}
          />
          <StatCard
            icon={<Award size={22} />}
            label="Performing Well"
            value={`${d.performing_well_count} (${d.performing_well_pct}%)`}
            color="#22c55e"
            isActive={selectedCategory === "Performing Well"}
            onClick={() => setSelectedCategory("Performing Well")}
          />
        </div>
      ) : null}

      <div className="charts-row">
        {/* Pie Chart */}
        <div className="card chart-card">
          <h3><Target size={16} /> Risk Distribution</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}>
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={CATEGORY_COLORS[entry.name] ?? "#6b7280"} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="empty">No data yet.</p>}
        </div>

        {/* Line Chart */}
        <div className="card chart-card">
          <h3><BarChart2 size={16} /> Prediction Trends (last 30 days)</h3>
          {trendData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                {Object.keys(CATEGORY_COLORS).map((cat) => (
                  <Line key={cat} type="monotone" dataKey={cat} stroke={CATEGORY_COLORS[cat]} dot={false} strokeWidth={2} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          ) : <p className="empty">No trend data yet.</p>}
        </div>
      </div>

      {/* Evaluated Students Table */}
      <div className="card">
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: 10, marginBottom: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: 6 }}>
              {selectedCategory === "At-Risk" ? (
                <><AlertTriangle size={16} color="#ef4444" /> Priority Attention & At-Risk Students</>
              ) : selectedCategory === "Needs Improvement" ? (
                <><TrendingUp size={16} color="#f59e0b" /> Needs Improvement Students</>
              ) : selectedCategory === "Performing Well" ? (
                <><Award size={16} color="#22c55e" /> Performing Well Students</>
              ) : (
                <><Users size={16} color="var(--primary)" /> Recent Analyzed Students</>
              )}
            </h3>
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
              (Showing {studentList.data?.length ?? 0} {selectedCategory === "all" ? "evaluations" : selectedCategory})
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ display: "inline-flex", background: "var(--surface-sunken)", padding: "2px 4px", borderRadius: 8, gap: 4 }}>
              <button
                type="button"
                onClick={() => setSelectedCategory("all")}
                style={{
                  padding: "4px 10px",
                  fontSize: 12,
                  borderRadius: 6,
                  border: "none",
                  cursor: "pointer",
                  background: selectedCategory === "all" ? "var(--primary)" : "transparent",
                  color: selectedCategory === "all" ? "#fff" : "var(--text-muted)",
                  fontWeight: selectedCategory === "all" ? 600 : 400,
                  transition: "all 0.15s ease",
                }}
              >
                All ({d?.total_predictions ?? 0})
              </button>
              <button
                type="button"
                onClick={() => setSelectedCategory("At-Risk")}
                style={{
                  padding: "4px 10px",
                  fontSize: 12,
                  borderRadius: 6,
                  border: "none",
                  cursor: "pointer",
                  background: selectedCategory === "At-Risk" ? "#ef4444" : "transparent",
                  color: selectedCategory === "At-Risk" ? "#fff" : "var(--text-muted)",
                  fontWeight: selectedCategory === "At-Risk" ? 600 : 400,
                  transition: "all 0.15s ease",
                }}
              >
                At-Risk ({d?.at_risk_count ?? 0})
              </button>
              <button
                type="button"
                onClick={() => setSelectedCategory("Needs Improvement")}
                style={{
                  padding: "4px 10px",
                  fontSize: 12,
                  borderRadius: 6,
                  border: "none",
                  cursor: "pointer",
                  background: selectedCategory === "Needs Improvement" ? "#f59e0b" : "transparent",
                  color: selectedCategory === "Needs Improvement" ? "#fff" : "var(--text-muted)",
                  fontWeight: selectedCategory === "Needs Improvement" ? 600 : 400,
                  transition: "all 0.15s ease",
                }}
              >
                Needs Impr ({d?.needs_improvement_count ?? 0})
              </button>
              <button
                type="button"
                onClick={() => setSelectedCategory("Performing Well")}
                style={{
                  padding: "4px 10px",
                  fontSize: 12,
                  borderRadius: 6,
                  border: "none",
                  cursor: "pointer",
                  background: selectedCategory === "Performing Well" ? "#22c55e" : "transparent",
                  color: selectedCategory === "Performing Well" ? "#fff" : "var(--text-muted)",
                  fontWeight: selectedCategory === "Performing Well" ? 600 : 400,
                  transition: "all 0.15s ease",
                }}
              >
                Well ({d?.performing_well_count ?? 0})
              </button>
            </div>

            <Link
              to="/history"
              style={{
                fontSize: 12,
                color: "var(--primary)",
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
                textDecoration: "none",
                fontWeight: 500,
                marginLeft: 4,
              }}
            >
              Full History <ExternalLink size={12} />
            </Link>
          </div>
        </div>

        {studentList.isLoading ? <div className="skeleton-table" /> : (
          studentList.data && studentList.data.length > 0 ? (
            <div className="data-table-container" style={{ border: "none", marginBottom: 0 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Student ID</th>
                    <th>Category</th>
                    <th>Confidence</th>
                    <th>Predicted At</th>
                    <th style={{ textAlign: "center" }}>Report</th>
                  </tr>
                </thead>
                <tbody>
                  {studentList.data.map((s) => (
                    <tr key={s.prediction_id}>
                      <td>
                        <strong
                          style={{ cursor: "pointer", color: "var(--primary)" }}
                          onClick={() => setSelectedPredictionId(s.prediction_id)}
                          title="Click to view detailed report"
                        >
                          {s.student_code || s.student_id || "N/A"}
                        </strong>
                      </td>
                      <td>
                        <span className={`status-badge-sm ${getCategoryBadgeClass(s.category)}`}>
                          {s.category}
                        </span>
                      </td>
                      <td>{(s.confidence * 100).toFixed(1)}%</td>
                      <td>{new Date(s.predicted_at).toLocaleDateString()}</td>
                      <td style={{ textAlign: "center" }}>
                        <button
                          type="button"
                          className="btn-secondary"
                          style={{ padding: "4px 10px", fontSize: 12, display: "inline-flex", alignItems: "center", gap: 5 }}
                          onClick={() => setSelectedPredictionId(s.prediction_id)}
                        >
                          <Eye size={13} /> View Report
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="empty">
              {selectedCategory === "all"
                ? "No analyzed student records found yet. Go to Predict to run evaluations."
                : `No ${selectedCategory} students found.`}
            </p>
          )
        )}
      </div>

      {/* Model Metrics */}
      {metrics.data && metrics.data.length > 0 && (
        <div className="card">
          <h3><BarChart2 size={16} /> Model Performance Metrics</h3>
          <div className="metrics-grid">
            {metrics.data.map((m) => (
              <div key={m.feature_set} className="metric-card">
                <div className="metric-label">{m.feature_set === "early" ? "Early Model (G1)" : "Mid Model (G1+G2)"}</div>
                <div className="metric-row"><span>Best Model</span><strong>{m.best_model}</strong></div>
                <div className="metric-row"><span>Accuracy</span><strong>{(m.accuracy * 100).toFixed(1)}%</strong></div>
                <div className="metric-row"><span>Macro F1</span><strong>{m.macro_f1.toFixed(3)}</strong></div>
                <div className="metric-row"><span>At-Risk Recall</span><strong>{(m.at_risk_recall * 100).toFixed(1)}%</strong></div>
              </div>
            ))}
          </div>
        </div>
      )}

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

export default DashboardPage;
