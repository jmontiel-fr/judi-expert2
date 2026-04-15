"""Configuration de la base de données PostgreSQL async pour le Site Central."""

import logging
import os
import uuid
from collections.abc import AsyncGenerator

import bcrypt as _bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models.base import Base

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/judi_expert",
)

engine = create_async_engine(DATABASE_URL, echo=False)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Crée toutes les tables si elles n'existent pas encore."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_admin() -> None:
    """Crée le compte administrateur s'il n'existe pas encore.

    Utilise les variables d'environnement ADMIN_EMAIL et ADMIN_DEFAULT_PASSWORD.
    En mode dev, le mot de passe est hashé et stocké dans cognito_sub (même
    mécanisme que le register dev). En production, seul l'enregistrement en BD
    est créé — l'authentification passe par Cognito.
    """
    from models.expert import Expert

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@judi-expert.fr")
    admin_password = os.environ.get("ADMIN_DEFAULT_PASSWORD", "change-me")
    is_dev = os.environ.get("APP_ENV", "production") == "development"

    async with async_session_factory() as session:
        result = await session.execute(
            select(Expert).where(Expert.email == admin_email)
        )
        if result.scalar_one_or_none():
            logger.info("Admin %s existe déjà — seed ignoré", admin_email)
            return

        if is_dev:
            pw_hash = _bcrypt.hashpw(
                admin_password.encode(), _bcrypt.gensalt()
            ).decode()
            cognito_sub = f"dev-{uuid.uuid4()}|{pw_hash}"
        else:
            cognito_sub = f"admin-{uuid.uuid4()}"

        admin = Expert(
            cognito_sub=cognito_sub,
            email=admin_email,
            nom="Administrateur",
            prenom="Judi-Expert",
            adresse="—",
            ville="—",
            code_postal="00000",
            telephone="—",
            domaine="psychologie",
            accept_newsletter=False,
        )
        session.add(admin)
        await session.commit()
        logger.info("Admin %s créé avec succès", admin_email)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dépendance FastAPI fournissant une session de base de données."""
    async with async_session_factory() as session:
        yield session
