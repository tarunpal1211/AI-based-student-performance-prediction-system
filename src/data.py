"""
src/data.py
-----------
Data loading and label-engineering utilities for the Student Performance Predictor.

Functions
---------
load_data(path)      Load a UCI Student Performance CSV and return a DataFrame.
combine_datasets()   Load both math and Portuguese files and concatenate them.
make_label(g3)       Map a G3 score to one of three performance categories.
build_feature_sets() Return the early-model and mid-term feature column lists.
"""

import os
import json
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LABEL_MAP = {
    "Performing Well": "Performing Well",
    "Needs Improvement": "Needs Improvement",
    "At-Risk": "At-Risk",
}

LABEL_ORDER = ["At-Risk", "Needs Improvement", "Performing Well"]

EARLY_FEATURES = [
    "absences",
    "G1",
    "failures",
    "studytime",
    "assignment_rate",
    "assessment_trend",
]
MID_FEATURES = [
    "absences",
    "G1",
    "failures",
    "studytime",
    "G2",
    "assignment_rate",
    "assessment_trend",
]

DATA_RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "schema.json")


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def make_label(g3: float) -> str:
    """
    Convert a G3 grade (0-20) to a performance category.

    Rules (per spec):
      - 14 or higher  → "Performing Well"
      - 8 to 13       → "Needs Improvement"
      - below 8       → "At-Risk"

    Parameters
    ----------
    g3 : numeric
        Final-period grade on a 0-20 scale.

    Returns
    -------
    str
        One of the three category strings.
    """
    if pd.isna(g3):
        raise ValueError("G3 must not be NaN.")
    g3 = float(g3)
    if g3 >= 14:
        return "Performing Well"
    elif g3 >= 8:
        return "Needs Improvement"
    else:
        return "At-Risk"


def load_data(path: str) -> pd.DataFrame:
    """
    Load a UCI Student Performance CSV file.

    The UCI files use a semicolon delimiter and include a header row.

    Parameters
    ----------
    path : str
        Absolute or relative path to the CSV file.

    Returns
    -------
    pd.DataFrame
        Raw data with original column names preserved.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Data file not found: {path}")
    df = pd.read_csv(path, sep=";")
    return df


def combine_datasets(math_path: str | None = None,
                     por_path: str | None = None) -> pd.DataFrame:
    """
    Load one or both UCI files and return a single DataFrame.

    If both files exist the frames are concatenated and the index is reset.
    If only one file exists that frame is returned as-is.

    Parameters
    ----------
    math_path : str, optional
        Path to student-mat.csv.  Defaults to data/raw/student-mat.csv.
    por_path : str, optional
        Path to student-por.csv.  Defaults to data/raw/student-por.csv.

    Returns
    -------
    pd.DataFrame
    """
    math_path = math_path or os.path.join(DATA_RAW, "student-mat.csv")
    por_path = por_path or os.path.join(DATA_RAW, "student-por.csv")

    frames = []
    for p in (math_path, por_path):
        if os.path.exists(p):
            frames.append(load_data(p))

    if not frames:
        raise FileNotFoundError(
            "No UCI data files found. Run 'python src/download_data.py' first."
        )

    if len(frames) == 1:
        return frames[0].reset_index(drop=True)

    return pd.concat(frames, ignore_index=True)


def build_feature_sets():
    """
    Return the early-model and mid-term feature column name lists.

    Returns
    -------
    tuple[list[str], list[str]]
        (early_features, mid_features)
    """
    return EARLY_FEATURES.copy(), MID_FEATURES.copy()


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure engineered features (assignment_rate and assessment_trend) exist.
    If missing, synthesizes realistic values based on student performance signals.
    """
    df = df.copy()
    if "assignment_rate" not in df.columns:
        rng = np.random.RandomState(42)
        study_term = df.get("studytime", pd.Series(2, index=df.index)).astype(float) * 5.0
        fail_term = df.get("failures", pd.Series(0, index=df.index)).astype(float) * 8.0
        abs_term = df.get("absences", pd.Series(0, index=df.index)).astype(float) * 0.3
        g1_term = (df.get("G1", pd.Series(10, index=df.index)).astype(float) - 10.0) * 1.5

        base = 70.0 + study_term - fail_term - abs_term + g1_term
        noise = rng.normal(0, 4.0, size=len(df))
        df["assignment_rate"] = np.clip(np.round(base + noise), 5, 100).astype(int)

    if "assessment_trend" not in df.columns:
        if "G1" in df.columns and "G2" in df.columns:
            diff = df["G2"].astype(float) - df["G1"].astype(float)
            df["assessment_trend"] = diff.apply(
                lambda d: 1 if d >= 1.0 else (-1 if d <= -1.0 else 0)
            ).astype(int)
        else:
            rng = np.random.RandomState(101)
            choices = [-1, 0, 1]
            df["assessment_trend"] = rng.choice(choices, size=len(df), p=[0.25, 0.50, 0.25]).astype(int)

    return df


def prepare_dataset(df: pd.DataFrame,
                    feature_set: str = "early") -> tuple[pd.DataFrame, pd.Series]:
    """
    Apply labels, select features, and drop rows with missing target.

    Parameters
    ----------
    df : pd.DataFrame
        Raw student data containing G3 and feature columns.
    feature_set : {"early", "mid"}
        Which set of predictor columns to use.

    Returns
    -------
    X : pd.DataFrame
        Feature matrix.
    y : pd.Series
        Categorical labels.
    """
    if "G3" not in df.columns:
        raise ValueError("DataFrame must contain a 'G3' column.")

    df = df.dropna(subset=["G3"]).copy()
    df = add_engineered_features(df)
    df["label"] = df["G3"].apply(make_label)

    cols = EARLY_FEATURES if feature_set == "early" else MID_FEATURES
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns for feature set '{feature_set}': {missing}")

    X = df[cols].copy()
    y = df["label"].copy()
    return X, y


def save_schema(feature_set: str = "early") -> None:
    """
    Write models/schema.json so the app and training agree on column order.

    Parameters
    ----------
    feature_set : {"early", "mid"}
    """
    os.makedirs(os.path.dirname(SCHEMA_PATH), exist_ok=True)
    cols = EARLY_FEATURES if feature_set == "early" else MID_FEATURES
    schema = {
        "feature_set": feature_set,
        "features": cols,
        "label_classes": LABEL_ORDER,
        "label_rules": {
            "Performing Well": "G3 >= 14",
            "Needs Improvement": "8 <= G3 <= 13",
            "At-Risk": "G3 < 8",
        },
    }
    with open(SCHEMA_PATH, "w") as f:
        json.dump(schema, f, indent=2)
    print(f"Schema saved to {SCHEMA_PATH}")


def load_schema() -> dict:
    """
    Load the schema from models/schema.json.

    Returns
    -------
    dict
    """
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(
            "models/schema.json not found. Run src/train.py to generate it."
        )
    with open(SCHEMA_PATH) as f:
        return json.load(f)
