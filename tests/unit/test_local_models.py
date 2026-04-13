"""Tests unitaires pour les modèles SQLAlchemy de l'Application Locale."""

import asyncio
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ajouter le backend au path pour les imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "site-central" / "local" / "web" / "backend"))

from models import Base, ChatMessage, Dossier, LocalConfig, Step, StepFile


@pytest_asyncio.fixture
async def async_session():
    """Crée une session async avec une BD SQLite en mémoire."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_local_config(async_session: AsyncSession):
    config = LocalConfig(
        password_hash="hashed_pw",
        domaine="psychologie",
        is_configured=True,
    )
    async_session.add(config)
    await async_session.commit()

    result = await async_session.execute(select(LocalConfig))
    row = result.scalar_one()
    assert row.password_hash == "hashed_pw"
    assert row.domaine == "psychologie"
    assert row.is_configured is True
    assert row.rag_version is None


@pytest.mark.asyncio
async def test_create_dossier_with_steps(async_session: AsyncSession):
    dossier = Dossier(
        nom="Dossier Test",
        ticket_id="TICKET-001",
        domaine="psychologie",
    )
    async_session.add(dossier)
    await async_session.flush()

    for i in range(4):
        step = Step(dossier_id=dossier.id, step_number=i)
        async_session.add(step)
    await async_session.commit()

    result = await async_session.execute(
        select(Dossier).where(Dossier.ticket_id == "TICKET-001")
    )
    d = result.scalar_one()
    assert d.nom == "Dossier Test"
    assert d.statut == "actif"

    steps_result = await async_session.execute(
        select(Step).where(Step.dossier_id == d.id).order_by(Step.step_number)
    )
    steps = steps_result.scalars().all()
    assert len(steps) == 4
    for i, step in enumerate(steps):
        assert step.step_number == i
        assert step.statut == "initial"
        assert step.executed_at is None
        assert step.validated_at is None


@pytest.mark.asyncio
async def test_step_file_relationship(async_session: AsyncSession):
    dossier = Dossier(nom="D", ticket_id="T-002", domaine="psychologie")
    async_session.add(dossier)
    await async_session.flush()

    step = Step(dossier_id=dossier.id, step_number=0)
    async_session.add(step)
    await async_session.flush()

    sf = StepFile(
        step_id=step.id,
        filename="scan.pdf",
        file_path="/data/dossiers/1/scan.pdf",
        file_type="pdf_scan",
        file_size=1024,
    )
    async_session.add(sf)
    await async_session.commit()

    result = await async_session.execute(
        select(StepFile).where(StepFile.step_id == step.id)
    )
    file = result.scalar_one()
    assert file.filename == "scan.pdf"
    assert file.file_type == "pdf_scan"
    assert file.file_size == 1024


@pytest.mark.asyncio
async def test_chat_message(async_session: AsyncSession):
    msg = ChatMessage(session_id=1, role="user", content="Bonjour")
    async_session.add(msg)
    await async_session.commit()

    result = await async_session.execute(select(ChatMessage))
    row = result.scalar_one()
    assert row.role == "user"
    assert row.content == "Bonjour"
    assert row.session_id == 1


@pytest.mark.asyncio
async def test_dossier_ticket_unique(async_session: AsyncSession):
    d1 = Dossier(nom="D1", ticket_id="UNIQUE-T", domaine="psychologie")
    async_session.add(d1)
    await async_session.commit()

    d2 = Dossier(nom="D2", ticket_id="UNIQUE-T", domaine="psychologie")
    async_session.add(d2)
    with pytest.raises(Exception):
        await async_session.commit()
