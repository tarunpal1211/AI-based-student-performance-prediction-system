"""
api/routers/analytics.py
------------------------
Class analytics and dashboard endpoints:
  GET /api/analytics/class         Risk distribution
  GET /api/analytics/at-risk       At-Risk student list
  GET /api/analytics/trends        Prediction trends over time (Fixed SQLite date)
  GET /api/analytics/model-metrics Model training metrics & evaluation (admin)
  GET /api/analytics/cohorts       Cohort / Department / Section comparison
"""

from __future__ import annotations

import json
import os

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select, String
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_session
from api.dependencies import require_role
from api.models.prediction import Prediction
from api.models.student import Student
from api.models.user import User, UserRole
from api.schemas.analytics import (
    AtRiskStudent,
    ClassAnalytics,
    CohortAnalyticsResponse,
    CohortItem,
    ModelMetrics,
    TrendPoint,
)

router = APIRouter()


@router.get(
    "/class",
    response_model=ClassAnalytics,
    summary="Class-level performance distribution",
)
async def get_class_analytics(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.teacher, UserRole.admin)),
):
    count_q = (
        select(Prediction.category, func.count(Prediction.id).label("cnt"))
        .where(Prediction.created_by == current_user.id)
        .group_by(Prediction.category)
    )

    rows = (await db.execute(count_q)).all()
    counts = {row.category: row.cnt for row in rows}
    actual_total = sum(counts.values())
    total_for_div = max(actual_total, 1)

    at_risk = counts.get("At-Risk", 0)
    needs = counts.get("Needs Improvement", 0)
    well = counts.get("Performing Well", 0)

    conf_q = (
        select(func.avg(Prediction.confidence))
        .where(Prediction.created_by == current_user.id)
    )
    avg_conf: float = (await db.execute(conf_q)).scalar() or 0.0

    return ClassAnalytics(
        total_predictions=actual_total,
        at_risk_count=at_risk,
        needs_improvement_count=needs,
        performing_well_count=well,
        at_risk_pct=round(at_risk / total_for_div * 100, 1) if actual_total > 0 else 0.0,
        needs_improvement_pct=round(needs / total_for_div * 100, 1) if actual_total > 0 else 0.0,
        performing_well_pct=round(well / total_for_div * 100, 1) if actual_total > 0 else 0.0,
        avg_confidence=round(avg_conf, 3),
    )


@router.get(
    "/at-risk",
    response_model=list[AtRiskStudent],
    summary="List At-Risk or categorized students (dashboard)",
)
async def get_at_risk_students(
    limit: int = Query(default=50, ge=1, le=200),
    category: str | None = Query(
        default="At-Risk",
        description="Filter category: 'At-Risk', 'Needs Improvement', 'Performing Well', or 'all' for all",
    ),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.teacher, UserRole.admin)),
):
    query = (
        select(Prediction)
        .outerjoin(Student, Prediction.student_id == Student.id)
        .options(selectinload(Prediction.student))
        .where(Prediction.created_by == current_user.id)
        .order_by(desc(Prediction.created_at))
    )

    if category and category.lower() != "all":
        query = query.where(Prediction.category == category)

    query = query.limit(limit)

    result = await db.execute(query)
    predictions = result.scalars().all()

    return [
        AtRiskStudent(
            prediction_id=str(p.id),
            student_id=str(p.student_id) if p.student_id else None,
            student_code=p.student.student_code if p.student else None,
            category=p.category,
            confidence=p.confidence,
            top_factors=p.top_factors,
            predicted_at=p.created_at.isoformat(),
        )
        for p in predictions
    ]


@router.get(
    "/trends",
    response_model=list[TrendPoint],
    summary="Prediction trends over the last 90 days",
)
async def get_trends(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.teacher, UserRole.admin)),
):
    date_col = func.substr(func.cast(Prediction.created_at, String), 1, 10).label("date")
    query = (
        select(
            date_col,
            Prediction.category,
            func.count(Prediction.id).label("count"),
        )
        .where(Prediction.created_by == current_user.id)
        .group_by(date_col, Prediction.category)
        .order_by(desc(date_col))
        .limit(90 * 3)
    )

    result = await db.execute(query)
    return [
        TrendPoint(date=str(row.date), category=row.category, count=row.count)
        for row in result.all()
    ]


@router.get(
    "/model-metrics",
    response_model=list[ModelMetrics],
    summary="ML model training metrics and evaluation (admin only)",
)
async def get_model_metrics(
    current_user: User = Depends(require_role(UserRole.admin)),
):
    results: list[ModelMetrics] = []
    for feature_set, fname in [
        ("early", "models/early_metrics.json"),
        ("mid", "models/mid_metrics.json"),
    ]:
        if not os.path.exists(fname):
            continue
        with open(fname, "r", encoding="utf-8") as f:
            data = json.load(f)
        results.append(
            ModelMetrics(
                feature_set=feature_set,
                best_model=data.get("best_model", "Unknown"),
                accuracy=data.get("accuracy", 0.0),
                macro_f1=data.get("macro_f1", 0.0),
                at_risk_recall=data.get("at_risk_recall", 0.0),
                per_class=data.get("per_class"),
                confusion_matrix=data.get("confusion_matrix"),
                cv_summary=data.get("cv_summary"),
            )
        )
    if not results:
        raise HTTPException(
            status_code=404,
            detail="No metric files found. Run 'python src/train.py' first.",
        )
    return results


@router.get(
    "/cohorts",
    response_model=CohortAnalyticsResponse,
    summary="Cross-cohort and section comparative analytics",
)
async def get_cohort_analytics(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.teacher, UserRole.admin)),
):
    query = (
        select(Prediction, Student)
        .outerjoin(Student, Prediction.student_id == Student.id)
        .where(Prediction.created_by == current_user.id)
        .order_by(desc(Prediction.created_at))
    )

    result = await db.execute(query)
    rows = result.all()

    cohort_data: dict[str, dict] = {}
    total_count = 0

    for pred, student in rows:
        total_count += 1
        name = None
        if student and student.class_section:
            name = student.class_section
        elif student and student.student_code:
            # Group by prefix of student code (e.g. R23EF -> Section R23EF)
            code_parts = student.student_code.split("-")[0]
            if len(code_parts) > 4:
                name = f"Cohort {code_parts[:5]}"
            else:
                name = f"Cohort {code_parts}"
        else:
            name = "General Assessment Cohort"

        if name not in cohort_data:
            cohort_data[name] = {
                "cohort_name": name,
                "total": 0,
                "at_risk": 0,
                "needs": 0,
                "well": 0,
                "confidence_sum": 0.0,
            }

        c = cohort_data[name]
        c["total"] += 1
        c["confidence_sum"] += pred.confidence
        if pred.category == "At-Risk":
            c["at_risk"] += 1
        elif pred.category == "Needs Improvement":
            c["needs"] += 1
        else:
            c["well"] += 1

    cohorts_list: list[CohortItem] = []
    for c in cohort_data.values():
        tot = max(c["total"], 1)
        cohorts_list.append(
            CohortItem(
                cohort_name=c["cohort_name"],
                total_students=c["total"],
                at_risk_count=c["at_risk"],
                needs_improvement_count=c["needs"],
                performing_well_count=c["well"],
                at_risk_pct=round(c["at_risk"] / tot * 100, 1),
                needs_improvement_pct=round(c["needs"] / tot * 100, 1),
                performing_well_pct=round(c["well"] / tot * 100, 1),
                avg_confidence=round(c["confidence_sum"] / tot, 3),
            )
        )

    cohorts_list.sort(key=lambda x: x.total_students, reverse=True)

    return CohortAnalyticsResponse(
        cohorts=cohorts_list,
        total_students=total_count,
    )
