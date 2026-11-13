"""
api/routers/recommend.py
------------------------
Personalized recommendations endpoints:
  GET   /api/recommend/{prediction_id}              Get (or generate) recommendations
  PATCH /api/recommend/{prediction_id}/toggle/{idx} Toggle completion status of a recommendation item
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_session
from api.dependencies import get_current_user
from api.models.prediction import Prediction
from api.models.recommendation import Recommendation
from api.models.user import User, UserRole
from api.schemas.recommend import RecommendationItem, RecommendationResponse
from src.recommend import generate_recommendations

router = APIRouter()


@router.get(
    "/{prediction_id}",
    response_model=RecommendationResponse,
    summary="Get personalised recommendations for a prediction",
)
async def get_recommendations(
    prediction_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    prediction = await db.get(Prediction, prediction_id)
    if prediction is None:
        raise HTTPException(status_code=404, detail="Prediction not found.")

    if prediction.created_by != current_user.id:
        raise HTTPException(
            status_code=403, detail="Access denied. This prediction belongs to another account."
        )

    cached_q = select(Recommendation).where(
        Recommendation.prediction_id == prediction_id
    )
    existing = (await db.execute(cached_q)).scalar_one_or_none()

    if existing is not None:
        items = []
        for r in existing.recommendations:
            r_dict = dict(r)
            if "completed" not in r_dict:
                r_dict["completed"] = False
            items.append(RecommendationItem(**r_dict))
        return RecommendationResponse(
            prediction_id=prediction_id,
            student_category=prediction.category,
            recommendations=items,
            generated_at=existing.created_at,
        )

    recs = generate_recommendations(prediction.category, prediction.input_features)
    for r in recs:
        if "completed" not in r:
            r["completed"] = False

    rec_obj = Recommendation(
        prediction_id=prediction_id,
        recommendations=recs,
    )
    db.add(rec_obj)
    await db.commit()
    await db.refresh(rec_obj)

    return RecommendationResponse(
        prediction_id=prediction_id,
        student_category=prediction.category,
        recommendations=[RecommendationItem(**r) for r in recs],
        generated_at=rec_obj.created_at,
    )


@router.patch(
    "/{prediction_id}/toggle/{item_idx}",
    response_model=RecommendationResponse,
    summary="Toggle completion status of an intervention recommendation",
)
async def toggle_recommendation_status(
    prediction_id: uuid.UUID,
    item_idx: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    prediction = await db.get(Prediction, prediction_id)
    if prediction is None:
        raise HTTPException(status_code=404, detail="Prediction not found.")

    if prediction.created_by != current_user.id:
        raise HTTPException(
            status_code=403, detail="Access denied. This prediction belongs to another account."
        )

    cached_q = select(Recommendation).where(
        Recommendation.prediction_id == prediction_id
    )
    rec_obj = (await db.execute(cached_q)).scalar_one_or_none()

    if rec_obj is None:
        recs = generate_recommendations(prediction.category, prediction.input_features)
        rec_obj = Recommendation(prediction_id=prediction_id, recommendations=recs)
        db.add(rec_obj)
        await db.flush()

    recs_list = list(rec_obj.recommendations or [])
    if item_idx < 0 or item_idx >= len(recs_list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid recommendation item index {item_idx}.",
        )

    curr_item = dict(recs_list[item_idx])
    now_completed = not curr_item.get("completed", False)
    curr_item["completed"] = now_completed
    curr_item["completed_at"] = (
        datetime.now(timezone.utc).isoformat() if now_completed else None
    )
    curr_item["completed_by"] = current_user.email if now_completed else None
    recs_list[item_idx] = curr_item

    # Reassign to trigger SQLAlchemy JSON change detection
    rec_obj.recommendations = recs_list
    await db.commit()
    await db.refresh(rec_obj)

    return RecommendationResponse(
        prediction_id=prediction_id,
        student_category=prediction.category,
        recommendations=[RecommendationItem(**r) for r in recs_list],
        generated_at=rec_obj.created_at,
    )
