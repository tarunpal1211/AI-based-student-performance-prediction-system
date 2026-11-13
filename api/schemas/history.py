"""
api/schemas/history.py
----------------------
Pydantic schemas for prediction history endpoints.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Any, Optional

from pydantic import BaseModel


class PredictionHistoryItem(BaseModel):
    id: UUID
    student_id: Optional[UUID] = None
    student_code: Optional[str] = None
    feature_set: str
    model_name: str
    input_features: dict
    category: str
    confidence: float
    top_factors: Optional[list[Any]] = None
    predicted_at: datetime


class PredictionDetail(PredictionHistoryItem):
    shap_values: Optional[dict] = None
    explanation: Optional[dict] = None
