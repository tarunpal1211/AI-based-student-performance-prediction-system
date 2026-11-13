# Student Performance Predictor

> **Decision-support tool** — predicts whether a student is **Performing Well**, **Needs Improvement**, or **At-Risk**, using first-period (G1) and optionally second-period (G2) data.

---

## What This Project Is

This Streamlit application trains scikit-learn models on the [UCI Student Performance dataset](https://archive.ics.uci.edu/dataset/320/student+performance) and lets educators enter a single student's data or upload a CSV to get instant risk assessments with explanations.

**Two models are trained:**

| Model | Features used | Purpose |
|-------|--------------|---------|
| Early model | G1, absences, failures, studytime | Flag at-risk students after the first grading period |
| Mid-term model | G1, G2, absences, failures, studytime | More accurate prediction midway through the course |

The **app uses the early model** by default.

---

## Setup

### Prerequisites

- Python 3.10 or higher
- `pip`

### 1. Clone the repository

```bash
git clone https://github.com/your-username/student-performance-predictor
cd student-performance-predictor
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Download the Dataset

```bash
python src/download_data.py
```

This downloads `student-mat.csv` and `student-por.csv` from the UCI repository into `data/raw/`.

> **Manual alternative:** Download from https://archive.ics.uci.edu/dataset/320/student+performance and place the two CSV files in `data/raw/`.

---

## Train the Models

```bash
python src/train.py
```

This will:
1. Load and combine the UCI dataset files
2. Run 5-fold stratified cross-validation on Logistic Regression, Decision Tree, and Random Forest
3. Select the best model (by At-Risk recall, with macro-F1 as tie-breaker)
4. Evaluate on a held-out 20% test set
5. Save models and metrics to `models/`
6. Save figures to `reports/figures/`

**Expected output files:**

```
models/
  early_model.joblib       ← used by the app
  mid_model.joblib
  early_metrics.json
  mid_metrics.json
  schema.json
reports/figures/
  early_model_g1__confusion_matrix.png
  early_model_g1__cv_comparison.png
  mid-term_model_g1+g2__confusion_matrix.png
  grade_distributions.png
  class_balance.png
  ...
```

---

## Run the App

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

### Single Student Tab

Fill in:
- **G1** — first period grade (0–20)
- **Absences** — total missed days (0–93)
- **Study time** — weekly study time (coded 1–4)
- **Past failures** — number of past class failures (0–4)

Click **Predict** to see the category, confidence, and top three contributing factors.

### CSV Upload Tab

1. Download the **CSV Template**
2. Fill it in with one student per row
3. Upload the CSV
4. Download the **results table** (sorted by risk level)

---

## Run the Exploration Script

```bash
python notebooks/01_exploration.py
```

Saves EDA figures to `reports/figures/`.

---

## Run Tests

```bash
pytest tests/ -v
```

All tests run without a trained model (they use mock pipelines where needed).

---

## Project Structure

```
student-performance-predictor/
  app.py                     Streamlit application
  requirements.txt           Pinned dependencies
  README.md
  data/
    raw/                     UCI CSV files (git-ignored)
  src/
    data.py                  load_data, make_label, prepare_dataset
    train.py                 Model training and comparison
    predict.py               predict_one, top_factors, predict_batch
    validate.py              Form and CSV validation
    download_data.py         Dataset download helper
  models/                    Saved models and metrics (git-ignored)
  notebooks/
    01_exploration.py        EDA script
  reports/figures/           Plots and confusion matrices
  tests/
    test_data.py
    test_validate.py
    test_predict.py
```

---

## Labelling Rules

| G3 Score | Category |
|----------|----------|
| 14 – 20 | ✅ Performing Well |
| 8 – 13 | ⚠️ Needs Improvement |
| 0 – 7 | 🚨 At-Risk |

---

## Limitations

- **Dataset size**: ~1,000 records from a single school in Portugal. Results may not generalise to other contexts.
- **Assignment scores**: The UCI dataset does not contain assignment or coursework scores; these inputs were not available for modelling.
- **Prediction is decision support only**: Educators should use their own judgment alongside model outputs.
- **Demographic fairness**: Sex, age, and other demographic columns are excluded from model inputs to reduce bias.

---

## Team

| Role | Owns |
|------|------|
| Data and training | src/data.py, src/train.py, notebooks/ |
| App and UI | app.py |
| Validation and tests | src/validate.py, tests/ |
| Explainability and report | src/predict.py, reports/ |
| Integration and submission | README.md, requirements.txt |
