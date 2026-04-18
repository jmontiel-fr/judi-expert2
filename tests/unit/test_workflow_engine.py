"""Tests unitaires pour le moteur de workflow séquentiel.

Valide : Exigences 10.1, 10.2, 10.3, 10.4
"""

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Backend sur le path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend"))

from models import Base
from models.dossier import Dossier
from models.step import Step
from services.workflow_engine import (
    DOSSIER_ACTIF,
    DOSSIER_ARCHIVE,
    DOSSIER_FERME,
    STATUT_INITIAL,
    STATUT_REALISE,
    STATUT_VALIDE,
    WorkflowEngine,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db(session_factory):
    async with session_factory() as session:
        yield session


async def _create_dossier(db, statut=DOSSIER_ACTIF) -> Dossier:
    """Helper: crée un dossier avec 4 étapes au statut initial."""
    dossier = Dossier(nom="Test", ticket_id="T-001", domaine="psychologie", statut=statut)
    db.add(dossier)
    await db.flush()
    for i in range(4):
        db.add(Step(dossier_id=dossier.id, step_number=i, statut=STATUT_INITIAL))
    await db.commit()
    await db.refresh(dossier)
    return dossier


@pytest.fixture
def wf():
    return WorkflowEngine()


# ---------------------------------------------------------------------------
# can_access_step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step0_always_accessible(wf, db):
    dossier = await _create_dossier(db)
    assert await wf.can_access_step(dossier.id, 0, db) is True


@pytest.mark.asyncio
async def test_step1_not_accessible_when_step0_initial(wf, db):
    dossier = await _create_dossier(db)
    assert await wf.can_access_step(dossier.id, 1, db) is False


@pytest.mark.asyncio
async def test_step1_accessible_when_step0_validated(wf, db):
    dossier = await _create_dossier(db)
    # Manually validate step0
    await wf.execute_step(dossier.id, 0, db)
    await wf.validate_step(dossier.id, 0, db)
    assert await wf.can_access_step(dossier.id, 1, db) is True


@pytest.mark.asyncio
async def test_step2_not_accessible_when_step1_only_realise(wf, db):
    dossier = await _create_dossier(db)
    await wf.execute_step(dossier.id, 0, db)
    await wf.validate_step(dossier.id, 0, db)
    await wf.execute_step(dossier.id, 1, db)
    # step1 is réalisé but not validé
    assert await wf.can_access_step(dossier.id, 2, db) is False


# ---------------------------------------------------------------------------
# can_execute_step / execute_step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_step0(wf, db):
    dossier = await _create_dossier(db)
    step = await wf.execute_step(dossier.id, 0, db)
    assert step.statut == STATUT_REALISE
    assert step.executed_at is not None


@pytest.mark.asyncio
async def test_cannot_execute_step_already_realise(wf, db):
    dossier = await _create_dossier(db)
    await wf.execute_step(dossier.id, 0, db)
    with pytest.raises(HTTPException) as exc_info:
        await wf.execute_step(dossier.id, 0, db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_cannot_execute_step_already_validated(wf, db):
    dossier = await _create_dossier(db)
    await wf.execute_step(dossier.id, 0, db)
    await wf.validate_step(dossier.id, 0, db)
    with pytest.raises(HTTPException) as exc_info:
        await wf.execute_step(dossier.id, 0, db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_cannot_execute_step1_without_step0_validated(wf, db):
    dossier = await _create_dossier(db)
    assert await wf.can_execute_step(dossier.id, 1, db) is False
    with pytest.raises(HTTPException) as exc_info:
        await wf.execute_step(dossier.id, 1, db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_execute_step1_after_step0_validated(wf, db):
    dossier = await _create_dossier(db)
    await wf.execute_step(dossier.id, 0, db)
    await wf.validate_step(dossier.id, 0, db)
    step = await wf.execute_step(dossier.id, 1, db)
    assert step.statut == STATUT_REALISE


# ---------------------------------------------------------------------------
# can_validate_step / validate_step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cannot_validate_initial_step(wf, db):
    dossier = await _create_dossier(db)
    assert await wf.can_validate_step(dossier.id, 0, db) is False
    with pytest.raises(HTTPException) as exc_info:
        await wf.validate_step(dossier.id, 0, db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_validate_step0(wf, db):
    dossier = await _create_dossier(db)
    await wf.execute_step(dossier.id, 0, db)
    step = await wf.validate_step(dossier.id, 0, db)
    assert step.statut == STATUT_VALIDE
    assert step.validated_at is not None


@pytest.mark.asyncio
async def test_cannot_validate_already_validated(wf, db):
    dossier = await _create_dossier(db)
    await wf.execute_step(dossier.id, 0, db)
    await wf.validate_step(dossier.id, 0, db)
    with pytest.raises(HTTPException) as exc_info:
        await wf.validate_step(dossier.id, 0, db)
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Full workflow: Step0 → Step1 → Step2 → Step3 + archivage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_workflow_and_archive(wf, db):
    """Après validation des 4 étapes, le dossier reste actif.

    L'expert doit désormais fermer le dossier explicitement via
    le bouton "Fermer le dossier" (cf. Requirement 5).
    """
    dossier = await _create_dossier(db)

    for step_num in range(4):
        await wf.execute_step(dossier.id, step_num, db)
        await wf.validate_step(dossier.id, step_num, db)

    # Refresh dossier — doit rester actif (plus d'archivage auto)
    await db.refresh(dossier)
    assert dossier.statut == DOSSIER_ACTIF


@pytest.mark.asyncio
async def test_archive_blocks_further_operations(wf, db):
    dossier = await _create_dossier(db, statut=DOSSIER_ARCHIVE)
    assert await wf.can_execute_step(dossier.id, 0, db) is False
    assert await wf.can_validate_step(dossier.id, 0, db) is False


@pytest.mark.asyncio
async def test_ferme_blocks_further_operations(wf, db):
    """Un dossier fermé interdit toute modification (Requirement 5.5, 5.6)."""
    dossier = await _create_dossier(db, statut=DOSSIER_FERME)
    assert await wf.can_execute_step(dossier.id, 0, db) is False
    assert await wf.can_validate_step(dossier.id, 0, db) is False


@pytest.mark.asyncio
async def test_ferme_execute_raises_403(wf, db):
    """execute_step sur dossier fermé lève HTTP 403 avec message explicite."""
    dossier = await _create_dossier(db, statut=DOSSIER_FERME)
    with pytest.raises(HTTPException) as exc_info:
        await wf.execute_step(dossier.id, 0, db)
    assert exc_info.value.status_code == 403
    assert "fermé" in exc_info.value.detail


@pytest.mark.asyncio
async def test_ferme_validate_raises_403(wf, db):
    """validate_step sur dossier fermé lève HTTP 403 avec message explicite."""
    dossier = await _create_dossier(db, statut=DOSSIER_FERME)
    # Set step 0 to réalisé so we test the fermé guard, not the statut guard
    from sqlalchemy import select as sa_select

    result = await db.execute(
        sa_select(Step).where(Step.dossier_id == dossier.id, Step.step_number == 0)
    )
    step = result.scalar_one()
    step.statut = STATUT_REALISE
    await db.flush()

    with pytest.raises(HTTPException) as exc_info:
        await wf.validate_step(dossier.id, 0, db)
    assert exc_info.value.status_code == 403
    assert "fermé" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Guards: require_step_access / require_step_not_validated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_step_access_raises_on_locked(wf, db):
    dossier = await _create_dossier(db)
    with pytest.raises(HTTPException) as exc_info:
        await wf.require_step_access(dossier.id, 1, db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_step_access_ok_for_step0(wf, db):
    dossier = await _create_dossier(db)
    # Should not raise
    await wf.require_step_access(dossier.id, 0, db)


@pytest.mark.asyncio
async def test_require_step_not_validated_raises(wf, db):
    dossier = await _create_dossier(db)
    await wf.execute_step(dossier.id, 0, db)
    await wf.validate_step(dossier.id, 0, db)
    with pytest.raises(HTTPException) as exc_info:
        await wf.require_step_not_validated(dossier.id, 0, db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_step_not_validated_ok_for_initial(wf, db):
    dossier = await _create_dossier(db)
    # Should not raise
    await wf.require_step_not_validated(dossier.id, 0, db)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dossier_not_found(wf, db):
    with pytest.raises(HTTPException) as exc_info:
        await wf.can_access_step(9999, 0, db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_invalid_step_number(wf, db):
    dossier = await _create_dossier(db)
    with pytest.raises(HTTPException) as exc_info:
        await wf.execute_step(dossier.id, 5, db)
    assert exc_info.value.status_code == 400
