"""
src/validate.py
---------------
Validation helpers for the Student Performance Predictor.

Two public surfaces:
  - validate_single(data)  : validate a dict of feature values from the form.
  - validate_csv(df)       : validate every row of an uploaded CSV DataFrame.

Both return (cleaned_data, errors) so the caller can decide what to show.
"""

from __future__ import annotations
import pandas as pd

# ---------------------------------------------------------------------------
# Feature specification
# ---------------------------------------------------------------------------

# Each entry: (column_name, min_value, max_value, dtype, description)
FEATURE_SPEC: dict[str, dict] = {
    "absences": {
        "min": 0,
        "max": 93,
        "dtype": int,
        "label": "Number of school absences",
    },
    "G1": {
        "min": 0,
        "max": 20,
        "dtype": int,
        "label": "First period grade (0–20)",
    },
    "failures": {
        "min": 0,
        "max": 4,
        "dtype": int,
        "label": "Number of past class failures",
    },
    "studytime": {
        "min": 1,
        "max": 4,
        "dtype": int,
        "label": "Weekly study time (1=<2h, 2=2–5h, 3=5–10h, 4=>10h)",
    },
    "assignment_rate": {
        "min": 0,
        "max": 100,
        "dtype": int,
        "label": "Assignment completion rate (0–100%)",
    },
    "assessment_trend": {
        "min": -1,
        "max": 1,
        "dtype": int,
        "label": "Recent assessment trend (-1=Declining, 0=Stable, 1=Improving)",
    },
    "G2": {
        "min": 0,
        "max": 20,
        "dtype": int,
        "label": "Second period grade (0–20)",
    },
}

EARLY_COLS = [
    "absences",
    "G1",
    "failures",
    "studytime",
    "assignment_rate",
    "assessment_trend",
]
MID_COLS = [
    "absences",
    "G1",
    "failures",
    "studytime",
    "G2",
    "assignment_rate",
    "assessment_trend",
]


# ---------------------------------------------------------------------------
# Single-record validation
# ---------------------------------------------------------------------------

def validate_single(data: dict,
                    feature_set: str = "early") -> tuple[dict | None, list[str]]:
    """
    Validate a dict of raw form values.

    Parameters
    ----------
    data : dict
        Mapping of feature name → raw value (may be str, int, float, or None).
    feature_set : {"early", "mid"}
        Which feature columns are required.

    Returns
    -------
    cleaned : dict | None
        Cleaned and type-cast values, or None if validation failed.
    errors : list[str]
        Human-readable error messages (empty if validation passed).
    """
    required = EARLY_COLS if feature_set == "early" else MID_COLS
    errors: list[str] = []
    cleaned: dict = {}

    for col in required:
        spec = FEATURE_SPEC[col]
        raw = data.get(col)

        # Missing check
        if raw is None or str(raw).strip() == "":
            errors.append(f"'{spec['label']}' is required.")
            continue

        # Type cast
        try:
            value = spec["dtype"](raw)
        except (ValueError, TypeError):
            errors.append(
                f"'{spec['label']}' must be a whole number, got: {raw!r}."
            )
            continue

        # Range check
        if not (spec["min"] <= value <= spec["max"]):
            errors.append(
                f"'{spec['label']}' must be between {spec['min']} and {spec['max']}, "
                f"got: {value}."
            )
            continue

        cleaned[col] = value

    if errors:
        return None, errors
    return cleaned, []


# ---------------------------------------------------------------------------
# CSV validation
# ---------------------------------------------------------------------------

def validate_csv(df: pd.DataFrame,
                 feature_set: str = "early") -> tuple[pd.DataFrame | None, list[str]]:
    """
    Validate all rows in an uploaded CSV DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Raw DataFrame loaded from the uploaded CSV.
    feature_set : {"early", "mid"}
        Which feature columns must be present.

    Returns
    -------
    cleaned : pd.DataFrame | None
        Cleaned DataFrame with correct dtypes, or None if fatal column errors.
    errors : list[str]
        Row-level and column-level error messages.
    """
    required = EARLY_COLS if feature_set == "early" else MID_COLS
    errors: list[str] = []

    # Check for required columns
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        errors.append(
            f"CSV is missing required columns: {', '.join(missing_cols)}. "
            f"Download the template to see the expected format."
        )
        return None, errors

    cleaned_rows = []
    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-indexed with header row
        row_cleaned = {}
        row_ok = True

        for col in required:
            spec = FEATURE_SPEC[col]
            raw = row[col]

            if pd.isna(raw) or str(raw).strip() == "":
                errors.append(f"Row {row_num}: '{spec['label']}' is missing.")
                row_ok = False
                continue

            try:
                value = spec["dtype"](raw)
            except (ValueError, TypeError):
                errors.append(
                    f"Row {row_num}: '{spec['label']}' must be a whole number, "
                    f"got: {raw!r}."
                )
                row_ok = False
                continue

            if not (spec["min"] <= value <= spec["max"]):
                errors.append(
                    f"Row {row_num}: '{spec['label']}' must be {spec['min']}–"
                    f"{spec['max']}, got: {value}."
                )
                row_ok = False
                continue

            row_cleaned[col] = value

        if row_ok:
            cleaned_rows.append(row_cleaned)

    if not cleaned_rows:
        errors.insert(0, "No valid rows found in the uploaded CSV.")
        return None, errors

    cleaned_df = pd.DataFrame(cleaned_rows, columns=required)
    return cleaned_df, errors


# ---------------------------------------------------------------------------
# CSV template generator
# ---------------------------------------------------------------------------

def make_csv_template(feature_set: str = "early") -> pd.DataFrame:
    """
    Return an empty template DataFrame with the correct column headers.

    Parameters
    ----------
    feature_set : {"early", "mid"}

    Returns
    -------
    pd.DataFrame
        One example row with plausible placeholder values.
    """
    required = EARLY_COLS if feature_set == "early" else MID_COLS
    example = {
        "absences": 4,
        "G1": 12,
        "failures": 0,
        "studytime": 2,
        "G2": 11,
        "assignment_rate": 85,
        "assessment_trend": 0,
    }
    row = {col: example[col] for col in required}
    return pd.DataFrame([row])


# ---------------------------------------------------------------------------
# Advanced Column Detection & Bulk Validation Engine
# ---------------------------------------------------------------------------

COLUMN_ALIASES: dict[str, list[str]] = {
    "student_id": [
        "student_id", "student id", "student_code", "student code", "id",
        "roll_no", "roll no", "roll_number", "roll number", "student", "student_name", "name"
    ],
    "G1": [
        "g1", "g 1", "grade1", "grade 1", "first_period_grade",
        "first period grade", "first_term_grade", "term1", "exam1"
    ],
    "G2": [
        "g2", "g 2", "grade2", "grade 2", "second_period_grade",
        "second period grade", "second_term_grade", "term2", "exam2"
    ],
    "absences": [
        "absences", "absence", "absent", "missed_classes", "missed classes",
        "days_absent", "days absent", "attendance_absent", "absent_days"
    ],
    "failures": [
        "failures", "past_failures", "past failures", "class_failures",
        "class failures", "failures_count", "failed_classes", "backlogs"
    ],
    "studytime": [
        "studytime", "study_time", "study time", "weekly_study_time",
        "weekly study time", "study_hours", "study hours"
    ],
    "assignment_rate": [
        "assignment_rate", "assignment rate", "assignments", "assignment_completion",
        "assignment completion", "homework_rate", "homework", "submission_rate"
    ],
    "assessment_trend": [
        "assessment_trend", "assessment trend", "trend", "performance_trend",
        "performance trend", "progress_trend", "recent_trend"
    ],
}


def detect_column_mappings(df_columns: list[str], feature_set: str = "early") -> tuple[dict[str, str], list[str]]:
    """
    Detect column mappings between uploaded file columns and model features.

    Returns:
        mapping: dict mapping target_feature -> uploaded_column_name
        unmapped_required: list of required model features not matched
    """
    required_features = ["absences", "G1", "failures", "studytime"]
    if feature_set == "mid":
        required_features.append("G2")

    all_target_features = list(required_features)
    if "assignment_rate" not in all_target_features:
        all_target_features.append("assignment_rate")
    if "assessment_trend" not in all_target_features:
        all_target_features.append("assessment_trend")
    all_target_features.append("student_id")

    mapping: dict[str, str] = {}
    used_cols: set[str] = set()

    # Pass 1: Exact matches (case-insensitive)
    for target in all_target_features:
        for col in df_columns:
            if col in used_cols:
                continue
            if col.strip().lower() == target.lower():
                mapping[target] = col
                used_cols.add(col)
                break

    # Pass 2: Alias matches
    for target in all_target_features:
        if target in mapping:
            continue
        aliases = COLUMN_ALIASES.get(target, [])
        for col in df_columns:
            if col in used_cols:
                continue
            norm = col.strip().lower().replace("-", " ").replace("_", " ")
            if norm in [a.lower().replace("-", " ").replace("_", " ") for a in aliases]:
                mapping[target] = col
                used_cols.add(col)
                break

    unmapped_required = [f for f in required_features if f not in mapping]
    return mapping, unmapped_required


def validate_student_records(
    df: pd.DataFrame,
    feature_set: str = "early",
    column_mapping: dict[str, str] | None = None,
) -> dict:
    """
    Validate student records from an uploaded DataFrame.

    Checks:
      - Column mapping for required features (absences, G1, failures, studytime, and G2 if mid).
      - Duplicate student IDs across rows.
      - Type conversion and valid ranges for all numeric features.
      - Defaulting of optional features (assignment_rate=75, assessment_trend=0).
    """
    detected_cols = list(df.columns)
    if not column_mapping:
        column_mapping, unmapped_required = detect_column_mappings(detected_cols, feature_set)
    else:
        required_features = ["absences", "G1", "failures", "studytime"]
        if feature_set == "mid":
            required_features.append("G2")
        unmapped_required = [f for f in required_features if not column_mapping.get(f)]

    special_notes: list[str] = []
    if feature_set == "mid" and "G2" in unmapped_required:
        special_notes.append(
            "Mid-term Prediction requires the second-period grade (G2, 0–20). "
            "The 'G2' column was not found or mapped in the uploaded file."
        )

    target_to_col = dict(column_mapping)
    student_id_col = target_to_col.get("student_id")

    # Detect duplicate student IDs
    seen_ids: dict[str, int] = {}
    duplicate_ids: set[str] = set()
    if student_id_col and student_id_col in df.columns:
        for raw_val in df[student_id_col]:
            if pd.notna(raw_val) and str(raw_val).strip():
                s_id = str(raw_val).strip()
                seen_ids[s_id] = seen_ids.get(s_id, 0) + 1
                if seen_ids[s_id] > 1:
                    duplicate_ids.add(s_id)

    total_rows = len(df)
    valid_count = 0
    invalid_count = 0
    row_records = []

    required_check_cols = ["absences", "G1", "failures", "studytime"]
    if feature_set == "mid":
        required_check_cols.append("G2")

    for idx, row in df.iterrows():
        row_num = idx + 1
        row_errors: list[str] = []
        cleaned: dict = {}
        raw_dict = {str(k): (None if pd.isna(v) else v) for k, v in row.to_dict().items()}

        # Student ID extraction
        if student_id_col and student_id_col in row and pd.notna(row[student_id_col]):
            s_id = str(row[student_id_col]).strip()
        else:
            s_id = f"R23EF{row_num:03d}"

        if s_id in duplicate_ids:
            row_errors.append(f"Duplicate Student ID '{s_id}' detected.")

        # Validate required model features
        for feat in required_check_cols:
            col_name = target_to_col.get(feat)
            if not col_name or col_name not in row:
                row_errors.append(f"Required feature '{feat}' is not mapped.")
                continue

            raw_val = row[col_name]
            if pd.isna(raw_val) or str(raw_val).strip() == "":
                row_errors.append(f"'{feat}' is missing.")
                continue

            spec = FEATURE_SPEC.get(feat, {"min": 0, "max": 100, "dtype": int})
            try:
                val_float = float(str(raw_val).strip())
                val_num = int(round(val_float))
            except (ValueError, TypeError):
                row_errors.append(f"'{feat}' must be a number, got: {raw_val!r}.")
                continue

            if not (spec["min"] <= val_num <= spec["max"]):
                row_errors.append(
                    f"'{feat}' must be between {spec['min']} and {spec['max']}, got: {val_num}."
                )
                continue

            cleaned[feat] = val_num

        # Optional features: assignment_rate & assessment_trend
        rate_col = target_to_col.get("assignment_rate")
        if rate_col and rate_col in row and pd.notna(row[rate_col]) and str(row[rate_col]).strip():
            try:
                rate_val = int(round(float(str(row[rate_col]).strip())))
                cleaned["assignment_rate"] = rate_val if (0 <= rate_val <= 100) else 75
            except Exception:
                cleaned["assignment_rate"] = 75
        else:
            cleaned["assignment_rate"] = 75

        trend_col = target_to_col.get("assessment_trend")
        if trend_col and trend_col in row and pd.notna(row[trend_col]) and str(row[trend_col]).strip():
            try:
                trend_val = int(round(float(str(row[trend_col]).strip())))
                cleaned["assessment_trend"] = trend_val if (-1 <= trend_val <= 1) else 0
            except Exception:
                cleaned["assessment_trend"] = 0
        else:
            cleaned["assessment_trend"] = 0

        is_valid = (len(row_errors) == 0) and (len(unmapped_required) == 0)
        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1

        row_records.append({
            "row_index": idx,
            "student_id": s_id,
            "is_valid": is_valid,
            "errors": row_errors,
            "cleaned_data": cleaned,
            "raw_data": raw_dict,
        })

    return {
        "total_rows": total_rows,
        "valid_rows_count": valid_count,
        "invalid_rows_count": invalid_count,
        "column_mapping": column_mapping,
        "unmapped_required": unmapped_required,
        "duplicate_student_ids": list(duplicate_ids),
        "special_notes": special_notes,
        "rows": row_records,
    }


def make_sample_template(feature_set: str = "early", file_format: str = "csv") -> tuple[bytes, str, str]:
    """
    Generate downloadable template file (CSV or Excel) with realistic sample student data.
    Returns (bytes, filename, media_type)
    """
    if feature_set == "mid":
        data = [
            {"student_id": "R23EF001", "G1": 15, "G2": 16, "absences": 2, "studytime": 3, "failures": 0, "assignment_rate": 90, "assessment_trend": 1},
            {"student_id": "R23EF002", "G1": 11, "G2": 10, "absences": 6, "studytime": 2, "failures": 1, "assignment_rate": 75, "assessment_trend": 0},
            {"student_id": "R23EF003", "G1": 6,  "G2": 7,  "absences": 14, "studytime": 1, "failures": 2, "assignment_rate": 45, "assessment_trend": -1},
            {"student_id": "R23EF004", "G1": 13, "G2": 14, "absences": 4, "studytime": 2, "failures": 0, "assignment_rate": 80, "assessment_trend": 1},
            {"student_id": "R23EF005", "G1": 8,  "G2": 9,  "absences": 10, "studytime": 2, "failures": 1, "assignment_rate": 60, "assessment_trend": 0},
        ]
        filename_base = "gradematrix_midterm_template"
    else:
        data = [
            {"student_id": "R23EF001", "G1": 15, "absences": 2, "studytime": 3, "failures": 0, "assignment_rate": 90, "assessment_trend": 1},
            {"student_id": "R23EF002", "G1": 11, "absences": 6, "studytime": 2, "failures": 1, "assignment_rate": 75, "assessment_trend": 0},
            {"student_id": "R23EF003", "G1": 6,  "absences": 14, "studytime": 1, "failures": 2, "assignment_rate": 45, "assessment_trend": -1},
            {"student_id": "R23EF004", "G1": 13, "absences": 4, "studytime": 2, "failures": 0, "assignment_rate": 80, "assessment_trend": 1},
            {"student_id": "R23EF005", "G1": 8,  "absences": 10, "studytime": 2, "failures": 1, "assignment_rate": 60, "assessment_trend": 0},
        ]
        filename_base = "gradematrix_early_template"

    df = pd.DataFrame(data)
    if file_format.lower() in ["xlsx", "excel"]:
        import io
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Students")
        bio.seek(0)
        return bio.getvalue(), f"{filename_base}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        csv_str = df.to_csv(index=False)
        return csv_str.encode("utf-8"), f"{filename_base}.csv", "text/csv"

