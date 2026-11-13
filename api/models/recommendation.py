"""
api/models/recommendation.py
-----------------------------
Recommendation ORM model (1-to-1 with Prediction).
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, GUID, TimestampMixin


class Recommendation(Base, TimestampMixin):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    prediction_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("predictions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    recommendations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    prediction: Mapped["Prediction"] = relationship(
        "Prediction", back_populates="recommendation"
    )
