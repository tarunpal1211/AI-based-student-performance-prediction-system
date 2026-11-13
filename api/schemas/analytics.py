"""
api/schemas/analytics.py
------------------------
Pydantic schemas for analytics and dashboard endpoints.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel


class ClassAnalytics(BaseModel):
    total_predictions: int
    at_risk_count: int
    needs_improvement_count: int
    performing_well_count: int
    at_risk_pct: float
    needs_improvement_pct: float
    performing_well_pct: float
    avg_confidence: float


class AtRiskStudent(BaseModel):
    prediction_id: str
    student_id: Optional[str] = None
    student_code: Optional[str] = None
    category: str
    confidence: float
    top_factors: Optional[list[Any]] = None
    predicted_at: str


class ModelMetrics(BaseModel):
    feature_set: str
    best_model: str
    accuracy: float
    macro_f1: float
    at_risk_recall: float
    per_class: Optional[dict[str, Any]] = None
    confusion_matrix: Optional[list[list[int]]] = None
    cv_summary: Optional[list[dict[str, Any]]] = None


class TrendPoint(BaseModel):
    date: str
    category: str
    count: int


class CohortItem(BaseModel):
    cohort_name: str
    total_students: int
    at_risk_count: int
    needs_improvement_count: int
    performing_well_count: int
    at_risk_pct: float
    needs_improvement_pct: float
    performing_well_pct: float
    avg_confidence: float


class CohortAnalyticsResponse(BaseModel):
    cohorts: list[CohortItem]
    total_students: int
