"""
tests/test_enhancements.py
--------------------------
Unit tests for GradeMatrix AI enhancements:
- Explainable AI (XAI) attributions & narratives
- Personalized Recommendations
"""

import joblib
import pytest
from src.explain import explain_prediction
from src.recommend import generate_recommendations


@pytest.fixture
def early_model():
    return joblib.load("models/early_model.joblib")


def test_explain_prediction_structure(early_model):
    sample_input = {
        "absences": 18,
        "G1": 5,
        "failures": 3,
        "studytime": 1,
        "assignment_rate": 40,
        "assessment_trend": -1,
    }
    explanation = explain_prediction(
        model=early_model,
        input_dict=sample_input,
        category="At-Risk",
        confidence=0.88,
    )
    assert isinstance(explanation, dict)
    assert "summary" in explanation
    assert "contributions" in explanation
    assert "risk_factors" in explanation
    assert "protective_factors" in explanation
    assert len(explanation["contributions"]) > 0
    # Absences should be highlighted as a risk factor
    has_risk = any(c.get("direction") == "increased_risk" for c in explanation["contributions"])
    assert has_risk


def test_recommendation_generation():
    inputs = {
        "G1": 6,
        "absences": 14,
        "failures": 2,
        "studytime": 1,
        "assignment_rate": 50,
        "assessment_trend": -1,
    }
    recs = generate_recommendations("At-Risk", inputs)
    assert isinstance(recs, list)
    assert len(recs) >= 3
    for r in recs:
        assert "priority" in r
        assert "category" in r
        assert "title" in r
        assert "action" in r


def test_recommendations_performing_well():
    inputs = {
        "G1": 18,
        "absences": 1,
        "failures": 0,
        "studytime": 4,
        "assignment_rate": 95,
        "assessment_trend": 1,
    }
    recs = generate_recommendations("Performing Well", inputs)
    assert isinstance(recs, list)
    assert len(recs) >= 1
    assert any("Performance" in r["title"] or "Study" in r["title"] for r in recs)
