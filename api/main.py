"""
api/main.py
-----------
FastAPI application factory.

Models are loaded once at startup and stored in app.state.models so that
all routers can access them via request.app.state.models[feature_set].

Run with:
    uvicorn api.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import joblib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import get_settings
from api.routers import auth, predict, history, analytics, recommend, simulate, reports

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML models and ensure database tables and seed users exist."""
    # 1. Initialize DB tables & seed admin/teacher if DB is reachable
    try:
        from api.init_db import init_db
        await init_db()
    except Exception as exc:
        print(f"  Notice: DB initialization skipped or deferred: {exc}")

    # 2. Load ML models
    app.state.models = {}
    for feature_set, path in [
        ("early", settings.early_model_path),
        ("mid", settings.mid_model_path),
    ]:
        try:
            app.state.models[feature_set] = joblib.load(path)
            print(f"  Loaded '{feature_set}' model from {path}")
        except FileNotFoundError:
            print(f"  Warning: Model not found at {path}")
        except Exception as exc:
            print(f"  Warning: Could not load '{feature_set}' model: {exc}")

    yield

    app.state.models.clear()
    print("Models unloaded.")



from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "FastAPI backend for the AI-based Student Performance Predictor.\n\n"
        "Provides prediction, history, analytics, recommendations, what-if "
        "simulation, and report export - secured with JWT and role-based access."
    ),
    lifespan=lifespan,
    docs_url=None,  # Handled by custom route below
    redoc_url="/redoc",
)

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    html = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=settings.app_name + " - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )
    # Inject JavaScript to dynamically replace the word 'username' with 'Email'
    custom_script = """
    <script>
    const observer = new MutationObserver(() => {
        document.querySelectorAll('label').forEach(label => {
            if (label.innerText && label.innerText.trim().toLowerCase() === 'username:') {
                label.innerText = 'Email:';
            }
        });
        document.querySelectorAll('input[name="username"]').forEach(input => {
            input.setAttribute('placeholder', 'Enter registered Email (e.g. tarun@example.com)');
        });
    });
    observer.observe(document.body, { childList: true, subtree: true });
    </script>
    </body>
    """
    body_content = html.body.decode("utf-8").replace("</body>", custom_script)
    return HTMLResponse(content=body_content)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(predict.router, prefix="/api/predict", tags=["Predictions"])
app.include_router(history.router, prefix="/api/history", tags=["History"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(recommend.router, prefix="/api/recommend", tags=["Recommendations"])
app.include_router(simulate.router, prefix="/api/simulate", tags=["Simulation"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "models_loaded": list(app.state.models.keys()) if hasattr(app.state, "models") else [],
    }
