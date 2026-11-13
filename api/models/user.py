"""
api/models/user.py
------------------
User ORM model and role enum.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, GUID, TimestampMixin


class UserRole(str, enum.Enum):
    admin = "admin"
    teacher = "teacher"
    student = "student"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="userrole"), nullable=False, default=UserRole.teacher
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    students: Mapped[list["Student"]] = relationship(
        "Student", back_populates="created_by_user", lazy="select"
    )
    predictions: Mapped[list["Prediction"]] = relationship(
        "Prediction", back_populates="creator", lazy="select"
    )
    batch_jobs: Mapped[list["BatchJob"]] = relationship(
        "BatchJob", back_populates="creator", lazy="select"
    )
