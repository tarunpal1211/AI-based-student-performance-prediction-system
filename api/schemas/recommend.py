"""
api/schemas/recommend.py
------------------------
Pydantic schemas for recommendation and simulation endpoints.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class RecommendationItem(BaseModel):
    id: Optional[str] = None
    priority: str
    category: str
    title: str
    description: str
    action: str
    completed: bool = False
    completed_at: Optional[str] = None
    completed_by: Optional[str] = None


class RecommendationResponse(BaseModel):
    prediction_id: UUID
    student_category: str
    recommendations: list[RecommendationItem]
    generated_at: datetime


class WhatIfRequest(BaseModel):
    base_prediction_id: Optional[UUID] = None
    feature_set: Optional[str] = "early"
    student_inputs: Optional[dict] = None
    overrides: dict


class WhatIfResponse(BaseModel):
    original: dict
    simulated: dict
    changed_inputs: dict
    outcome_changed: bool
    risk_change: Optional[str] = None
