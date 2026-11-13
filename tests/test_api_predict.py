"""
tests/test_api_predict.py
-------------------------
Unit tests for prediction schemas and recommendation engine integration.
"""

import pytest
from pydantic import ValidationError
from api.schemas.predict import SinglePredictRequest
from src.recommend import generate_recommendations


def test_predict_request_schema_valid_early():
    req = SinglePredictRequest(
        feature_set="early",
        absences=4,
        G1=12,
        failures=0,
        studytime=2,
    )
    assert req.feature_set == "early"
    assert req.G1 == 12


def test_predict_request_schema_mid_requires_g2():
    with pytest.raises(ValidationError):
        SinglePredictRequest(
            feature_set="mid",
            absences=4,
            G1=12,
            failures=0,
            studytime=2,
            G2=None,
        )


def test_generate_recommendations_at_risk():
    recs = generate_recommendations(
        category="At-Risk",
        input_features={"G1": 6, "absences": 14, "failures": 2, "studytime": 1},
    )
    assert len(recs) > 0
    priorities = [r["priority"] for r in recs]
    assert "high" in priorities


from api.schemas.predict import BatchStudentInput, BatchProcessRequest, BatchExportRequest


def test_batch_student_input_schema():
    inp = BatchStudentInput(
        row_index=0,
        student_id="STU-001",
        absences=5,
        G1=14,
        failures=0,
        studytime=3,
        G2=15,
        assignment_rate=80,
        assessment_trend=1,
    )
    assert inp.student_id == "STU-001"
    assert inp.G2 == 15
    assert inp.assignment_rate == 80


def test_batch_process_request_validation():
    req = BatchProcessRequest(
        feature_set="early",
        records=[
            BatchStudentInput(
                row_index=0,
                student_id="STU-001",
                absences=5,
                G1=14,
                failures=0,
                studytime=3,
            )
        ],
    )
    assert len(req.records) == 1
    assert req.feature_set == "early"


def test_batch_export_request_validation():
    exp = BatchExportRequest(
        format="csv",
        feature_set="early",
        results=[{"student_id": "STU-001", "category": "Performing Well", "confidence": 0.88}],
    )
    assert exp.format == "csv"

