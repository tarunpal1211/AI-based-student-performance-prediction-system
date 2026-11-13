"""
tests/test_validate.py
----------------------
Unit tests for src/validate.py — form input and CSV validation.
"""

import pytest
import pandas as pd

from src.validate import validate_single, validate_csv, make_csv_template


# ---------------------------------------------------------------------------
# validate_single
# ---------------------------------------------------------------------------

VALID_EARLY = {
    "absences": 4,
    "G1": 12,
    "failures": 0,
    "studytime": 2,
    "assignment_rate": 80,
    "assessment_trend": 0,
}


class TestValidateSingle:

    def test_valid_input_returns_cleaned(self):
        cleaned, errors = validate_single(VALID_EARLY, feature_set="early")
        assert errors == []
        assert cleaned == VALID_EARLY

    def test_missing_field_returns_error(self):
        data = {k: v for k, v in VALID_EARLY.items() if k != "G1"}
        cleaned, errors = validate_single(data, feature_set="early")
        assert cleaned is None
        assert any("G1" in e or "first period" in e.lower() for e in errors)

    def test_out_of_range_g1_too_high(self):
        data = {**VALID_EARLY, "G1": 25}
        cleaned, errors = validate_single(data, feature_set="early")
        assert cleaned is None
        assert len(errors) > 0

    def test_out_of_range_absences_negative(self):
        data = {**VALID_EARLY, "absences": -1}
        cleaned, errors = validate_single(data, feature_set="early")
        assert cleaned is None

    def test_non_integer_value_returns_error(self):
        data = {**VALID_EARLY, "G1": "abc"}
        cleaned, errors = validate_single(data, feature_set="early")
        assert cleaned is None
        assert len(errors) > 0

    def test_none_value_treated_as_missing(self):
        data = {**VALID_EARLY, "failures": None}
        cleaned, errors = validate_single(data, feature_set="early")
        assert cleaned is None

    def test_string_integer_is_accepted(self):
        """Form may pass string values — should be coerced."""
        data = {**VALID_EARLY, "G1": "15"}
        cleaned, errors = validate_single(data, feature_set="early")
        assert errors == []
        assert cleaned["G1"] == 15

    def test_boundary_values_accepted(self):
        data = {
            "absences": 0,
            "G1": 0,
            "failures": 0,
            "studytime": 1,
            "assignment_rate": 0,
            "assessment_trend": -1,
        }
        cleaned, errors = validate_single(data, feature_set="early")
        assert errors == []

        data2 = {
            "absences": 93,
            "G1": 20,
            "failures": 4,
            "studytime": 4,
            "assignment_rate": 100,
            "assessment_trend": 1,
        }
        cleaned2, errors2 = validate_single(data2, feature_set="early")
        assert errors2 == []


# ---------------------------------------------------------------------------
# validate_csv
# ---------------------------------------------------------------------------

class TestValidateCSV:

    @pytest.fixture
    def valid_df(self):
        return pd.DataFrame(
            [
                {
                    "absences": 0,
                    "G1": 18,
                    "failures": 0,
                    "studytime": 3,
                    "assignment_rate": 95,
                    "assessment_trend": 1,
                },
                {
                    "absences": 5,
                    "G1": 10,
                    "failures": 1,
                    "studytime": 2,
                    "assignment_rate": 75,
                    "assessment_trend": 0,
                },
                {
                    "absences": 10,
                    "G1": 5,
                    "failures": 2,
                    "studytime": 1,
                    "assignment_rate": 40,
                    "assessment_trend": -1,
                },
            ]
        )

    def test_valid_csv(self, valid_df):
        cleaned, errors = validate_csv(valid_df, feature_set="early")
        assert cleaned is not None
        assert len(cleaned) == 3
        assert errors == []

    def test_missing_column(self, valid_df):
        df = valid_df.drop(columns=["G1"])
        cleaned, errors = validate_csv(df, feature_set="early")
        assert cleaned is None
        assert len(errors) > 0

    def test_out_of_range_row_excluded(self, valid_df):
        df = valid_df.copy()
        df.loc[0, "G1"] = 99  # invalid
        cleaned, errors = validate_csv(df, feature_set="early")
        # Two valid rows remain
        assert cleaned is not None
        assert len(cleaned) == 2
        assert len(errors) > 0

    def test_empty_csv_returns_none(self):
        df = pd.DataFrame(
            columns=[
                "absences",
                "G1",
                "failures",
                "studytime",
                "assignment_rate",
                "assessment_trend",
            ]
        )
        cleaned, errors = validate_csv(df, feature_set="early")
        assert cleaned is None

    def test_nan_cell_flagged(self, valid_df):
        df = valid_df.copy()
        df.loc[1, "failures"] = float("nan")
        cleaned, errors = validate_csv(df, feature_set="early")
        assert any("failures" in e.lower() or "missing" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# make_csv_template
# ---------------------------------------------------------------------------

class TestMakeCSVTemplate:

    def test_early_template_columns(self):
        df = make_csv_template(feature_set="early")
        assert list(df.columns) == [
            "absences",
            "G1",
            "failures",
            "studytime",
            "assignment_rate",
            "assessment_trend",
        ]

    def test_mid_template_columns(self):
        df = make_csv_template(feature_set="mid")
        assert "G2" in df.columns
        assert "assignment_rate" in df.columns
        assert "assessment_trend" in df.columns

    def test_template_has_one_row(self):
        df = make_csv_template()
        assert len(df) == 1


# ---------------------------------------------------------------------------
# Advanced Bulk Validation & Template Tests
# ---------------------------------------------------------------------------

from src.validate import detect_column_mappings, validate_student_records, make_sample_template


class TestBulkValidation:

    def test_detect_column_mappings_with_aliases(self):
        cols = ["Student Code", "First Period Grade", "missed_classes", "study_time", "past_failures"]
        mapping, unmapped = detect_column_mappings(cols, feature_set="early")
        assert mapping["student_id"] == "Student Code"
        assert mapping["G1"] == "First Period Grade"
        assert mapping["absences"] == "missed_classes"
        assert mapping["studytime"] == "study_time"
        assert mapping["failures"] == "past_failures"
        assert unmapped == []

    def test_detect_column_mappings_mid_missing_g2(self):
        cols = ["student_id", "G1", "absences", "studytime", "failures"]
        mapping, unmapped = detect_column_mappings(cols, feature_set="mid")
        assert "G2" in unmapped

    def test_validate_student_records_valid_dataset(self):
        df = pd.DataFrame([
            {"student_id": "STU-01", "G1": 15, "absences": 3, "studytime": 3, "failures": 0},
            {"student_id": "STU-02", "G1": 8, "absences": 12, "studytime": 1, "failures": 2},
        ])
        report = validate_student_records(df, feature_set="early")
        assert report["total_rows"] == 2
        assert report["valid_rows_count"] == 2
        assert report["invalid_rows_count"] == 0
        assert report["duplicate_student_ids"] == []

    def test_validate_student_records_duplicate_id_and_out_of_range(self):
        df = pd.DataFrame([
            {"student_id": "STU-01", "G1": 15, "absences": 3, "studytime": 3, "failures": 0},
            {"student_id": "STU-01", "G1": 25, "absences": 3, "studytime": 3, "failures": 0},  # duplicate ID & G1 > 20
        ])
        report = validate_student_records(df, feature_set="early")
        assert "STU-01" in report["duplicate_student_ids"]
        assert report["invalid_rows_count"] > 0
        assert report["rows"][1]["is_valid"] is False
        assert any("20" in e for e in report["rows"][1]["errors"])

    def test_validate_student_records_mid_g2_explanation(self):
        df = pd.DataFrame([
            {"student_id": "STU-01", "G1": 15, "absences": 3, "studytime": 3, "failures": 0},
        ])
        report = validate_student_records(df, feature_set="mid")
        assert "G2" in report["unmapped_required"]
        assert len(report["special_notes"]) > 0
        assert "G2" in report["special_notes"][0]

    def test_make_sample_template_csv_and_xlsx(self):
        csv_bytes, csv_name, csv_type = make_sample_template("early", "csv")
        assert csv_name.endswith(".csv")
        assert b"student_id" in csv_bytes
        assert csv_type == "text/csv"

        xlsx_bytes, xlsx_name, xlsx_type = make_sample_template("mid", "xlsx")
        assert xlsx_name.endswith(".xlsx")
        assert len(xlsx_bytes) > 0
        assert "sheet" in xlsx_type

