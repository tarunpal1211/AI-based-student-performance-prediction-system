"""
src/explain.py
--------------
SHAP-based and model-intrinsic explainability for the Student Performance Predictor.

Functions
---------
get_shap_values(model, input_df)
    Compute per-feature SHAP values for a single prediction.
    Returns a dict {feature_name: shap_value} or empty dict on failure.
explain_prediction(model, input_dict, category, confidence)
    Produce rich, directional Explainable AI (XAI) feature attributions.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline


FEATURE_LABELS = {
    "absences": "School Absences",
    "G1": "First Period Grade (G1)",
    "G2": "Second Period Grade (G2)",
    "failures": "Past Course Failures",
    "studytime": "Weekly Study Time",
    "assignment_rate": "Assignment Completion Rate",
    "assessment_trend": "Assessment Score Trend",
}


def get_shap_values(model: Pipeline, input_df: pd.DataFrame) -> dict[str, float]:
    """
    Compute SHAP values for a single-row prediction.

    Supports RandomForestClassifier (TreeExplainer) and
    LogisticRegression (LinearExplainer). Falls back to an empty dict
    if SHAP is not installed or computation fails.
    """
    try:
        import shap
    except ImportError:
        return {}

    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression

        estimator = model[-1]
        feature_names = list(input_df.columns)

        # Transform input through all steps except the classifier
        X_transformed = input_df.copy().values.astype(float)
        for _, step in model.steps[:-1]:
            X_transformed = step.transform(X_transformed)

        if isinstance(estimator, RandomForestClassifier):
            explainer = shap.TreeExplainer(estimator)
            shap_vals = explainer.shap_values(X_transformed)
            if isinstance(shap_vals, list):
                avg_shap = np.mean([np.abs(sv) for sv in shap_vals], axis=0)[0]
            elif isinstance(shap_vals, np.ndarray) and len(shap_vals.shape) == 3:
                avg_shap = np.mean(np.abs(shap_vals), axis=-1)[0]
            else:
                avg_shap = np.abs(shap_vals[0])

        elif isinstance(estimator, LogisticRegression):
            explainer = shap.LinearExplainer(
                estimator, X_transformed, feature_perturbation="interventional"
            )
            shap_vals = explainer.shap_values(X_transformed)
            if isinstance(shap_vals, list):
                avg_shap = np.mean([np.abs(sv) for sv in shap_vals], axis=0)[0]
            elif isinstance(shap_vals, np.ndarray) and len(shap_vals.shape) == 3:
                avg_shap = np.mean(np.abs(shap_vals), axis=-1)[0]
            else:
                avg_shap = np.abs(shap_vals[0])

        else:
            avg_shap = np.ones(len(feature_names))

        return {feat: float(val) for feat, val in zip(feature_names, avg_shap)}

    except Exception:
        return {}


def explain_prediction(
    model: Pipeline,
    input_dict: dict,
    category: str,
    confidence: float,
) -> dict:
    """
    Produce rich, directional Explainable AI (XAI) feature attributions.

    Returns:
    {
        "summary": "...",
        "contributions": [
            {
                "feature": "G1",
                "label": "First Period Grade (G1)",
                "value": 6,
                "importance": 45.2,
                "direction": "increased_risk",
                "impact": "negative",
                "description": "Low first period grade (6/20) increased academic failure risk."
            }, ...
        ],
        "risk_factors": [...],
        "protective_factors": [...]
    }
    """
    expected_cols = getattr(model, "feature_names_in_", None)
    if expected_cols is None:
        for _, step in getattr(model, "steps", []):
            cols = getattr(step, "feature_names_in_", None)
            if cols is not None:
                expected_cols = cols
                break

    feature_names = list(expected_cols) if expected_cols is not None else list(input_dict.keys())
    row_vals = [input_dict.get(c, 0) for c in feature_names]
    input_df = pd.DataFrame([row_vals], columns=feature_names)

    # 1. Base SHAP or linear attribution calculation
    raw_shap = get_shap_values(model, input_df)

    estimator = model[-1]
    classes = list(getattr(model, "classes_", getattr(estimator, "classes_", [])))
    class_idx = classes.index("At-Risk") if "At-Risk" in classes else 0

    attributions = {}
    if hasattr(estimator, "coef_"):
        try:
            X_trans = input_df.copy().values.astype(float)
            for _, step in model.steps[:-1]:
                X_trans = step.transform(X_trans)
            # Logit attribution for At-Risk class
            coefs = estimator.coef_[class_idx]
            linear_attr = X_trans[0] * coefs
            for feat, a in zip(feature_names, linear_attr):
                attributions[feat] = float(a)
        except Exception:
            pass

    contributions = []
    total_abs = sum(abs(attributions.get(f, raw_shap.get(f, 1.0))) for f in feature_names) or 1.0

    for feat in feature_names:
        val = input_dict.get(feat, 0)
        label = FEATURE_LABELS.get(feat, feat.replace("_", " ").title())
        attr_val = attributions.get(feat, 0.0)

        # Domain-calibrated risk direction
        # Positive attribution to At-Risk logit indicates higher risk
        if feat == "G1":
            if val <= 5:
                is_risk = True
                desc = f"First-period grade {val}/20 is critically low (0–5/20 — Very Bad), indicating acute academic vulnerability."
            elif val <= 10:
                is_risk = True
                desc = f"First-period grade {val}/20 is low (6–10/20 — Bad), contributing directly to academic struggle."
            elif val <= 15:
                is_risk = (category in ["At-Risk", "Needs Improvement"])
                desc = f"First-period grade {val}/20 is an average-level grade (11–15/20), meeting satisfactory baseline."
            else:
                is_risk = False
                desc = f"First-period grade {val}/20 is strong (16–20/20), providing an excellent academic buffer."
        elif feat == "G2":
            if val <= 5:
                is_risk = True
                desc = f"Second-period grade {val}/20 is critically low (0–5/20 — Very Bad), indicating acute academic crisis."
            elif val <= 10:
                is_risk = True
                desc = f"Second-period grade {val}/20 is low (6–10/20 — Bad), reflecting persistent academic struggle."
            elif val <= 15:
                is_risk = (category in ["At-Risk", "Needs Improvement"])
                desc = f"Second-period grade {val}/20 is an average-level grade (11–15/20), maintaining satisfactory progress."
            else:
                is_risk = False
                desc = f"Second-period grade {val}/20 is strong (16–20/20), sustaining high academic achievement."
        elif feat == "absences":
            is_risk = val > 6
            desc = f"High absence count ({val} days missed) significantly elevates failure probability." if is_risk else f"Steady attendance ({val} missed days) supports learning continuity."
        elif feat == "failures":
            is_risk = val >= 1
            desc = f"History of past failures ({val}) is a strong indicator of course vulnerability." if is_risk else "Zero prior failures reduces systemic academic risk."
        elif feat == "studytime":
            is_risk = val < 2
            desc = f"Reported study time (<2 hrs/week) limits topic mastery." if is_risk else f"Dedicated study effort ({val} / 4 level) builds subject retention."
        elif feat == "assignment_rate":
            is_risk = val < 70
            desc = f"Low assignment completion ({val}%) highlights engagement gaps." if is_risk else f"High homework completion ({val}%) reinforces concepts."
        elif feat == "assessment_trend":
            is_risk = val < 0
            desc = "Declining recent test trend indicates worsening performance." if is_risk else "Stable/improving recent quiz trajectory demonstrates resilience."
        else:
            is_risk = attr_val > 0
            desc = f"{label} (value: {val})"

        # Weight calculation percentage
        weight_score = abs(attributions.get(feat, raw_shap.get(feat, 1.0)))
        importance_pct = round((weight_score / total_abs) * 100, 1)

        contributions.append({
            "feature": feat,
            "label": label,
            "value": val,
            "importance": importance_pct,
            "direction": "increased_risk" if is_risk else "reduced_risk",
            "impact": "negative" if is_risk else "positive",
            "description": desc,
        })

    # Sort descending by importance
    contributions.sort(key=lambda x: x["importance"], reverse=True)

    risk_factors = [c for c in contributions if c["impact"] == "negative"]
    protective_factors = [c for c in contributions if c["impact"] == "positive"]

    # Generate plain-English executive narrative
    conf_pct = "99.5%" if confidence >= 0.995 else f"{round(confidence * 100, 1)}%"
    if category == "At-Risk":
        top_risks = [f"{rf['label'].lower()} ({rf['value']})" for rf in risk_factors[:2]]
        risk_str = " and ".join(top_risks) if top_risks else "multiple warning thresholds"
        narrative = (
            f"The student was classified as At-Risk with {conf_pct} confidence primarily driven by {risk_str}. "
            "Immediate targeted academic intervention and attendance check-ins are recommended."
        )
    elif category == "Needs Improvement":
        top_risks = [f"{rf['label'].lower()}" for rf in risk_factors[:2]]
        risk_str = " and ".join(top_risks) if top_risks else "moderate inconsistencies"
        narrative = (
            f"The student is classified as Needs Improvement ({conf_pct} confidence). "
            f"While maintaining baseline performance, {risk_str} suggests vulnerability to dropping into the At-Risk tier."
        )
    else:
        top_prot = [f"{pf['label'].lower()}" for pf in protective_factors[:2]]
        prot_str = " and ".join(top_prot) if top_prot else "consistent academic inputs"
        narrative = (
            f"The student is Performing Well ({conf_pct} confidence) anchored by strong {prot_str}. "
            "Continue fostering self-directed learning and enrichment activities."
        )

    return {
        "summary": narrative,
        "contributions": contributions,
        "risk_factors": risk_factors,
        "protective_factors": protective_factors,
        "shap_values": raw_shap,
    }
