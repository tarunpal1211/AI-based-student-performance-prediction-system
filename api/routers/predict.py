"""
api/routers/predict.py
----------------------
Prediction endpoints:
  POST /api/predict/single          Single-student prediction
  POST /api/predict/upload-validate Parse and validate uploaded CSV/Excel
  POST /api/predict/batch-process   Execute batch ML inference on confirmed records
  GET  /api/predict/template        Download sample CSV/Excel template
  POST /api/predict/export          Export batch prediction results to CSV/Excel
  POST /api/predict/batch           Legacy CSV batch upload -> job record
  GET  /api/predict/batch/{job_id}  Poll batch job / get results
"""

from __future__ import annotations

import io
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_session
from api.dependencies import require_role
from api.models.prediction import BatchJob, Prediction
from api.models.recommendation import Recommendation
from api.models.student import Student
from api.models.user import User, UserRole
from api.schemas.predict import (
    BatchExportRequest,
    BatchJobDetail,
    BatchJobResponse,
    BatchProcessRequest,
    BatchProcessResponse,
    BatchStudentResult,
    PredictionResponse,
    SinglePredictRequest,
    UploadValidateResponse,
)
from src.explain import explain_prediction, get_shap_values
from src.predict import predict_batch, predict_one
from src.recommend import generate_recommendations
from src.validate import (
    make_sample_template,
    validate_csv,
    validate_student_records,
)

router = APIRouter()


def _get_model(request: Request, feature_set: str):
    """Retrieve a loaded model from app state, or raise 503."""
    model = getattr(request.app.state, "models", {}).get(feature_set)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Model '{feature_set}' is not loaded. "
                "Run 'python src/train.py' then restart the server."
            ),
        )
    return model


async def _resolve_student_uuid(
    db: AsyncSession, student_id_str: str | None, user_id: uuid.UUID
) -> uuid.UUID | None:
    """Find or create a Student record to maintain foreign key integrity."""
    if not student_id_str or not str(student_id_str).strip():
        return None
    code = str(student_id_str).strip()

    # Check if string is already a UUID
    try:
        p_uuid = uuid.UUID(code)
        s = await db.get(Student, p_uuid)
        if s is not None:
            return s.id
    except ValueError:
        pass

    # Search by student_code
    stmt = select(Student).where(Student.student_code == code)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing is not None:
        return existing.id

    # Create new student entry
    new_student = Student(
        student_code=code,
        name=code,
        created_by=user_id,
    )
    db.add(new_student)
    await db.flush()
    return new_student.id


def _sanitize_cell(val):
    """Prevent CSV/Excel formula injection (CWE-1236)."""
    if val is None:
        return ""
    if isinstance(val, (int, float, bool)):
        return val
    s = str(val).strip()
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


# ---------------------------------------------------------------------------
# Single Prediction
# ---------------------------------------------------------------------------

@router.post(
    "/single",
    response_model=PredictionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Predict a single student's performance",
)
async def predict_single(
    body: SinglePredictRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.teacher, UserRole.admin)),
):
    model = _get_model(request, body.feature_set)

    input_dict = {
        "absences": body.absences,
        "G1": body.G1,
        "failures": body.failures,
        "studytime": body.studytime,
        "assignment_rate": body.assignment_rate if body.assignment_rate is not None else 75,
        "assessment_trend": body.assessment_trend if body.assessment_trend is not None else 0,
    }
    if body.feature_set == "mid":
        input_dict["G2"] = body.G2 if body.G2 is not None else 10

    result = predict_one(model, input_dict)

    input_df = pd.DataFrame([input_dict])
    shap_vals = get_shap_values(model, input_df)
    model_name = type(model[-1]).__name__

    explanation = explain_prediction(model, input_dict, result["category"], result["confidence"])

    resolved_student_id = await _resolve_student_uuid(db, body.student_id, current_user.id)
    if body.student_id:
        input_dict["student_id"] = str(body.student_id)

    prediction = Prediction(
        student_id=resolved_student_id,
        created_by=current_user.id,
        feature_set=body.feature_set,
        model_name=model_name,
        input_features=input_dict,
        category=result["category"],
        confidence=result["confidence"],
        shap_values=explanation,
        top_factors=result["factors"],
    )
    db.add(prediction)
    await db.commit()
    await db.refresh(prediction)

    # Pre-generate recommendations
    recs = generate_recommendations(result["category"], input_dict)
    rec_obj = Recommendation(
        prediction_id=prediction.id,
        recommendations=recs,
    )
    db.add(rec_obj)
    await db.commit()

    return PredictionResponse(
        id=prediction.id,
        category=prediction.category,
        confidence=prediction.confidence,
        top_factors=prediction.top_factors or [],
        shap_values=shap_vals or None,
        explanation=explanation,
        feature_set=prediction.feature_set,
        model_name=prediction.model_name,
        predicted_at=prediction.created_at,
    )


# ---------------------------------------------------------------------------
# Bulk Upload Validation Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/upload-validate",
    response_model=UploadValidateResponse,
    summary="Validate uploaded student dataset file (CSV/Excel) and preview rows",
)
async def upload_validate_dataset(
    feature_set: str = Form(default="early"),
    column_mapping: Optional[str] = Form(default=None),
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(UserRole.teacher, UserRole.admin)),
):
    filename = (file.filename or "").lower()
    valid_exts = (".csv", ".xlsx", ".xls")
    if not any(filename.endswith(ext) for ext in valid_exts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a CSV (.csv) or Excel (.xlsx, .xls) file.",
        )

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 10 MB limit.",
        )

    try:
        if filename.endswith(".csv"):
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(contents), encoding="latin-1")
        elif filename.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")
        elif filename.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(contents), engine="xlrd")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse file: {str(exc)}",
        )

    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file contains no data rows.",
        )

    if len(df) > 5000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum batch limit of 5,000 rows (found {len(df)} rows).",
        )

    # Parse user mapping override if provided
    user_mapping: dict[str, str] | None = None
    if column_mapping:
        try:
            parsed = json.loads(column_mapping)
            if isinstance(parsed, dict):
                user_mapping = {str(k): str(v) for k, v in parsed.items()}
        except Exception:
            pass

    report = validate_student_records(
        df=df,
        feature_set=feature_set,
        column_mapping=user_mapping,
    )

    msg = f"Validated {report['total_rows']} student records: {report['valid_rows_count']} valid, {report['invalid_rows_count']} invalid."

    return UploadValidateResponse(
        total_rows=report["total_rows"],
        valid_rows_count=report["valid_rows_count"],
        invalid_rows_count=report["invalid_rows_count"],
        detected_columns=list(df.columns),
        column_mapping=report["column_mapping"],
        unmapped_required=report["unmapped_required"],
        duplicate_student_ids=report["duplicate_student_ids"],
        special_notes=report.get("special_notes", []),
        preview_rows=report["rows"],
        message=msg,
    )


# ---------------------------------------------------------------------------
# Batch Processing Execution
# ---------------------------------------------------------------------------

@router.post(
    "/batch-process",
    response_model=BatchProcessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute batch predictions on confirmed student records",
)
async def batch_process_records(
    body: BatchProcessRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.teacher, UserRole.admin)),
):
    if not body.records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No student records provided for batch processing.",
        )

    model = _get_model(request, body.feature_set)
    model_name = type(model[-1]).__name__

    results: list[BatchStudentResult] = []
    category_counts: dict[str, int] = {
        "At-Risk": 0,
        "Needs Improvement": 0,
        "Performing Well": 0,
    }
    total_confidence = 0.0

    batch_job = BatchJob(
        created_by=current_user.id,
        status="processing",
        total_rows=len(body.records),
        processed_rows=0,
    )
    db.add(batch_job)
    await db.flush()

    for rec in body.records:
        input_dict = {
            "absences": rec.absences,
            "G1": rec.G1,
            "failures": rec.failures,
            "studytime": rec.studytime,
            "assignment_rate": rec.assignment_rate if rec.assignment_rate is not None else 75,
            "assessment_trend": rec.assessment_trend if rec.assessment_trend is not None else 0,
        }
        if body.feature_set == "mid":
            input_dict["G2"] = rec.G2 if rec.G2 is not None else 10

        pred_res = predict_one(model, input_dict)
        cat = pred_res["category"]
        conf = float(pred_res["confidence"])

        category_counts[cat] = category_counts.get(cat, 0) + 1
        total_confidence += conf

        s_id = rec.student_id or f"R23EF{rec.row_index + 1:03d}"
        resolved_s_id = await _resolve_student_uuid(db, s_id, current_user.id)

        input_with_id = dict(input_dict)
        input_with_id["student_id"] = s_id

        pred_record = Prediction(
            student_id=resolved_s_id,
            created_by=current_user.id,
            feature_set=body.feature_set,
            model_name=model_name,
            input_features=input_with_id,
            category=cat,
            confidence=conf,
            top_factors=pred_res["factors"],
        )
        db.add(pred_record)
        await db.flush()

        recs = generate_recommendations(cat, input_with_id)
        rec_record = Recommendation(
            prediction_id=pred_record.id,
            recommendations=recs,
        )
        db.add(rec_record)

        results.append(
            BatchStudentResult(
                row_index=rec.row_index,
                student_id=s_id,
                prediction_id=str(pred_record.id),
                feature_set=body.feature_set,
                model_name=model_name,
                category=cat,
                confidence=conf,
                top_factors=pred_res["factors"],
                inputs=input_with_id,
                recommendations=recs,
            )
        )

    processed_count = len(results)
    batch_job.status = "done"
    batch_job.processed_rows = processed_count
    batch_job.completed_at = datetime.now(timezone.utc)
    batch_job.result_data = [r.model_dump() for r in results]

    await db.commit()

    total_count = max(processed_count, 1)
    percentages = {
        k: round((v / total_count) * 100, 1) for k, v in category_counts.items()
    }
    avg_conf = round(total_confidence / total_count, 3)

    return BatchProcessResponse(
        job_id=str(batch_job.id),
        total_rows=len(body.records),
        processed_rows=processed_count,
        failed_rows=len(body.records) - processed_count,
        category_distribution=category_counts,
        category_percentages=percentages,
        avg_confidence=avg_conf,
        results=results,
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Template Download Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/template",
    summary="Download sample CSV or Excel template for student bulk upload",
)
async def download_template(
    format: str = Query(default="csv", pattern="^(csv|xlsx)$"),
    feature_set: str = Query(default="early", pattern="^(early|mid)$"),
):
    content_bytes, filename, media_type = make_sample_template(
        feature_set=feature_set, file_format=format
    )
    return StreamingResponse(
        io.BytesIO(content_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Batch Results Export Endpoint (CSV / Excel)
# ---------------------------------------------------------------------------

@router.post(
    "/export",
    summary="Export batch prediction results to CSV or Excel (.xlsx)",
)
async def export_batch_results(
    body: BatchExportRequest,
    current_user: User = Depends(require_role(UserRole.teacher, UserRole.admin)),
):
    if not body.results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No prediction results provided for export.",
        )

    rows = []
    for item in body.results:
        inputs = item.get("inputs") or {}
        recs = item.get("recommendations") or []
        rec_summary = " | ".join([f"[{r.get('priority', '').upper()}] {r.get('title', '')}: {r.get('action', '')}" for r in recs])

        row = {
            "Student ID": _sanitize_cell(item.get("student_id")),
            "Predicted Outcome": _sanitize_cell(item.get("category")),
            "Confidence": f"{float(item.get('confidence', 0)):.1%}",
            "Model": _sanitize_cell(item.get("model_name")),
            "Feature Set": _sanitize_cell(item.get("feature_set")),
            "G1": _sanitize_cell(inputs.get("G1")),
            "Absences": _sanitize_cell(inputs.get("absences")),
            "Study Time": _sanitize_cell(inputs.get("studytime")),
            "Failures": _sanitize_cell(inputs.get("failures")),
            "Assignment Rate (%)": _sanitize_cell(inputs.get("assignment_rate")),
            "Assessment Trend": _sanitize_cell(inputs.get("assessment_trend")),
        }
        if body.feature_set == "mid" or "G2" in inputs:
            row["G2"] = _sanitize_cell(inputs.get("G2"))

        row["Top Contributing Factors"] = _sanitize_cell(" | ".join(item.get("top_factors") or []))
        row["AI Recommendations"] = _sanitize_cell(rec_summary)
        rows.append(row)

    export_df = pd.DataFrame(rows)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if body.format == "xlsx":
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False, sheet_name="Batch Predictions")
        bio.seek(0)
        return StreamingResponse(
            bio,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="gradematrix_predictions_{timestamp}.xlsx"'},
        )
    else:
        output = io.StringIO()
        export_df.to_csv(output, index=False)
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="gradematrix_predictions_{timestamp}.csv"'},
        )


# ---------------------------------------------------------------------------
# Legacy CSV Batch Upload
# ---------------------------------------------------------------------------

@router.post(
    "/batch",
    response_model=BatchJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Legacy batch predict via CSV upload",
)
async def predict_batch_upload(
    request: Request,
    feature_set: str = "early",
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.teacher, UserRole.admin)),
):
    if not (file.filename or "").endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    contents = await file.read()
    try:
        raw_df = pd.read_csv(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}")

    cleaned_df, errors = validate_csv(raw_df, feature_set=feature_set)

    if cleaned_df is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": errors},
        )

    model = _get_model(request, feature_set)
    results_df = predict_batch(model, cleaned_df)

    job = BatchJob(
        created_by=current_user.id,
        status="done",
        total_rows=len(raw_df),
        processed_rows=len(results_df),
        result_data=results_df.to_dict(orient="records"),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    warning = f" {len(errors)} validation issue(s)." if errors else ""
    return BatchJobResponse(
        job_id=job.id,
        status=job.status,
        total_rows=job.total_rows,
        processed_rows=job.processed_rows,
        message=f"Batch complete.{warning}",
    )


@router.get(
    "/batch/{job_id}",
    response_model=BatchJobDetail,
    summary="Get batch job status and results",
)
async def get_batch_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.teacher, UserRole.admin)),
):
    job = await db.get(BatchJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Batch job not found.")

    if job.created_by != current_user.id:
        raise HTTPException(
            status_code=403, detail="Access denied. This batch job was created by another account."
        )

    return BatchJobDetail(
        job_id=job.id,
        status=job.status,
        total_rows=job.total_rows,
        processed_rows=job.processed_rows,
        message=f"Job {job.status}.",
        results=job.result_data,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )

