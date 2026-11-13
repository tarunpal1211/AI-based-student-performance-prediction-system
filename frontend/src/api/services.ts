import { apiClient } from "./client";

// ── Auth ──────────────────────────────────────────────────────────────────────
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "teacher";
  is_active: boolean;
}

export const login = async (email: string, password: string): Promise<TokenResponse> => {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);
  const res = await apiClient.post<TokenResponse>("/api/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return res.data;
};

export const getMe = async (): Promise<UserProfile> => {
  const res = await apiClient.get<UserProfile>("/api/auth/me");
  return res.data;
};

// ── Predict ───────────────────────────────────────────────────────────────────
export interface SinglePredictRequest {
  student_id?: string;
  feature_set: "early" | "mid";
  absences: number;
  G1: number;
  failures: number;
  studytime: number;
  G2?: number;
  assignment_rate?: number;
  assessment_trend?: number;
}

export interface XAIContribution {
  feature: string;
  label: string;
  value: number;
  importance: number;
  direction: "increased_risk" | "reduced_risk" | "neutral" | string;
  impact: "positive" | "negative" | "neutral" | string;
  description: string;
}

export interface XAIExplanation {
  summary: string;
  contributions: XAIContribution[];
  risk_factors: XAIContribution[];
  protective_factors: XAIContribution[];
}

export interface PredictionResponse {
  id: string;
  category: string;
  confidence: number;
  top_factors: any[];
  shap_values: Record<string, number> | null;
  explanation?: XAIExplanation | null;
  recommendations?: RecommendationItem[] | null;
  feature_set: string;
  model_name: string;
  predicted_at: string;
}

export const predictSingle = async (body: SinglePredictRequest): Promise<PredictionResponse> => {
  const res = await apiClient.post<PredictionResponse>("/api/predict/single", body);
  return res.data;
};

// ── Bulk Upload & Batch Prediction ───────────────────────────────────────────
export interface PreviewRow {
  row_index: number;
  student_id: string;
  is_valid: boolean;
  errors: string[];
  cleaned_data: Record<string, any>;
  raw_data: Record<string, any>;
}

export interface UploadValidateResponse {
  total_rows: number;
  valid_rows_count: number;
  invalid_rows_count: number;
  detected_columns: string[];
  column_mapping: Record<string, string>;
  unmapped_required: string[];
  duplicate_student_ids: string[];
  special_notes: string[];
  preview_rows: PreviewRow[];
  message: string;
}

export interface BatchStudentInput {
  row_index: number;
  student_id?: string;
  absences: number;
  G1: number;
  failures: number;
  studytime: number;
  G2?: number;
  assignment_rate?: number;
  assessment_trend?: number;
}

export interface BatchStudentResult {
  row_index: number;
  student_id: string;
  prediction_id: string;
  feature_set: string;
  model_name: string;
  category: "At-Risk" | "Needs Improvement" | "Performing Well" | string;
  confidence: number;
  top_factors: string[];
  inputs: Record<string, any>;
  recommendations: Array<{
    priority: "high" | "medium" | "low" | string;
    category: string;
    title: string;
    description: string;
    action: string;
  }>;
}

export interface BatchProcessResponse {
  job_id: string;
  total_rows: number;
  processed_rows: number;
  failed_rows: number;
  category_distribution: Record<string, number>;
  category_percentages: Record<string, number>;
  avg_confidence: number;
  results: BatchStudentResult[];
  created_at: string;
}

export const uploadAndValidate = async (
  file: File,
  featureSet: "early" | "mid",
  columnMapping?: Record<string, string>
): Promise<UploadValidateResponse> => {
  const form = new FormData();
  form.append("file", file);
  form.append("feature_set", featureSet);
  if (columnMapping) {
    form.append("column_mapping", JSON.stringify(columnMapping));
  }
  const res = await apiClient.post<UploadValidateResponse>(
    "/api/predict/upload-validate",
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return res.data;
};

export const processBatch = async (
  featureSet: "early" | "mid",
  records: BatchStudentInput[]
): Promise<BatchProcessResponse> => {
  const res = await apiClient.post<BatchProcessResponse>(
    "/api/predict/batch-process",
    { feature_set: featureSet, records }
  );
  return res.data;
};

export const downloadTemplate = async (
  featureSet: "early" | "mid",
  format: "csv" | "xlsx" = "csv"
): Promise<Blob> => {
  const res = await apiClient.get<Blob>(
    `/api/predict/template?format=${format}&feature_set=${featureSet}`,
    { responseType: "blob" }
  );
  return res.data;
};

export const exportBatchResults = async (
  results: BatchStudentResult[],
  format: "csv" | "xlsx",
  featureSet: "early" | "mid"
): Promise<Blob> => {
  const res = await apiClient.post<Blob>(
    "/api/predict/export",
    { format, feature_set: featureSet, results },
    { responseType: "blob" }
  );
  return res.data;
};

// ── History ───────────────────────────────────────────────────────────────────
export interface PredictionHistoryItem {
  id: string;
  student_id: string | null;
  student_code?: string | null;
  feature_set: string;
  model_name: string;
  input_features: Record<string, any>;
  category: string;
  confidence: number;
  top_factors: any[] | null;
  predicted_at: string;
}

export const getHistory = async (params?: {
  skip?: number;
  limit?: number;
  search?: string;
  category?: string;
  feature_set?: string;
  start_date?: string;
  end_date?: string;
}): Promise<PredictionHistoryItem[]> => {
  const res = await apiClient.get<PredictionHistoryItem[]>("/api/history/", { params });
  return res.data;
};

export interface PredictionDetail extends PredictionHistoryItem {
  shap_values?: Record<string, number> | null;
  explanation?: XAIExplanation | null;
  recommendations?: RecommendationItem[] | null;
}

export const getPredictionDetail = async (predictionId: string): Promise<PredictionDetail> => {
  const res = await apiClient.get<PredictionDetail>(`/api/history/${predictionId}`);
  return res.data;
};

export const getStudentProgress = async (studentIdOrCode: string): Promise<PredictionHistoryItem[]> => {
  const res = await apiClient.get<PredictionHistoryItem[]>(`/api/history/student/${encodeURIComponent(studentIdOrCode)}`);
  return res.data;
};

export const deleteHistory = async (predictionId: string): Promise<void> => {
  await apiClient.delete(`/api/history/${predictionId}`);
};

// ── Analytics ─────────────────────────────────────────────────────────────────
export interface ClassAnalytics {
  total_predictions: number;
  at_risk_count: number;
  needs_improvement_count: number;
  performing_well_count: number;
  at_risk_pct: number;
  needs_improvement_pct: number;
  performing_well_pct: number;
  avg_confidence: number;
}

export interface AtRiskStudent {
  prediction_id: string;
  student_id: string | null;
  student_code?: string | null;
  category: string;
  confidence: number;
  top_factors: any[] | null;
  predicted_at: string;
}

export interface TrendPoint {
  date: string;
  category: string;
  count: number;
}

export interface PerClassMetric {
  precision: number;
  recall: number;
  f1: number;
  support: number;
}

export interface CVSummaryItem {
  model: string;
  cv_accuracy: number;
  cv_accuracy_std: number;
  cv_f1_macro: number;
  cv_f1_macro_std: number;
  cv_at_risk_recall: number;
  cv_at_risk_recall_std: number;
}

export interface ModelMetrics {
  feature_set: string;
  best_model: string;
  accuracy: number;
  macro_f1: number;
  at_risk_recall: number;
  per_class?: Record<string, PerClassMetric> | null;
  confusion_matrix?: number[][] | null;
  cv_summary?: CVSummaryItem[] | null;
}

export const getClassAnalytics = async (): Promise<ClassAnalytics> => {
  const res = await apiClient.get<ClassAnalytics>("/api/analytics/class");
  return res.data;
};

export const getAtRiskStudents = async (limit = 50, category?: string): Promise<AtRiskStudent[]> => {
  const params: Record<string, any> = { limit };
  if (category) params.category = category;
  const res = await apiClient.get<AtRiskStudent[]>("/api/analytics/at-risk", { params });
  return res.data;
};

export const getTrends = async (): Promise<TrendPoint[]> => {
  const res = await apiClient.get<TrendPoint[]>("/api/analytics/trends");
  return res.data;
};

export const getModelMetrics = async (): Promise<ModelMetrics[]> => {
  const res = await apiClient.get<ModelMetrics[]>("/api/analytics/model-metrics");
  return res.data;
};

export interface CohortItem {
  cohort_name: string;
  total_students: number;
  at_risk_count: number;
  needs_improvement_count: number;
  performing_well_count: number;
  at_risk_pct: number;
  needs_improvement_pct: number;
  performing_well_pct: number;
  avg_confidence: number;
}

export interface CohortAnalyticsResponse {
  cohorts: CohortItem[];
  total_students: number;
}

export const getCohortAnalytics = async (): Promise<CohortAnalyticsResponse> => {
  const res = await apiClient.get<CohortAnalyticsResponse>("/api/analytics/cohorts");
  return res.data;
};

// ── Recommendations ───────────────────────────────────────────────────────────
export interface RecommendationItem {
  priority: string;
  category: string;
  title: string;
  description: string;
  action: string;
  area?: string;
  tip?: string;
  completed?: boolean;
  completed_at?: string | null;
  completed_by?: string | null;
}

export interface RecommendationResponse {
  prediction_id: string;
  student_category: string;
  recommendations: RecommendationItem[];
  generated_at: string;
}

export const getRecommendations = async (predictionId: string): Promise<RecommendationResponse> => {
  const res = await apiClient.get<RecommendationResponse>(`/api/recommend/${predictionId}`);
  return res.data;
};

export const toggleRecommendation = async (
  predictionId: string,
  itemIdx: number
): Promise<RecommendationResponse> => {
  const res = await apiClient.patch<RecommendationResponse>(
    `/api/recommend/${predictionId}/toggle/${itemIdx}`
  );
  return res.data;
};

// ── What-If Simulator ─────────────────────────────────────────────────────────
export interface WhatIfRequest {
  base_prediction_id?: string;
  feature_set?: "early" | "mid";
  student_inputs?: Record<string, any>;
  overrides: Record<string, any>;
}

export interface WhatIfPredictionSnapshot {
  inputs: Record<string, any>;
  category: string;
  confidence: number;
  top_factors?: any[];
}

export interface WhatIfResponse {
  original: WhatIfPredictionSnapshot;
  simulated: WhatIfPredictionSnapshot;
  confidence_delta?: number;
  risk_change?: "improved" | "worsened" | "unchanged" | string;
  risk_direction?: "improved" | "worsened" | "unchanged" | string;
  changed_inputs?: Record<string, any>;
  outcome_changed?: boolean;
  feature_set?: string;
  model_name?: string;
}

export const simulateWhatIf = async (body: WhatIfRequest): Promise<WhatIfResponse> => {
  const res = await apiClient.post<WhatIfResponse>("/api/simulate/what-if", body);
  return res.data;
};

// ── PDF Export ────────────────────────────────────────────────────────────────
export const downloadStudentPdf = async (studentIdOrCode: string): Promise<Blob> => {
  const res = await apiClient.get<Blob>(
    `/api/reports/export/pdf/${encodeURIComponent(studentIdOrCode)}`,
    { responseType: "blob" }
  );
  return res.data;
};

export const downloadPredictionPdf = async (predictionId: string): Promise<Blob> => {
  const res = await apiClient.get<Blob>(
    `/api/reports/export/pdf/prediction/${encodeURIComponent(predictionId)}`,
    { responseType: "blob" }
  );
  return res.data;
};
