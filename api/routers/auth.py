"""
api/routers/auth.py
-------------------
Authentication endpoints:
  POST /api/auth/register   Register a new user
  POST /api/auth/login      Login -> returns JWT tokens
  POST /api/auth/refresh    Refresh access token
  GET  /api/auth/me         Current user profile
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.database import get_session
from api.dependencies import get_current_user
from api.models.user import User, UserRole
from api.schemas.auth import (
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)

router = APIRouter()
settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(data: dict, expires_delta: timedelta) -> str:
    payload = {**data, "exp": datetime.now(timezone.utc) + expires_delta}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    body: UserCreate,
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    user = User(
        email=body.email,
        hashed_password=_hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive JWT tokens",
)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(User).where(User.email == form.username))
    user: User | None = result.scalar_one_or_none()

    if user is None or not _verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact an administrator.",
        )

    access_token = _create_token(
        {"sub": str(user.id), "role": user.role.value, "type": "access"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh_token = _create_token(
        {"sub": str(user.id), "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange a refresh token for a new token pair",
)
async def refresh_token(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_session),
):
    try:
        payload = jwt.decode(
            body.refresh_token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token.")
        user_id: str = payload["sub"]
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )

    access_token = _create_token(
        {"sub": str(user.id), "role": user.role.value, "type": "access"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    new_refresh = _create_token(
        {"sub": str(user.id), "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )
    return TokenResponse(access_token=access_token, refresh_token=new_refresh)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
