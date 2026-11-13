# Student Performance Predictor — React Frontend

A React + TypeScript dashboard for the AI-based Student Performance Predictive System. Communicates with the FastAPI backend to provide educators with real-time risk assessments, batch predictions, and intervention recommendations.

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| React 18 + TypeScript | UI framework |
| Vite | Build tool & dev server |
| Redux Toolkit | Global state management |
| React Router | Client-side routing |
| Recharts | Analytics charts |
| Axios | API communication |
| Lucide React | Icons |

---

## Pages

| Page | Route | Description |
|------|-------|-------------|
| Login | `/login` | JWT authentication |
| Dashboard | `/` | Overview stats and at-risk summary |
| Predict | `/predict` | Single student prediction form |
| At-Risk | `/at-risk` | List of flagged students |
| History | `/history` | Past prediction records |
| Analytics | `/analytics` | Charts and performance trends |

---

## Setup

### Prerequisites
- Node.js 18+
- FastAPI backend running at `http://localhost:8000`

### Install & Run

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### Build for Production

```bash
npm run build
# Output in frontend/dist/
```

---

## Environment

The frontend reads the API base URL from `frontend/.env`:

```
VITE_API_BASE_URL=http://localhost:8000
```

The `.env` file is pre-configured for local development.

---

## Connecting to the Backend

Make sure the FastAPI server is running before starting the frontend:

```bash
# From project root
uvicorn api.main:app --reload
```

Default credentials (seeded on first run):
- **Admin:** `admin@school.edu` / `admin123`
- **Teacher:** `teacher@school.edu` / `teacher123`

