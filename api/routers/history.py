"""
api/routers/history.py
----------------------
Prediction history endpoints:
  GET    /api/history/                             List (paginated, filtered, search)
  GET    /api/history/{prediction_id}              Prediction detail + SHAP + XAI
  GET    /api/history/student/{student_id_or_code} All predictions for a student (trend)
  DELETE /api/history/{prediction_id}              Delete (admin only)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, func, or_, select, String
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_session
from api.dependencies import get_current_user, require_role
from api.models.prediction import Prediction
from api.models.recommendation import Recommendation
from api.models.student import Student
from api.models.user import User, UserRole
from api.schemas.history import PredictionDetail, PredictionHistoryItem
from src.explain import explain_prediction

router = APIRouter()


def _to_item(p: Prediction) -> PredictionHistoryItem:
    st_code = p.student.student_code if p.student is not None else None
    return PredictionHistoryItem(
        id=p.id,
        student_id=p.student_id,
        student_code=st_code,
        feature_set=p.feature_set,
        model_name=p.model_name,
        input_features=p.input_features or {},
        category=p.category,
        confidence=p.confidence,
        top_factors=p.top_factors,
        predicted_at=p.created_at,
    )


@router.get(
    "/",
    response_model=list[PredictionHistoryItem],
    summary="List prediction history with search and filters",
)
async def list_predictions(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=50, ge=1, le=200, description="Max records to return"),
    search: Optional[str] = Query(default=None, description="Search by student code, name or ID"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    feature_set: Optional[str] = Query(default=None, description="Filter by feature_set"),
    start_date: Optional[str] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.teacher, UserRole.admin)),
):
    query = (
        select(Prediction)
        .outerjoin(Student, Prediction.student_id == Student.id)
        .options(selectinload(Prediction.student))
        .order_by(desc(Prediction.created_at))
    )

    # Strict per-account isolation: users only see predictions created by their own account
    query = query.where(Prediction.created_by == current_user.id)
    if category:
        query = query.where(Prediction.category == category)
    if feature_set:
        query = query.where(Prediction.feature_set == feature_set)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Student.student_code.ilike(search_pattern),
                Student.name.ilike(search_pattern),
                func.cast(Prediction.id, String).ilike(search_pattern),
            )
        )

    if start_date:
        query = query.where(func.substr(func.cast(Prediction.created_at, String), 1, 10) >= start_date)
    if end_date:
        query = query.where(func.substr(func.cast(Prediction.created_at, String), 1, 10) <= end_date)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return [_to_item(p) for p in result.scalars().all()]


@router.get(
    "/student/{student_id_or_code}",
    response_model=list[PredictionHistoryItem],
    summary="All predictions for a student (progression view by UUID or code)",
)
async def get_student_predictions(
    student_id_or_code: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.teacher, UserRole.admin)),
):
    target_student_id = None
    try:
        target_student_id = uuid.UUID(student_id_or_code)
    except ValueError:
        pass

    query = (
        select(Prediction)
        .outerjoin(Student, Prediction.student_id == Student.id)
        .options(selectinload(Prediction.student))
        .order_by(Prediction.created_at.asc())
    )

    if target_student_id is not None:
        query = query.where(
            or_(
                Prediction.student_id == target_student_id,
                Student.student_code == student_id_or_code,
            )
        )
    else:
        query = query.where(Student.student_code == student_id_or_code)

    # Strict per-account isolation: users only see predictions created by their own account
    query = query.where(Prediction.created_by == current_user.id)

    result = await db.execute(query)
    return [_to_item(p) for p in result.scalars().all()]


@router.get(
    "/{prediction_id}",
    response_model=PredictionDetail,
    summary="Get one prediction with SHAP values and XAI explanation",
)
async def get_prediction(
    prediction_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Prediction)
        .options(
            selectinload(Prediction.student),
            selectinload(Prediction.recommendation),
        )
        .where(Prediction.id == prediction_id)
    )
    res = await db.execute(query)
    p = res.scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="Prediction not found.")

    if p.created_by != current_user.id:
        raise HTTPException(
            status_code=403, detail="Access denied. This prediction belongs to another user account."
        )

    explanation = None
    try:
        model = getattr(request.app.state, "models", {}).get(p.feature_set)
        if model is not None:
            explanation = explain_prediction(
                model=model,
                input_dict=p.input_features,
                category=p.category,
                confidence=p.confidence,
            )
    except Exception:
        explanation = None

    st_code = p.student.student_code if p.student is not None else None

    return PredictionDetail(
        id=p.id,
        student_id=p.student_id,
        student_code=st_code,
        feature_set=p.feature_set,
        model_name=p.model_name,
        input_features=p.input_features or {},
        category=p.category,
        confidence=p.confidence,
        top_factors=p.top_factors,
        shap_values=p.shap_values,
        explanation=explanation,
        predicted_at=p.created_at,
    )


@router.delete(
    "/{prediction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a prediction (admin only)",
)
async def delete_prediction(
    prediction_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    p = await db.get(Prediction, prediction_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Prediction not found.")
    if p.created_by != current_user.id:
        raise HTTPException(
            status_code=403, detail="Access denied. You can only delete your own predictions."
        )
    await db.delete(p)
    await db.commit()
