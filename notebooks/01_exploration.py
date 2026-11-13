"""
notebooks/01_exploration.py
----------------------------
Exploration script — run as a plain Python file or convert to a Jupyter notebook.

Produces figures under reports/figures/:
  - grade_distributions.png
  - feature_vs_outcome.png
  - class_balance.png
  - correlation_heatmap.png

Usage
-----
    python notebooks/01_exploration.py
"""

import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.data import combine_datasets, make_label, LABEL_ORDER

FIGURES_DIR = os.path.join(ROOT, "reports", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
print("Loading data …")
df = combine_datasets()
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print(f"\nMissing values:\n{df.isnull().sum()[df.isnull().sum() > 0]}")
print(f"Duplicate rows: {df.duplicated().sum()}")

# Apply labels
df["label"] = df["G3"].apply(make_label)

# ---------------------------------------------------------------------------
# 1. Class balance
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 4))
counts = df["label"].value_counts()
colors = ["#e74c3c", "#f39c12", "#2ecc71"]
counts[LABEL_ORDER].plot(kind="bar", ax=ax, color=colors, edgecolor="white")
ax.set_title("Class Distribution (G3-derived labels)")
ax.set_xlabel("Performance Category")
ax.set_ylabel("Number of Students")
ax.set_xticklabels(LABEL_ORDER, rotation=0)
for bar, count in zip(ax.patches, counts[LABEL_ORDER]):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 2,
        str(count),
        ha="center",
        fontsize=10,
    )
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "class_balance.png"), dpi=150)
plt.close(fig)
print(f"\nClass counts:\n{counts[LABEL_ORDER]}")

# ---------------------------------------------------------------------------
# 2. Grade distributions
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(14, 4))
for ax, col in zip(axes, ["G1", "G2", "G3"]):
    sns.histplot(df[col], bins=21, kde=True, ax=ax, color="#4878CF")
    ax.set_title(f"{col} Distribution")
    ax.set_xlabel("Grade (0-20)")
    ax.axvline(df[col].mean(), color="red", linestyle="--", label=f"Mean={df[col].mean():.1f}")
    ax.legend()
plt.suptitle("Grade Distributions (G1, G2, G3)", fontsize=13)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "grade_distributions.png"), dpi=150)
plt.close(fig)

# ---------------------------------------------------------------------------
# 3. Feature distributions
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(14, 4))
for ax, col in zip(axes, ["absences", "studytime", "failures"]):
    if df[col].nunique() <= 10:
        df[col].value_counts().sort_index().plot(kind="bar", ax=ax, color="#6ACC65", edgecolor="white")
    else:
        sns.histplot(df[col], bins=20, ax=ax, color="#6ACC65")
    ax.set_title(f"{col} Distribution")
plt.suptitle("Key Feature Distributions", fontsize=13)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "feature_distributions.png"), dpi=150)
plt.close(fig)

# ---------------------------------------------------------------------------
# 4. Features vs. Outcome (box plots)
# ---------------------------------------------------------------------------
features = ["absences", "G1", "studytime", "failures"]
fig, axes = plt.subplots(1, 4, figsize=(16, 5))
pal = {"At-Risk": "#e74c3c", "Needs Improvement": "#f39c12", "Performing Well": "#2ecc71"}
for ax, feat in zip(axes, features):
    sns.boxplot(
        data=df,
        x="label",
        y=feat,
        hue="label",
        order=LABEL_ORDER,
        palette=pal,
        legend=False,
        ax=ax,
    )
    ax.set_title(f"{feat} vs. Outcome")
    ax.set_xlabel("")
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["At-Risk", "Needs\nImprov.", "Perf.\nWell"], fontsize=8)
plt.suptitle("Feature Distributions by Performance Category", fontsize=13)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "feature_vs_outcome.png"), dpi=150)
plt.close(fig)

# ---------------------------------------------------------------------------
# 5. Correlation heatmap (numeric features only)
# ---------------------------------------------------------------------------
numeric_cols = ["absences", "G1", "G2", "G3", "studytime", "failures",
                "age", "freetime", "goout", "Dalc", "Walc", "health"]
available = [c for c in numeric_cols if c in df.columns]
fig, ax = plt.subplots(figsize=(10, 8))
corr = df[available].corr()
sns.heatmap(
    corr,
    ax=ax,
    annot=True,
    fmt=".2f",
    cmap="RdYlGn",
    center=0,
    square=True,
    linewidths=0.5,
)
ax.set_title("Correlation Heatmap (Numeric Features)")
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "correlation_heatmap.png"), dpi=150)
plt.close(fig)

print(f"\n[OK] All figures saved to {FIGURES_DIR}")
print("\nKey observations:")
print(f"  - At-Risk students: {(df['label']=='At-Risk').sum()}")
print(f"  - Needs Improvement: {(df['label']=='Needs Improvement').sum()}")
print(f"  - Performing Well: {(df['label']=='Performing Well').sum()}")
print(f"  - Mean absences: {df['absences'].mean():.1f}")
print(f"  - G1-G3 correlation: {df['G1'].corr(df['G3']):.3f}")
