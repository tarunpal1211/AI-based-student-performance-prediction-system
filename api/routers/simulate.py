"""
api/routers/simulate.py
-----------------------
What-If simulation endpoint:
  POST /api/simulate/what-if  Change inputs -> compare predictions
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_session
from api.dependencies import require_role
from api.models.prediction import Prediction
from api.models.user import User, UserRole
from api.schemas.recommend import WhatIfRequest, WhatIfResponse
from src.predict import predict_one

router = APIRouter()

_RISK_RANK = {"At-Risk": 0, "Needs Improvement": 1, "Performing Well": 2}


@router.post(
    "/what-if",
    response_model=WhatIfResponse,
    summary="What-If academic simulation",
)
async def what_if_simulation(
    body: WhatIfRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.teacher, UserRole.admin)),
):
    feature_set = body.feature_set or "early"
    base_inputs: dict = {}
    orig_category: str = ""
    orig_confidence: float = 0.0
    orig_factors: list = []

    if body.base_prediction_id is not None:
        prediction = await db.get(Prediction, body.base_prediction_id)
        if prediction is None:
            raise HTTPException(status_code=404, detail="Base prediction not found.")

        if prediction.created_by != current_user.id:
            raise HTTPException(
                status_code=403, detail="Access denied. Base prediction belongs to another account."
            )

        feature_set = prediction.feature_set
        base_inputs = dict(prediction.input_features)
        orig_category = prediction.category
        orig_confidence = prediction.confidence
        orig_factors = prediction.top_factors or []
    elif body.student_inputs:
        base_inputs = dict(body.student_inputs)
        model = getattr(request.app.state, "models", {}).get(feature_set)
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Model '{feature_set}' is not loaded.",
            )
        base_res = predict_one(model, base_inputs)
        orig_category = base_res["category"]
        orig_confidence = base_res["confidence"]
        orig_factors = base_res["factors"]
    else:
        # Default baseline if neither was provided
        base_inputs = {
            "G1": 10,
            "absences": 8,
            "failures": 1,
            "studytime": 2,
            "assignment_rate": 75,
            "assessment_trend": 0,
        }
        if feature_set == "mid":
            base_inputs["G2"] = 10
        model = getattr(request.app.state, "models", {}).get(feature_set)
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Model '{feature_set}' is not loaded.",
            )
        base_res = predict_one(model, base_inputs)
        orig_category = base_res["category"]
        orig_confidence = base_res["confidence"]
        orig_factors = base_res["factors"]

    model = getattr(request.app.state, "models", {}).get(feature_set)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model '{feature_set}' is not loaded.",
        )

    simulated_input = {**base_inputs, **body.overrides}
    sim_result = predict_one(model, simulated_input)

    orig_rank = _RISK_RANK.get(orig_category, 1)
    sim_rank = _RISK_RANK.get(sim_result["category"], 1)
    if sim_rank > orig_rank:
        risk_change = "improved"
    elif sim_rank < orig_rank:
        risk_change = "worsened"
    else:
        risk_change = "unchanged"

    return WhatIfResponse(
        original={
            "inputs": base_inputs,
            "category": orig_category,
            "confidence": orig_confidence,
            "top_factors": orig_factors,
        },
        simulated={
            "inputs": simulated_input,
            "category": sim_result["category"],
            "confidence": sim_result["confidence"],
            "top_factors": sim_result["factors"],
        },
        changed_inputs=body.overrides,
        outcome_changed=orig_category != sim_result["category"],
        risk_change=risk_change,
    )
