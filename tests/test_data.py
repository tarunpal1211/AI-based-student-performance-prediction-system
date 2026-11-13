"""
tests/test_data.py
------------------
Unit tests for src/data.py — make_label and data loading.
"""

import pytest
import pandas as pd

from src.data import make_label, prepare_dataset


# ---------------------------------------------------------------------------
# make_label
# ---------------------------------------------------------------------------

class TestMakeLabel:
    """Tests for the make_label boundary conditions."""

    def test_performing_well_at_14(self):
        assert make_label(14) == "Performing Well"

    def test_performing_well_at_20(self):
        assert make_label(20) == "Performing Well"

    def test_performing_well_at_15(self):
        assert make_label(15) == "Performing Well"

    def test_needs_improvement_at_13(self):
        assert make_label(13) == "Needs Improvement"

    def test_needs_improvement_at_8(self):
        assert make_label(8) == "Needs Improvement"

    def test_needs_improvement_at_10(self):
        assert make_label(10) == "Needs Improvement"

    def test_at_risk_at_7(self):
        assert make_label(7) == "At-Risk"

    def test_at_risk_at_0(self):
        assert make_label(0) == "At-Risk"

    def test_at_risk_at_1(self):
        assert make_label(1) == "At-Risk"

    def test_nan_raises(self):
        with pytest.raises(ValueError):
            make_label(float("nan"))

    def test_float_input(self):
        """Fractional scores should be handled via float cast."""
        assert make_label(14.0) == "Performing Well"
        assert make_label(7.9) == "At-Risk"
        assert make_label(13.5) == "Needs Improvement"

    def test_all_labels_returned(self):
        labels = {make_label(g) for g in [0, 8, 14]}
        assert labels == {"At-Risk", "Needs Improvement", "Performing Well"}


# ---------------------------------------------------------------------------
# prepare_dataset
# ---------------------------------------------------------------------------

class TestPrepareDataset:
    """Tests for prepare_dataset with synthetic data."""

    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame(
            {
                "absences": [0, 5, 10, 2],
                "G1": [18, 10, 5, 12],
                "G2": [17, 9, 4, 11],
                "failures": [0, 1, 2, 0],
                "studytime": [3, 2, 1, 2],
                "G3": [18, 10, 5, 13],
                "age": [17, 16, 18, 17],
                "sex": ["M", "F", "M", "F"],
            }
        )

    def test_early_feature_set(self, sample_df):
        X, y = prepare_dataset(sample_df, feature_set="early")
        assert list(X.columns) == [
            "absences",
            "G1",
            "failures",
            "studytime",
            "assignment_rate",
            "assessment_trend",
        ]
        assert len(y) == 4

    def test_mid_feature_set(self, sample_df):
        X, y = prepare_dataset(sample_df, feature_set="mid")
        assert list(X.columns) == [
            "absences",
            "G1",
            "failures",
            "studytime",
            "G2",
            "assignment_rate",
            "assessment_trend",
        ]

    def test_labels_correct(self, sample_df):
        _, y = prepare_dataset(sample_df, feature_set="early")
        assert y.iloc[0] == "Performing Well"
        assert y.iloc[2] == "At-Risk"

    def test_g3_not_in_features(self, sample_df):
        X, _ = prepare_dataset(sample_df, feature_set="early")
        assert "G3" not in X.columns

    def test_missing_g3_raises(self):
        bad_df = pd.DataFrame({"absences": [1], "G1": [10]})
        with pytest.raises(ValueError, match="G3"):
            prepare_dataset(bad_df)
