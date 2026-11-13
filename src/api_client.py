"""
src/api_client.py
-----------------
Helper client for Streamlit (or other frontends) to communicate with the FastAPI backend.
Falls back seamlessly to local ML inference if the FastAPI backend is offline.
"""

from __future__ import annotations
import os
import requests
from typing import Optional

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")


def is_backend_online(timeout: float = 1.0) -> bool:
    """Check if the FastAPI backend service is reachable."""
    try:
        resp = requests.get(f"{API_BASE_URL.replace('/api', '')}/health", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


def login(username: str = "teacher@school.edu", password: str = "Teacher@123") -> Optional[str]:
    """Login and return JWT access token."""
    try:
        resp = requests.post(
            f"{API_BASE_URL}/auth/login",
            data={"username": username, "password": password},
            timeout=3.0,
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except Exception:
        pass
    return None


def predict_single_api(payload: dict, token: Optional[str] = None) -> Optional[dict]:
    """Call the backend POST /api/predict/single endpoint."""
    try:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        resp = requests.post(f"{API_BASE_URL}/predict/single", json=payload, headers=headers, timeout=5.0)
        if resp.status_code in (200, 201):
            return resp.json()
    except Exception:
        pass
    return None


def get_recommendations_api(prediction_id: str, token: Optional[str] = None) -> Optional[list]:
    """Fetch personalized recommendations from GET /api/recommend/{prediction_id}."""
    try:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        resp = requests.get(f"{API_BASE_URL}/recommend/{prediction_id}", headers=headers, timeout=5.0)
        if resp.status_code == 200:
            return resp.json().get("recommendations", [])
    except Exception:
        pass
    return None
