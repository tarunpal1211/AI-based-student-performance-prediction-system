"""
api/routers/reports.py
----------------------
Report export endpoints:
  GET /api/reports/export/csv                       Download predictions as CSV
  GET /api/reports/export/excel                     Download predictions as Excel
  GET /api/reports/export/pdf/{student_id_or_code}  Student longitudinal PDF report
  GET /api/reports/export/pdf/prediction/{pred_id}  Individual prediction diagnostic PDF
"""

from __future__ import annotations

import io
import json
import uuid
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, or_, select, String
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_session
from api.dependencies import require_role
from api.models.prediction import Prediction
from api.models.recommendation import Recommendation
from api.models.student import Student
from api.models.user import User, UserRole
from src.explain import FEATURE_LABELS, explain_prediction
from src.recommend import generate_recommendations

router = APIRouter()


async def _predictions_to_df(
    db: AsyncSession, user: User
) -> pd.DataFrame:
    query = (
        select(Prediction)
        .outerjoin(Student, Prediction.student_id == Student.id)
        .options(selectinload(Prediction.student))
        .where(Prediction.created_by == user.id)
        .order_by(desc(Prediction.created_at))
    )

    result = await db.execute(query)
    rows = []
    for p in result.scalars().all():
        st_code = p.student.student_code if p.student else (str(p.student_id) if p.student_id else "")
        row = {
            "Prediction ID": str(p.id),
            "Student Code": st_code,
            "Category": p.category,
            "Confidence": f"{p.confidence:.1%}",
            "Feature Set": p.feature_set,
            "Model": p.model_name,
            "Predicted At": p.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for k, v in (p.input_features or {}).items():
            row[f"input_{k}"] = v
        rows.append(row)
    return pd.DataFrame(rows)


@router.get("/export/csv", summary="Download predictions as CSV")
async def export_csv(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.teacher, UserRole.admin)),
):
    df = await _predictions_to_df(db, current_user)
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=gradematrix_predictions.csv"},
    )


@router.get("/export/excel", summary="Download predictions as Excel (.xlsx)")
async def export_excel(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.teacher, UserRole.admin)),
):
    df = await _predictions_to_df(db, current_user)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Predictions")
    output.seek(0)
    return StreamingResponse(
        iter([output.read()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=gradematrix_predictions.xlsx"},
    )


def _build_diagnostic_pdf(
    student_code: str,
    predictions: list[Prediction],
    user_email: str,
) -> bytes:
    """Build a publication-quality GradeMatrix Academic Diagnostic PDF report."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    header_title_style = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1E293B"),
    )
    header_subtitle_style = ParagraphStyle(
        "HeaderSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#64748B"),
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#312E81"),
        spaceBefore=8,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
    )
    badge_style = ParagraphStyle(
        "BadgeText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        alignment=1,  # Center
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1E293B"),
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
    )

    story = []

    # 1. Header Banner
    header_table_data = [
        [
            Paragraph("GRADEMATRIX AI — ACADEMIC DECISION SUPPORT", header_title_style),
            Paragraph(
                f"<b>Generated:</b> {datetime.now().strftime('%b %d, %Y %H:%M')}<br/>"
                f"<b>Assessor:</b> {user_email}<br/>"
                "<b>System:</b> GradeMatrix v2.0 Enterprise",
                ParagraphStyle("HeaderMeta", parent=body_style, fontSize=8, leading=11, alignment=2),
            ),
        ]
    ]
    header_table = Table(header_table_data, colWidths=[360, 180])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(header_table)
    story.append(
        Paragraph(
            "Official Student Performance Diagnostic & Early Warning Intervention Report",
            header_subtitle_style,
        )
    )
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#4F46E5"), spaceAfter=10))

    if not predictions:
        story.append(Paragraph("No prediction records found for this student.", body_style))
        doc.build(story)
        buffer.seek(0)
        return buffer.read()

    latest = predictions[0]
    category = latest.category
    confidence = latest.confidence
    feature_set = latest.feature_set.upper()
    inputs = latest.input_features or {}

    # Category Colors
    if category == "At-Risk":
        cat_bg = colors.HexColor("#FEF2F2")
        cat_border = colors.HexColor("#EF4444")
        cat_text = colors.HexColor("#B91C1C")
    elif category == "Needs Improvement":
        cat_bg = colors.HexColor("#FFFBEB")
        cat_border = colors.HexColor("#F59E0B")
        cat_text = colors.HexColor("#B45309")
    else:
        cat_bg = colors.HexColor("#ECFDF5")
        cat_border = colors.HexColor("#10B981")
        cat_text = colors.HexColor("#047857")

    # 2. Executive Diagnostic Card
    def _format_confidence_display(conf: float) -> str:
        # Cap at 99.5% to avoid displaying unrealistic 100.0% certainty in empirical machine learning diagnostics
        if conf >= 0.995:
            return "99.5% (High Statistical Certainty)"
        elif conf <= 0.005:
            return "< 1.0%"
        return f"{conf:.1%}"

    badge_p = Paragraph(f"<font color='{cat_text.hexval()}'>{category.upper()}</font>", badge_style)
    sub_badge = Paragraph(
        f"<b>Assessment Phase:</b> {feature_set} Model ({latest.model_name}) &nbsp;|&nbsp; "
        f"<b>Model Confidence:</b> {_format_confidence_display(confidence)} &nbsp;|&nbsp; "
        f"<b>Student ID:</b> {student_code}",
        ParagraphStyle("SubBadge", parent=body_style, alignment=1, fontSize=8.5, leading=12),
    )
    conf_disclaimer = Paragraph(
        "<i>*Diagnostic probability estimation. Model confidence reflects historical training data pattern alignment and should not be treated as guaranteed certainty or deterministic outcome.</i>",
        ParagraphStyle("ConfDisclaimer", parent=body_style, fontSize=7, leading=9, textColor=colors.HexColor("#64748B"), alignment=1),
    )

    diag_box = Table([[badge_p], [sub_badge], [conf_disclaimer]], colWidths=[540])
    diag_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), cat_bg),
                ("BOX", (0, 0), (-1, -1), 1.5, cat_border),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(diag_box)
    story.append(Spacer(1, 10))

    # 3. Academic Input Summary
    story.append(Paragraph("1. Academic Input Breakdown & Student Metrics", section_heading))
    g1 = inputs.get("G1", "N/A")
    g2 = inputs.get("G2", "N/A") if feature_set == "MID" else "Not Assessed (Early Phase)"
    absences = inputs.get("absences", 0)
    failures = inputs.get("failures", 0)
    studytime = inputs.get("studytime", 0)
    assignment_rate = inputs.get("assignment_rate", "N/A")

    def _grade_status(g):
        if not isinstance(g, (int, float)):
            return "Not Assessed"
        if g <= 5:
            return "Very Bad (0–5/20)"
        elif g <= 10:
            return "Bad (6–10/20)"
        elif g <= 15:
            return "Average (11–15/20)"
        else:
            return "Strong (16–20/20)"

    def _studytime_info(st):
        # Aligned with official UCI Student Benchmark Scale
        try:
            st_val = int(st)
        except (ValueError, TypeError):
            return ("Not Assessed", "Level 3 (≥ 5–10 hrs/wk)", "Not Assessed")
        if st_val == 1:
            return ("Level 1 (< 2 hrs/week)", "Level 3 (≥ 5–10 hrs/wk)", "Critically Low (< 2 hrs)")
        elif st_val == 2:
            return ("Level 2 (2–5 hrs/week)", "Level 3 (≥ 5–10 hrs/wk)", "Below Benchmark (2–5 hrs)")
        elif st_val == 3:
            return ("Level 3 (5–10 hrs/week)", "Level 3 (≥ 5–10 hrs/wk)", "Satisfactory / On Target")
        else:
            return ("Level 4 (> 10 hrs/week)", "Level 3 (≥ 5–10 hrs/wk)", "Exemplary Effort (> 10 hrs)")

    st_val, st_standard, st_status = _studytime_info(studytime)
    abs_status = f"<font color='#B91C1C'><b>High Absenteeism ({absences}d)</b></font>" if absences > 5 else "Regular Attendance"

    input_data = [
        [
            Paragraph("<b>Metric</b>", table_cell_bold),
            Paragraph("<b>Value</b>", table_cell_bold),
            Paragraph("<b>Standard Criteria / Scale</b>", table_cell_bold),
            Paragraph("<b>Diagnostic Status</b>", table_cell_bold),
        ],
        [
            Paragraph("First Period Grade (G1)", table_cell),
            Paragraph(f"{g1} / 20", table_cell_bold),
            Paragraph("0-5: Very Bad | 6-10: Bad | 11-15: Avg | 16-20: Strong", table_cell),
            Paragraph(_grade_status(g1), table_cell_bold),
        ],
        [
            Paragraph("Second Period Grade (G2)", table_cell),
            Paragraph(f"{g2} / 20" if feature_set == "MID" else str(g2), table_cell_bold),
            Paragraph("0-5: Very Bad | 6-10: Bad | 11-15: Avg | 16-20: Strong", table_cell),
            Paragraph(_grade_status(g2) if feature_set == "MID" else "Baseline", table_cell_bold),
        ],
        [
            Paragraph("School Absences", table_cell),
            Paragraph(f"{absences} days", table_cell_bold),
            Paragraph("< 5 days per semester", table_cell),
            Paragraph(abs_status, table_cell),
        ],
        [
            Paragraph("Past Course Failures", table_cell),
            Paragraph(f"{failures}", table_cell_bold),
            Paragraph("0 failures", table_cell),
            Paragraph("At-Risk History" if failures > 0 else "Clean Record", table_cell),
        ],
        [
            Paragraph("Weekly Study Time", table_cell),
            Paragraph(st_val, table_cell_bold),
            Paragraph(st_standard, table_cell),
            Paragraph(st_status, table_cell_bold if ("Low" in st_status or "Below" in st_status) else table_cell),
        ],
    ]
    input_table = Table(input_data, colWidths=[150, 115, 150, 125])
    input_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(input_table)
    story.append(Spacer(1, 10))

    # 4. Explainable AI Analysis & Contributing Factors
    story.append(Paragraph("2. Explainable AI (XAI) Attribution & Contributing Factors", section_heading))
    xai_data = [
        [
            Paragraph("<b>Factor & Influence</b>", table_cell_bold),
            Paragraph("<b>Impact Direction</b>", table_cell_bold),
            Paragraph("<b>Observation & Evidence</b>", table_cell_bold),
        ]
    ]

    shap_data = None
    if latest.shap_values:
        if isinstance(latest.shap_values, str):
            try:
                shap_data = json.loads(latest.shap_values)
            except Exception:
                shap_data = None
        elif isinstance(latest.shap_values, dict):
            shap_data = latest.shap_values

    xai_rows = []
    seen_features = set()

    # Priority 1: Use directional SHAP contributions if available
    if shap_data and isinstance(shap_data.get("contributions"), list):
        prots = [c for c in shap_data["contributions"] if c.get("impact") == "positive" or c.get("direction") == "reduced_risk"]
        risks = [c for c in shap_data["contributions"] if c.get("impact") == "negative" or c.get("direction") == "increased_risk"]

        # Take top 2 protective drivers
        for p in prots[:2]:
            lbl = p.get("label", p.get("feature", "Factor"))
            xai_rows.append((lbl, "<font color='#047857'><b>Positive Contribution</b></font>", p.get("description", "")))
            seen_features.add(p.get("feature"))

        # Take top 2 risk drivers
        for r in risks[:2]:
            feat = r.get("feature")
            if feat not in seen_features:
                lbl = r.get("label", feat or "Factor")
                xai_rows.append((lbl, "<font color='#B91C1C'><b>Negative / Risk Factor</b></font>", r.get("description", "")))
                seen_features.add(feat)

    # Priority 2: Fall back to top_factors if empty
    if not xai_rows:
        top_factors = latest.top_factors or []
        for f in top_factors[:4]:
            if isinstance(f, dict):
                lbl = f.get("label", f.get("feature", "Factor"))
                is_pos = f.get("impact") == "positive" or f.get("direction") == "reduced_risk"
                dir_badge = "<font color='#047857'><b>Positive Contribution</b></font>" if is_pos else "<font color='#B91C1C'><b>Negative / Risk Factor</b></font>"
                desc_txt = f.get("description", str(f))
                seen_features.add(f.get("feature"))
            else:
                txt = str(f)
                lbl = txt.split("(")[0].strip()
                is_pos = any(w in txt.lower() for w in ["strong", "positive", "good", "steady", "satisfactory", "high homework", "zero prior", "clean"])
                dir_badge = "<font color='#047857'><b>Positive Contribution</b></font>" if is_pos else "<font color='#B91C1C'><b>Negative / Risk Factor</b></font>"
                desc_txt = txt
                if "absence" in txt.lower():
                    seen_features.add("absences")
            xai_rows.append((lbl, dir_badge, desc_txt))

    # Priority 3 (Attendance Guarantee): If student has > 5 absences, always highlight attendance risk
    if absences > 5 and "absences" not in seen_features and not any("absence" in r[0].lower() for r in xai_rows):
        xai_rows.append((
            "School Absences",
            "<font color='#B91C1C'><b>Negative / Risk Factor</b></font>",
            f"High absence count ({absences} days missed vs standard < 5 days) creates learning continuity vulnerability despite course scores.",
        ))

    if not xai_rows:
        xai_rows.append((
            "Course Performance",
            "<font color='#475569'><b>Baseline Factor</b></font>",
            "Student academic metrics align within class cohort distribution.",
        ))

    for lbl, dir_badge, desc_txt in xai_rows:
        xai_data.append(
            [
                Paragraph(f"<b>{lbl}</b>", table_cell),
                Paragraph(dir_badge, table_cell),
                Paragraph(desc_txt, table_cell),
            ]
        )

    xai_table = Table(xai_data, colWidths=[150, 130, 260])
    xai_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(xai_table)
    story.append(Spacer(1, 10))

    # 5. Personalized Improvement Action Plan
    story.append(Paragraph("3. Targeted Academic Interventions & Action Plan", section_heading))
    recs = generate_recommendations(category, inputs)
    rec_rows = [
        [
            Paragraph("<b>Priority</b>", table_cell_bold),
            Paragraph("<b>Category</b>", table_cell_bold),
            Paragraph("<b>Prescribed Intervention & Action</b>", table_cell_bold),
            Paragraph("<b>Status</b>", table_cell_bold),
        ]
    ]
    for r in recs[:4]:
        prio = r.get("priority", "medium").upper()
        prio_color = "#DC2626" if prio == "HIGH" else "#D97706"
        rec_rows.append(
            [
                Paragraph(f"<font color='{prio_color}'><b>{prio}</b></font>", table_cell),
                Paragraph(r.get("category", "Academic").title(), table_cell),
                Paragraph(f"<b>{r.get('title', '')}</b>: {r.get('action', '')}", table_cell),
                Paragraph("[ &nbsp; ] Pending", table_cell),
            ]
        )

    rec_table = Table(rec_rows, colWidths=[65, 85, 310, 80])
    rec_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(rec_table)
    story.append(Spacer(1, 12))

    # 6. Longitudinal Progression History Table (if multiple predictions exist)
    if len(predictions) > 1:
        story.append(Paragraph("4. Historical Assessment Timeline", section_heading))
        hist_rows = [
            [
                Paragraph("<b>Date</b>", table_cell_bold),
                Paragraph("<b>Phase</b>", table_cell_bold),
                Paragraph("<b>Category</b>", table_cell_bold),
                Paragraph("<b>Confidence</b>", table_cell_bold),
            ]
        ]
        for hp in predictions[:5]:
            hist_rows.append(
                [
                    Paragraph(hp.created_at.strftime("%Y-%m-%d"), table_cell),
                    Paragraph(hp.feature_set.upper(), table_cell),
                    Paragraph(hp.category, table_cell),
                    Paragraph(f"{hp.confidence:.1%}", table_cell),
                ]
            )
        hist_table = Table(hist_rows, colWidths=[120, 100, 180, 140])
        hist_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(hist_table)
        story.append(Spacer(1, 10))

    # 7. Institutional Signatures & Legal Disclaimer
    story.append(
        Paragraph(
            "<b>Institutional Decision-Support Notice:</b> This diagnostic report is generated by GradeMatrix AI "
            "as an early academic intervention indicator. Final grading, intervention strategies, and evaluations "
            "must be verified by certified teaching faculty and academic counseling personnel.",
            ParagraphStyle("NoticeText", parent=body_style, fontSize=7.5, leading=10, textColor=colors.HexColor("#64748B")),
        )
    )
    story.append(Spacer(1, 14))

    sign_table_data = [
        [
            Paragraph("____________________________<br/><b>Academic Counselor Signature</b>", table_cell),
            Paragraph("____________________________<br/><b>Faculty Advisor Signature</b>", table_cell),
            Paragraph(f"<b>Verification Date:</b> {datetime.now().strftime('%Y-%m-%d')}<br/><b>Seal / GradeMatrix AI</b>", table_cell),
        ]
    ]
    sign_table = Table(sign_table_data, colWidths=[180, 180, 180])
    sign_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(sign_table)

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


@router.get(
    "/export/pdf/{student_id_or_code}",
    summary="Per-student publication-ready PDF performance diagnostic report",
)
async def export_student_pdf(
    student_id_or_code: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.teacher, UserRole.admin)),
):
    target_uuid = None
    try:
        target_uuid = uuid.UUID(student_id_or_code)
    except ValueError:
        pass

    query = (
        select(Prediction)
        .outerjoin(Student, Prediction.student_id == Student.id)
        .options(selectinload(Prediction.student))
        .order_by(desc(Prediction.created_at))
    )
    if target_uuid is not None:
        query = query.where(
            or_(
                Prediction.student_id == target_uuid,
                Student.student_code == student_id_or_code,
            )
        )
    else:
        query = query.where(Student.student_code == student_id_or_code)

    # Strict per-account isolation
    query = query.where(Prediction.created_by == current_user.id)

    result = await db.execute(query)
    predictions = result.scalars().all()

    student_code = student_id_or_code
    if predictions and predictions[0].student:
        student_code = predictions[0].student.student_code

    pdf_bytes = _build_diagnostic_pdf(
        student_code=student_code,
        predictions=predictions,
        user_email=current_user.email,
    )

    filename = f"gradematrix_report_{student_code}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get(
    "/export/pdf/prediction/{prediction_id}",
    summary="Per-prediction publication-ready PDF diagnostic report",
)
async def export_prediction_pdf(
    prediction_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.teacher, UserRole.admin)),
):
    query = (
        select(Prediction)
        .outerjoin(Student, Prediction.student_id == Student.id)
        .options(selectinload(Prediction.student))
        .where(Prediction.id == prediction_id)
    )
    # Strict per-account isolation
    query = query.where(Prediction.created_by == current_user.id)

    result = await db.execute(query)
    pred = result.scalar_one_or_none()
    if pred is None:
        raise HTTPException(status_code=404, detail="Prediction not found.")

    student_code = pred.student.student_code if pred.student else str(pred.student_id or pred.id)[:8]

    pdf_bytes = _build_diagnostic_pdf(
        student_code=student_code,
        predictions=[pred],
        user_email=current_user.email,
    )

    filename = f"gradematrix_diagnostic_{student_code}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
