"""Configuration de la base de données SQLite async pour l'Application Locale."""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models.base import Base

DATABASE_DIR = os.environ.get("DATABASE_DIR", "data")
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{DATABASE_DIR}/judi-expert.db",
)

engine = create_async_engine(DATABASE_URL, echo=False)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Crée toutes les tables si elles n'existent pas encore."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dépendance FastAPI fournissant une session de base de données."""
    async with async_session_factory() as session:
        yield session
