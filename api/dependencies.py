"""
api/dependencies.py
-------------------
Shared FastAPI dependencies:
  get_db()           - yields an async DB session
  get_current_user() - decodes JWT and returns the active User
  require_role()     - factory that creates a role-check dependency
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.database import get_session
from api.models.user import User, UserRole

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    description="Enter your registered **Email** in the username field and your password.",
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async for session in get_session():
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode a Bearer JWT and return the corresponding active User."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_role(*roles: UserRole) -> Callable:
    """Dependency factory restricting access to users with specified role(s)."""

    async def _check_role(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {[r.value for r in roles]}.",
            )
        return current_user

    return _check_role
