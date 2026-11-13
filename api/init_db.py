"""
api/init_db.py
--------------
Database initialization and default seed data.
Can be run on FastAPI lifespan startup or directly via:
    python -m api.init_db
"""

from __future__ import annotations

import asyncio
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import AsyncSessionLocal, engine
from api.models.base import Base
from api.models.user import User, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def init_db():
    """Create all tables and seed default admin & teacher accounts if not present."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables verified/created.")

    async with AsyncSessionLocal() as session:
        # Check if admin exists
        admin_q = await session.execute(
            select(User).where(User.email == "admin@school.edu")
        )
        if admin_q.scalar_one_or_none() is None:
            admin_user = User(
                email="admin@school.edu",
                hashed_password=pwd_context.hash("Admin@123"),
                full_name="System Administrator",
                role=UserRole.admin,
                is_active=True,
            )
            session.add(admin_user)
            print("Seeded default admin: admin@school.edu (password: Admin@123)")

        # Check if teacher exists
        teacher_q = await session.execute(
            select(User).where(User.email == "teacher@school.edu")
        )
        if teacher_q.scalar_one_or_none() is None:
            teacher_user = User(
                email="teacher@school.edu",
                hashed_password=pwd_context.hash("Teacher@123"),
                full_name="Class Teacher",
                role=UserRole.teacher,
                is_active=True,
            )
            session.add(teacher_user)
            print("Seeded default teacher: teacher@school.edu (password: Teacher@123)")

        await session.commit()
    print("Database initialization and seed complete.")


if __name__ == "__main__":
    asyncio.run(init_db())
