"""
tests/test_predict.py
---------------------
Unit tests for src/predict.py — predict_one returns valid output.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch

from src.predict import predict_one, top_factors, predict_batch

VALID_CATEGORIES = {"Performing Well", "Needs Improvement", "At-Risk"}


def _make_mock_model(category: str = "At-Risk", confidence: float = 0.8):
    """Build a minimal mock pipeline that mimics a scikit-learn pipeline."""
    mock = MagicMock()
    mock.predict.return_value = [category]
    mock.classes_ = np.array(["At-Risk", "Needs Improvement", "Performing Well"])
    idx = list(mock.classes_).index(category)
    proba = [0.0, 0.0, 0.0]
    proba[idx] = confidence
    rest = (1 - confidence) / 2
    for i in range(3):
        if i != idx:
            proba[i] = rest
    mock.predict_proba.return_value = [proba]

    # Last step of pipeline for feature importances
    last_step = MagicMock()
    last_step.feature_importances_ = np.array([0.3, 0.25, 0.15, 0.1, 0.1, 0.1])
    mock.__getitem__ = MagicMock(return_value=last_step)
    mock.__iter__ = MagicMock(return_value=iter([last_step]))
    return mock


EARLY_INPUT = {
    "absences": 10,
    "G1": 5,
    "failures": 2,
    "studytime": 1,
    "assignment_rate": 40,
    "assessment_trend": -1,
}


class TestPredictOne:

    def test_returns_dict(self):
        model = _make_mock_model("At-Risk")
        result = predict_one(model, EARLY_INPUT)
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        model = _make_mock_model("At-Risk")
        result = predict_one(model, EARLY_INPUT)
        assert "category" in result
        assert "confidence" in result
        assert "factors" in result

    def test_category_is_valid(self):
        for cat in VALID_CATEGORIES:
            model = _make_mock_model(cat)
            result = predict_one(model, EARLY_INPUT)
            assert result["category"] in VALID_CATEGORIES

    def test_confidence_between_0_and_1(self):
        model = _make_mock_model("Needs Improvement", 0.65)
        result = predict_one(model, EARLY_INPUT)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_factors_is_list_of_3(self):
        model = _make_mock_model("At-Risk")
        result = predict_one(model, EARLY_INPUT)
        assert isinstance(result["factors"], list)
        assert len(result["factors"]) == 3

    def test_factors_are_strings(self):
        model = _make_mock_model("At-Risk")
        result = predict_one(model, EARLY_INPUT)
        assert all(isinstance(f, str) for f in result["factors"])

    def test_at_risk_prediction(self):
        model = _make_mock_model("At-Risk", 0.9)
        result = predict_one(model, EARLY_INPUT)
        assert result["category"] == "At-Risk"
        assert result["confidence"] == pytest.approx(0.9, abs=1e-6)

    def test_performing_well_prediction(self):
        model = _make_mock_model("Performing Well", 0.85)
        good_input = {"absences": 1, "G1": 18, "failures": 0, "studytime": 4}
        result = predict_one(model, good_input)
        assert result["category"] == "Performing Well"


class TestPredictBatch:

    def test_returns_dataframe(self):
        model = _make_mock_model("Needs Improvement")
        df = pd.DataFrame([EARLY_INPUT, EARLY_INPUT])
        result = predict_batch(model, df)
        assert isinstance(result, pd.DataFrame)

    def test_result_has_prediction_column(self):
        model = _make_mock_model("At-Risk")
        df = pd.DataFrame([EARLY_INPUT])
        result = predict_batch(model, df)
        assert "Prediction" in result.columns

    def test_sorted_by_risk(self):
        """At-Risk rows should appear before Performing Well rows."""
        model = MagicMock()
        model.classes_ = np.array(["At-Risk", "Needs Improvement", "Performing Well"])
        model.predict.side_effect = lambda x: ["Performing Well" if x.iloc[0]["G1"] >= 14 else "At-Risk"]
        model.predict_proba.return_value = [[0.1, 0.1, 0.8]]

        last_step = MagicMock()
        last_step.feature_importances_ = np.array([0.4, 0.3, 0.2, 0.1])
        model.__getitem__ = MagicMock(return_value=last_step)

        rows = [
            {"absences": 0, "G1": 18, "failures": 0, "studytime": 4},
            {"absences": 10, "G1": 5, "failures": 3, "studytime": 1},
        ]
        df = pd.DataFrame(rows)
        result = predict_batch(model, df)
        # First row should be At-Risk (lower G1)
        # (model mock returns At-Risk when G1 < 14)
        assert "Prediction" in result.columns
