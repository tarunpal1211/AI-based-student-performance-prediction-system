# Student Performance Predictor — Project Report

**Course:** [Your Course Name]  
**Submission Date:** [Your Deadline]  
**Team Members:** [Names]  
**Dataset:** UCI Student Performance Dataset (math + Portuguese subjects)

---

## 1. Problem Statement

Early identification of at-risk students is critical for timely academic intervention. This project builds a machine-learning tool that predicts a student's performance category — **Performing Well**, **Needs Improvement**, or **At-Risk** — from early-semester data (first-period grade, absences, study habits, and past failures). The tool is deployed as a Streamlit web application accessible to faculty.

---

## 2. Dataset

**Source:** [UCI Machine Learning Repository — Student Performance](https://archive.ics.uci.edu/dataset/320/student+performance)

| Property | Value |
|----------|-------|
| Files | student-mat.csv, student-por.csv |
| Combined records | ~1,000 rows |
| Original features | 33 columns |
| Target column | G3 (final period grade, 0–20) |
| Delimiter | Semicolon (`;`) |

### Key columns used

| Column | Description | Range |
|--------|-------------|-------|
| `G1` | First period grade | 0–20 |
| `G2` | Second period grade | 0–20 |
| `G3` | Final grade (label source) | 0–20 |
| `absences` | School absences | 0–93 |
| `studytime` | Weekly study time (coded) | 1–4 |
| `failures` | Past class failures | 0–4 |

### Dropped columns

- **Demographic columns** (`sex`, `age`, `address`, etc.) — excluded to reduce demographic bias.
- **G3** — used only to derive labels; removed from feature inputs.
- **Assignment scores** — the UCI dataset does **not** contain assignment or coursework scores. This input was planned in the original spec but was unavailable in the dataset. This limitation is noted in Section 6.

---

## 3. Labelling Scheme

The three-class target label is derived from G3 using the following rules:

| G3 Score | Label | Rationale |
|----------|-------|-----------|
| 14 – 20 | Performing Well | Above average (70%+ on a 0–20 scale) |
| 8 – 13 | Needs Improvement | Mid-range, at risk of falling further |
| 0 – 7 | At-Risk | Below 40% — critical intervention needed |

**Class distribution (approximate):**

| Label | Count | % |
|-------|-------|---|
| Performing Well | ~350 | ~36% |
| Needs Improvement | ~450 | ~46% |
| At-Risk | ~170 | ~18% |

At-Risk is the smallest class, as anticipated. All models used `class_weight="balanced"` to compensate.

---

## 4. Feature Engineering

Two feature sets were defined:

**Early model (available after first grading period):**
- `absences`, `G1`, `failures`, `studytime`

**Mid-term model (available at mid-semester):**
- `absences`, `G1`, `failures`, `studytime`, `G2`

Column names and ordering are stored in `models/schema.json` to ensure the app and training code agree.

---

## 5. Modelling

### Approach

- **Train/test split:** 80/20, stratified by label class.
- **Cross-validation:** 5-fold stratified, on the training set only.
- **Three algorithms evaluated:**
  1. Logistic Regression (with StandardScaler, balanced class weights)
  2. Decision Tree (max depth 6, balanced class weights)
  3. Random Forest (200 trees, balanced class weights)

### Model selection criterion

**Primary:** At-Risk recall — we prefer to over-flag at-risk students rather than miss them.  
**Tie-breaker:** Macro-F1.

### Cross-validation results (Early Model)

| Model | CV Accuracy | CV Macro-F1 | CV At-Risk Recall |
|-------|------------|-------------|-------------------|
| Logistic Regression | 0.737 | 0.700 | **0.838** |
| Decision Tree | 0.729 | 0.686 | 0.750 |
| Random Forest | 0.757 | 0.689 | 0.550 |

**Winner: Logistic Regression** — highest At-Risk recall (0.838).

### Test-set results (Early Model)

| Metric | Value |
|--------|-------|
| Accuracy | 0.708 |
| Macro F1 | 0.659 |
| At-Risk Recall | **0.700** |
| At-Risk Precision | (see early_metrics.json) |

**Mid-term model (G1+G2) test-set results:**

| Metric | Value |
|--------|-------|
| Accuracy | 0.809 |
| Macro F1 | 0.776 |
| At-Risk Recall | **0.900** |

### Confusion Matrix

![Early Model Confusion Matrix](figures/early_model_g1__confusion_matrix.png)

*(generated after training)*

---

## 6. Explainability

For each prediction the app surfaces the **top three contributing features** in plain English:

| Feature value | Plain-English description |
|--------------|--------------------------|
| High absences | "High number of classes missed" |
| Low G1 | "Low first-period grade" |
| High failures | "History of past class failures" |

Feature importances are extracted from `feature_importances_` (Random Forest) or mean absolute coefficients (Logistic Regression).

---

## 7. Application

The Streamlit app (`app.py`) provides:

- **Single-student form** — four inputs with range validation; shows category badge (color-coded), confidence percentage, and top factors.
- **CSV upload** — row-level validation, results sorted by risk (At-Risk first), downloadable output CSV.
- **Error handling** — all invalid inputs show a clear message; the app never crashes on bad data.
- **Model loading** — the pipeline is cached at startup (`st.cache_resource`) and not reloaded on every interaction.

---

## 8. Testing

| Test file | What is covered |
|-----------|----------------|
| `tests/test_data.py` | `make_label` boundary conditions, `prepare_dataset` |
| `tests/test_validate.py` | Form validation, CSV validation, template generation |
| `tests/test_predict.py` | `predict_one` returns valid category/confidence/factors |

Run with:
```bash
pytest tests/ -v
```

---

## 9. Limitations

1. **Dataset size:** ~1,000 records from a single school in Portugal. The model has not been validated on other populations or education systems.
2. **Assignment scores:** The original spec mentioned assignment scores as an input. The UCI dataset does not contain assignment or coursework data; this input was dropped.
3. **Single-school bias:** All students attended the same school, limiting generalisability.
4. **Label thresholds:** The thresholds (14, 8) are rule-based rather than data-driven; a different school may require recalibration.
5. **Static model:** The model does not update as new student data arrives.
6. **Decision support only:** Predictions should supplement — not replace — educator judgment.

---

## 10. References

- Cortez, P., & Silva, A. (2008). *Using data mining to predict secondary school student performance.* Proceedings of the 5th Annual Future Business Technology Conference.
- UCI ML Repository: https://archive.ics.uci.edu/dataset/320/student+performance
- scikit-learn documentation: https://scikit-learn.org/stable/
- Streamlit documentation: https://docs.streamlit.io/
