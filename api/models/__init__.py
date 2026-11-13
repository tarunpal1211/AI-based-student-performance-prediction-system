# api/models/__init__.py
from api.models.base import Base
from api.models.user import User, UserRole
from api.models.student import Student
from api.models.prediction import Prediction, BatchJob
from api.models.recommendation import Recommendation

__all__ = [
    "Base",
    "User",
    "UserRole",
    "Student",
    "Prediction",
    "BatchJob",
    "Recommendation",
]
