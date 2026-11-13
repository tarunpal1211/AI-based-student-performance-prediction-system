# System Architecture — AI Student Performance Predictive System

> A decision-support tool that predicts student risk levels (Performing Well / Needs Improvement / At-Risk) using first and second period grades, attendance, and study habits.

---

## High-Level Architecture

```mermaid
flowchart TD
    subgraph DATA["Data Layer"]
        D1["UCI Student Performance Dataset\nstudent-mat.csv · student-por.csv"]
        D2["SQLite / PostgreSQL\nstudent_predictor.db"]
    end

    subgraph ML["ML Pipeline (src/)"]
        T1["data.py\nLoad · Label · Split"]
        T2["train.py\n5-Fold CV\nLR · DT · RF"]
        T3["early_model.joblib\nLogistic Regression"]
        T4["mid_model.joblib\nLogistic Regression"]
        T5["predict.py\nThreshold-based inference\n+ Top Factors"]
        T6["explain.py\nSHAP Values"]
        T7["recommend.py\nIntervention Rules"]
    end

    subgraph API["Backend — FastAPI (api/)"]
        A1["main.py\nApp Factory · Lifespan"]
        A2["auth router\nJWT Register · Login · Refresh"]
        A3["predict router\nSingle · Batch · Export"]
        A4["history router\nPast Predictions"]
        A5["analytics router\nAggregated Stats"]
        A6["recommend router"]
        A7["simulate router"]
        A8["reports router\nPDF / Excel Export"]
        A9["SQLAlchemy ORM\nUser · Student · Prediction\nBatchJob · Recommendation"]
    end

    subgraph UI1["Primary UI — Streamlit (app.py)"]
        S1["Single Student Tab\nForm → Prediction + Gauge"]
        S2["CSV Batch Tab\nUpload → Colour-coded Table"]
    end

    subgraph UI2["Dashboard UI — React (frontend/)"]
        R1["LoginPage\nJWT Auth"]
        R2["DashboardPage\nStats Overview"]
        R3["PredictPage\nSingle Prediction"]
        R4["AtRiskPage\nFlagged Students"]
        R5["HistoryPage\nPast Records"]
        R6["AnalyticsPage\nRecharts Graphs"]
    end

    subgraph INFRA["Infrastructure"]
        I1["Dockerfile"]
        I2["docker-compose.yml"]
        I3[".env / pydantic-settings"]
        I4["Alembic Migrations"]
    end

    D1 --> T1 --> T2 --> T3 & T4
    T3 & T4 --> T5 --> T6 & T7
    T5 --> A3
    T6 --> A3
    T7 --> A3
    A1 --> A2 & A3 & A4 & A5 & A6 & A7 & A8
    A3 & A4 & A5 --> A9 --> D2
    T3 --> S1 & S2
    A3 --> R3
    A4 --> R5
    A5 --> R6
    A9 --> R4
    I3 --> A1
    I4 --> D2
```

---

## Component Breakdown

### 1. ML Pipeline

| File | Responsibility |
|------|---------------|
| `src/data.py` | Loads UCI CSVs, merges maths + Portuguese datasets, creates 3-class label from G3 score |
| `src/train.py` | Runs 5-fold stratified CV across Logistic Regression, Decision Tree, Random Forest; selects winner by At-Risk recall → macro-F1 |
| `src/predict.py` | Threshold-based inference (`AT_RISK_THRESHOLD = 0.45`), feature importance extraction, batch prediction |
| `src/explain.py` | SHAP TreeExplainer / LinearExplainer for per-feature impact values |
| `src/recommend.py` | Rule-based intervention engine — generates high/medium/low priority actions based on prediction category and input values |
| `src/validate.py` | Input sanitisation for single-student forms and CSV uploads |

#### Labelling Rules

| G3 Score | Category |
|----------|----------|
| 14 – 20 | ✅ Performing Well |
| 8 – 13 | ⚠️ Needs Improvement |
| 0 – 7 | 🚨 At-Risk |

#### Model Selection Results

| Model | CV Accuracy | At-Risk Recall | CV Macro-F1 | Selected |
|-------|-------------|---------------|-------------|---------|
| Logistic Regression | 81.2% | **88.8%** | **77.5%** | ✅ Early |
| Decision Tree | 81.8% | 75.0% | 76.6% | — |
| Random Forest | 83.8% | 51.3% | 76.2% | — |

> Random Forest had the highest accuracy but the lowest At-Risk recall — it missed too many struggling students. Logistic Regression was selected because catching At-Risk students is the primary objective.

---

### 2. FastAPI Backend

**Base URL:** `http://localhost:8000`  
**Interactive docs:** `http://localhost:8000/docs`

| Router | Prefix | Key Endpoints |
|--------|--------|--------------|
| Auth | `/api/auth` | `POST /register`, `POST /login`, `POST /refresh`, `GET /me` |
| Predict | `/api/predict` | `POST /single`, `POST /batch-process`, `POST /upload-validate`, `GET /template` |
| History | `/api/history` | `GET /` — paginated past predictions |
| Analytics | `/api/analytics` | Aggregated category distributions and trends |
| Recommend | `/api/recommend` | Rule-based intervention suggestions |
| Simulate | `/api/simulate` | What-if scenario modelling |
| Reports | `/api/reports` | PDF / Excel export |

**Auth flow:** `POST /login` → JWT access token (30 min) + refresh token (7 days) → Bearer header on all protected routes.

#### Database Models

```mermaid
erDiagram
    User {
        UUID id PK
        string email
        string hashed_password
        string full_name
        enum role
        bool is_active
    }
    Student {
        UUID id PK
        string student_id
        UUID created_by FK
    }
    Prediction {
        UUID id PK
        string category
        float confidence
        string feature_set
        string model_name
        UUID student_id FK
        UUID created_by FK
    }
    Recommendation {
        UUID id PK
        string title
        string priority
        UUID prediction_id FK
    }
    BatchJob {
        UUID id PK
        string status
        int total_rows
        int processed_rows
        UUID created_by FK
    }

    User ||--o{ Student : creates
    User ||--o{ Prediction : makes
    User ||--o{ BatchJob : submits
    Student ||--o{ Prediction : has
    Prediction ||--o{ Recommendation : generates
```

---

### 3. Streamlit App (Primary Demo Interface)

```
streamlit run app.py → http://localhost:8501
```

| Tab | Features |
|-----|---------|
| Single Student | Grade / absence / studytime form → animated SVG confidence gauge → top 3 factors → intervention recommendations |
| CSV Batch Upload | Template download → upload → colour-coded risk table → results download |

---

### 4. React Dashboard

```
cd frontend && npm run dev → http://localhost:5173
```

| Page | Route | Description |
|------|-------|-------------|
| Login | `/login` | JWT authentication |
| Dashboard | `/` | At-risk count, category distribution |
| Predict | `/predict` | Single-student form via API |
| At-Risk | `/at-risk` | Filtered list of flagged students |
| History | `/history` | Paginated prediction log |
| Analytics | `/analytics` | Recharts trend graphs |

**State management:** Redux Toolkit  
**API layer:** Axios client in `frontend/src/api/`  
**Auth:** JWT stored in context, attached as Bearer token to every API call

---

### 5. Infrastructure

| File | Purpose |
|------|---------|
| `.env` | Local config (SQLite DB, dev secret key) |
| `.env.example` | Template for production setup (PostgreSQL) |
| `Dockerfile` | Containerises the FastAPI backend |
| `docker-compose.yml` | Orchestrates API + PostgreSQL |
| `alembic.ini` + `migrations/` | Database schema versioning |

---

## Data Flow — Single Prediction

```mermaid
sequenceDiagram
    participant U as Educator
    participant ST as Streamlit / React
    participant API as FastAPI
    participant ML as ML Pipeline
    participant DB as SQLite / PostgreSQL

    U->>ST: Enter G1, absences, failures, studytime
    ST->>API: POST /api/predict/single (Bearer token)
    API->>ML: predict_one(model, input)
    ML->>ML: Compute probabilities
    ML->>ML: Apply AT_RISK_THRESHOLD (0.45)
    ML->>ML: Extract top 3 factors
    ML->>API: {category, confidence, factors}
    API->>ML: generate_recommendations(category, input)
    API->>DB: INSERT Prediction + Recommendations
    API->>ST: PredictionResponse
    ST->>U: Risk badge + gauge + factors + actions
```

---

## Running the Project

### Option A — Streamlit only (simplest)
```bash
pip install -r requirements.txt
python src/train.py        # only needed once
streamlit run app.py
```

### Option B — Full stack
```bash
# Terminal 1
uvicorn api.main:app --reload

# Terminal 2
cd frontend && npm install && npm run dev
```

### Option C — Docker
```bash
docker-compose up
```

---

## Test Coverage

| Suite | Tests | Status |
|-------|-------|--------|
| `test_data.py` | 5 | ✅ Pass |
| `test_predict.py` | 8 | ✅ Pass |
| `test_validate.py` | 16 | ✅ Pass |
| `test_api_auth.py` | 3 | ✅ Pass |
| `test_api_predict.py` | 6 | ✅ Pass |
| **Total** | **68** | ✅ **0 failures** |

```bash
pytest tests/ -v   # run all 68 tests
```

---

## Limitations

- **Dataset size:** ~1,000 records from one school in Portugal. Results may not generalise to other educational contexts.
- **Features available:** Only grades, absences, study time, and past failures. Assignment scores and coursework were not in the UCI dataset.
- **Decision support only:** Predictions should complement, not replace, educator judgment.
- **Demographic fairness:** Sex, age, and other demographic columns are excluded from model inputs to reduce bias.
