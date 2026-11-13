"""
api/models/prediction.py
------------------------
Prediction and BatchJob ORM models.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, GUID, TimestampMixin


class Prediction(Base, TimestampMixin):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("students.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False
    )
    feature_set: Mapped[str] = mapped_column(String(10), nullable=False, default="early")
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_features: Mapped[dict] = mapped_column(JSON, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    shap_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    top_factors: Mapped[list | None] = mapped_column(JSON, nullable=True)

    student: Mapped["Student | None"] = relationship(
        "Student", back_populates="predictions"
    )
    creator: Mapped["User"] = relationship(
        "User", back_populates="predictions"
    )
    recommendation: Mapped["Recommendation | None"] = relationship(
        "Recommendation", back_populates="prediction", uselist=False
    )


class BatchJob(Base, TimestampMixin):
    __tablename__ = "batch_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_data: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    creator: Mapped["User"] = relationship(
        "User", back_populates="batch_jobs"
    )
