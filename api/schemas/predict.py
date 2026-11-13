"""
api/schemas/predict.py
----------------------
Pydantic request / response schemas for prediction endpoints.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class SinglePredictRequest(BaseModel):
    student_id: Optional[str] = None
    feature_set: str = Field(default="early", pattern="^(early|mid)$")
    absences: int = Field(ge=0, le=93, description="Number of school absences (0-93)")
    G1: int = Field(ge=0, le=20, description="First period grade (0-20)")
    failures: int = Field(ge=0, le=4, description="Past class failures (0-4)")
    studytime: int = Field(ge=1, le=4, description="Weekly study time coded 1-4")
    assignment_rate: Optional[int] = Field(
        default=75, ge=0, le=100, description="Assignment completion rate (0-100%)"
    )
    assessment_trend: Optional[int] = Field(
        default=0, ge=-1, le=1, description="Recent assessment trend (-1=Declining, 0=Stable, 1=Improving)"
    )
    G2: Optional[int] = Field(
        default=None, ge=0, le=20, description="Second period grade (0-20), required for mid feature set"
    )

    @model_validator(mode="after")
    def g2_required_for_mid(self) -> "SinglePredictRequest":
        if self.feature_set == "mid" and self.G2 is None:
            raise ValueError("G2 is required when feature_set is 'mid'.")
        return self


class PredictionResponse(BaseModel):
    id: UUID
    category: str
    confidence: float
    top_factors: list[Any] = []
    shap_values: Optional[dict] = None
    explanation: Optional[dict] = None
    feature_set: str
    model_name: str
    predicted_at: datetime


class BatchJobResponse(BaseModel):
    job_id: UUID
    status: str
    total_rows: int
    processed_rows: int
    message: str


class BatchJobDetail(BatchJobResponse):
    results: Optional[list[dict]] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class UploadValidateResponse(BaseModel):
    total_rows: int
    valid_rows_count: int
    invalid_rows_count: int
    detected_columns: list[str]
    column_mapping: dict[str, str]
    unmapped_required: list[str]
    duplicate_student_ids: list[str]
    special_notes: list[str] = []
    preview_rows: list[dict]
    message: str


class BatchStudentInput(BaseModel):
    row_index: int
    student_id: Optional[str] = None
    absences: int = Field(ge=0, le=93)
    G1: int = Field(ge=0, le=20)
    failures: int = Field(ge=0, le=4)
    studytime: int = Field(ge=1, le=4)
    G2: Optional[int] = Field(default=None, ge=0, le=20)
    assignment_rate: Optional[int] = Field(default=75, ge=0, le=100)
    assessment_trend: Optional[int] = Field(default=0, ge=-1, le=1)


class BatchProcessRequest(BaseModel):
    feature_set: str = Field(default="early", pattern="^(early|mid)$")
    records: list[BatchStudentInput]


class BatchStudentResult(BaseModel):
    row_index: int
    student_id: str
    prediction_id: str
    feature_set: str
    model_name: str
    category: str
    confidence: float
    top_factors: list[str]
    inputs: dict
    recommendations: list[dict]


class BatchProcessResponse(BaseModel):
    job_id: str
    total_rows: int
    processed_rows: int
    failed_rows: int
    category_distribution: dict[str, int]
    category_percentages: dict[str, float]
    avg_confidence: float
    results: list[BatchStudentResult]
    created_at: datetime


class BatchExportRequest(BaseModel):
    format: str = Field(pattern="^(csv|xlsx)$")
    feature_set: str = Field(default="early")
    results: list[dict]
