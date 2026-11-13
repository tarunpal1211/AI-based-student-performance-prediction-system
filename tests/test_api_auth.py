"""
tests/test_api_auth.py
----------------------
Unit and integration tests for FastAPI authentication and authorization.
"""

import pytest
from pydantic import ValidationError
from api.schemas.auth import UserCreate, UserLogin
from api.models.user import UserRole


def test_user_create_schema_valid():
    user = UserCreate(
        email="teacher@school.edu",
        password="securePassword123",
        full_name="Jane Doe",
        role=UserRole.teacher,
    )
    assert user.email == "teacher@school.edu"
    assert user.role == UserRole.teacher


def test_user_create_short_password():
    with pytest.raises(ValidationError):
        UserCreate(
            email="teacher@school.edu",
            password="short",
            full_name="Jane Doe",
        )


def test_user_login_schema():
    login = UserLogin(email="teacher@school.edu", password="mypassword")
    assert login.email == "teacher@school.edu"
