"""
src/train.py
------------
Model training, comparison, and persistence for the Student Performance Predictor.

Run directly to train both the early model (G1 features) and the mid-term model
(G1 + G2 features), then save the best of each to the models/ directory.

Usage
-----
    python src/train.py

Outputs
-------
    models/early_model.joblib   Best early-model pipeline
    models/mid_model.joblib     Best mid-term model pipeline
    models/early_metrics.json   Cross-val + test metrics for early model
    models/mid_metrics.json     Cross-val + test metrics for mid-term model
    models/schema.json          Feature column names and label rules
    reports/figures/            Confusion matrices and CV bar charts
"""

from __future__ import annotations
import json
import os
import sys
import warnings

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    classification_report,
    confusion_matrix,
    f1_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(ROOT, "models")
FIGURES_DIR = os.path.join(ROOT, "reports", "figures")

sys.path.insert(0, ROOT)
from src.data import (
    LABEL_ORDER,
    combine_datasets,
    prepare_dataset,
    save_schema,
)

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# Pipeline builders
# ---------------------------------------------------------------------------

def _build_pipelines() -> dict[str, Pipeline]:
    """Return a dict of candidate scikit-learn pipelines."""
    return {
        "Logistic Regression": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1000,
                        random_state=42,
                    ),
                ),
            ]
        ),
        "Decision Tree": Pipeline(
            [
                (
                    "clf",
                    DecisionTreeClassifier(
                        class_weight="balanced",
                        random_state=42,
                        max_depth=6,
                    ),
                )
            ]
        ),
        "Random Forest": Pipeline(
            [
                (
                    "clf",
                    RandomForestClassifier(
                        class_weight="balanced",
                        n_estimators=200,
                        random_state=42,
                        n_jobs=-1,
                    ),
                )
            ]
        ),
    }


# ---------------------------------------------------------------------------
# Cross-validation helper
# ---------------------------------------------------------------------------

def _cross_validate_models(
    pipelines: dict[str, Pipeline],
    X: pd.DataFrame,
    y: pd.Series,
    cv: int = 5,
) -> pd.DataFrame:
    """Run stratified CV on every pipeline and return a summary DataFrame."""
    results = []
    skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)

    for name, pipe in pipelines.items():
        cv_out = cross_validate(
            pipe,
            X,
            y,
            cv=skf,
            scoring=["accuracy", "f1_macro"],
            return_train_score=False,
        )

        # At-Risk recall per fold
        at_risk_recalls = []
        for train_idx, val_idx in skf.split(X, y):
            pipe.fit(X.iloc[train_idx], y.iloc[train_idx])
            y_pred = pipe.predict(X.iloc[val_idx])
            recall = recall_score(
                y.iloc[val_idx],
                y_pred,
                labels=["At-Risk"],
                average="macro",
                zero_division=0,
            )
            at_risk_recalls.append(recall)

        results.append(
            {
                "model": name,
                "cv_accuracy": np.mean(cv_out["test_accuracy"]),
                "cv_accuracy_std": np.std(cv_out["test_accuracy"]),
                "cv_f1_macro": np.mean(cv_out["test_f1_macro"]),
                "cv_f1_macro_std": np.std(cv_out["test_f1_macro"]),
                "cv_at_risk_recall": np.mean(at_risk_recalls),
                "cv_at_risk_recall_std": np.std(at_risk_recalls),
            }
        )

    return pd.DataFrame(results).set_index("model")


# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------

def _select_best(cv_df: pd.DataFrame) -> str:
    """
    Select the best model by At-Risk recall (primary), macro-F1 (tie-breaker).
    """
    best = cv_df.sort_values(
        by=["cv_at_risk_recall", "cv_f1_macro"], ascending=False
    ).index[0]
    return best


# ---------------------------------------------------------------------------
# Test-set evaluation
# ---------------------------------------------------------------------------

def _evaluate_on_test(
    pipe: Pipeline,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    label: str,
) -> dict:
    """Fit has already happened; evaluate on the held-out test set."""
    y_pred = pipe.predict(X_test)
    report = classification_report(
        y_test,
        y_pred,
        labels=LABEL_ORDER,
        output_dict=True,
        zero_division=0,
    )
    cm = confusion_matrix(y_test, y_pred, labels=LABEL_ORDER)

    # Confusion matrix figure
    os.makedirs(FIGURES_DIR, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 5))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=LABEL_ORDER)
    disp.plot(ax=ax, colorbar=True, cmap="Blues")
    ax.set_title(f"Confusion Matrix — {label}")
    plt.tight_layout()
    fname = label.replace(" ", "_").lower() + "_confusion_matrix.png"
    fig.savefig(os.path.join(FIGURES_DIR, fname), dpi=150)
    plt.close(fig)

    metrics = {
        "accuracy": report["accuracy"],
        "macro_f1": report["macro avg"]["f1-score"],
        "at_risk_recall": report.get("At-Risk", {}).get("recall", 0.0),
        "per_class": {
            cls: {
                "precision": report[cls]["precision"],
                "recall": report[cls]["recall"],
                "f1": report[cls]["f1-score"],
                "support": report[cls]["support"],
            }
            for cls in LABEL_ORDER
            if cls in report
        },
        "confusion_matrix": cm.tolist(),
    }
    return metrics


# ---------------------------------------------------------------------------
# Main training routine
# ---------------------------------------------------------------------------

def train_feature_set(
    df: pd.DataFrame,
    feature_set: str,
    model_filename: str,
    metrics_filename: str,
    label: str,
) -> dict:
    """
    Train and evaluate all three models on one feature set, save the best.

    Returns the test-set metrics dict for the winning model.
    """
    print(f"\n{'='*60}")
    print(f"  Training: {label} ({feature_set} feature set)")
    print(f"{'='*60}")

    X, y = prepare_dataset(df, feature_set=feature_set)
    print(f"  Dataset shape: {X.shape}, Classes: {dict(y.value_counts())}")

    # Train / test split (stratified, 80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    pipelines = _build_pipelines()

    # Cross-validation
    print("\n  Running 5-fold stratified cross-validation ...")
    cv_df = _cross_validate_models(pipelines, X_train, y_train, cv=5)
    print(cv_df[["cv_accuracy", "cv_f1_macro", "cv_at_risk_recall"]].to_string())

    # Plot CV results
    _plot_cv_results(cv_df, label)

    # Select and retrain best model on full train set
    best_name = _select_best(cv_df)
    print(f"\n  [BEST] Model selected: {best_name}")

    best_pipe = pipelines[best_name]
    best_pipe.fit(X_train, y_train)

    # Evaluate on held-out test set
    metrics = _evaluate_on_test(best_pipe, X_test, y_test, label)
    metrics["best_model"] = best_name
    metrics["feature_set"] = feature_set
    metrics["cv_summary"] = cv_df.reset_index().to_dict(orient="records")

    print(
        f"\n  Test-set  | Accuracy: {metrics['accuracy']:.3f}  "
        f"| Macro-F1: {metrics['macro_f1']:.3f}  "
        f"| At-Risk Recall: {metrics['at_risk_recall']:.3f}"
    )

    # Persist
    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(best_pipe, os.path.join(MODELS_DIR, model_filename))
    with open(os.path.join(MODELS_DIR, metrics_filename), "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    print(f"  Saved model   -> models/{model_filename}")
    print(f"  Saved metrics -> models/{metrics_filename}")

    return metrics


def _plot_cv_results(cv_df: pd.DataFrame, label: str) -> None:
    """Bar chart comparing CV metrics across the three algorithms."""
    os.makedirs(FIGURES_DIR, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    metrics_cols = {
        "cv_accuracy": "CV Accuracy",
        "cv_f1_macro": "CV Macro-F1",
        "cv_at_risk_recall": "CV At-Risk Recall",
    }
    colors = ["#4878CF", "#6ACC65", "#D65F5F"]
    for ax, (col, title) in zip(axes, metrics_cols.items()):
        vals = cv_df[col]
        errs = cv_df[col + "_std"]
        bars = ax.bar(cv_df.index, vals, yerr=errs, color=colors, capsize=5)
        ax.set_title(title)
        ax.set_ylim(0, 1.05)
        ax.set_xticklabels(cv_df.index, rotation=15, ha="right", fontsize=8)
        for bar, v in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                v + 0.02,
                f"{v:.2f}",
                ha="center",
                fontsize=8,
            )

    fig.suptitle(f"Cross-Validation Comparison — {label}", fontsize=12)
    plt.tight_layout()
    fname = label.replace(" ", "_").lower() + "_cv_comparison.png"
    fig.savefig(os.path.join(FIGURES_DIR, fname), dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    df = combine_datasets()
    print(f"Loaded dataset: {df.shape[0]} rows, {df.shape[1]} columns")

    # Duplicate / missing check
    dups = df.duplicated().sum()
    miss = df.isnull().sum().sum()
    print(f"Duplicates: {dups}  |  Missing values: {miss}")

    # Early model (G1-only feature set)
    early_metrics = train_feature_set(
        df,
        feature_set="early",
        model_filename="early_model.joblib",
        metrics_filename="early_metrics.json",
        label="Early Model (G1)",
    )

    # Mid-term model (G1 + G2 feature set)
    mid_metrics = train_feature_set(
        df,
        feature_set="mid",
        model_filename="mid_model.joblib",
        metrics_filename="mid_metrics.json",
        label="Mid-Term Model (G1+G2)",
    )

    # Save schema for the active (early) model used by the app
    save_schema(feature_set="early")

    print("\n[DONE] Training complete. Models saved to models/")
