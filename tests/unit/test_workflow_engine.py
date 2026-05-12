"""Tests unitaires pour le moteur de workflow séquentiel.

Valide : Exigences 10.1, 10.2, 10.3, 10.4

Le workflow utilise 5 étapes numérotées de 1 à 5 :
  Step 1 — Extraction (OCR + structuration)
  Step 2 — PEMEC (Plan d'Entretien)
  Step 3 — Consolidation documentaire
  Step 4 — Pré-rapport (REF-Projet)
  Step 5 — Archivage (ZIP + hash)
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
    """Helper: crée un dossier avec 5 étapes (1-5) au statut initial."""
    dossier = Dossier(nom="Test", ticket_id="T-001", domaine="psychologie", statut=statut)
    db.add(dossier)
    await db.flush()
    for i in range(1, 6):
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
async def test_step1_always_accessible(wf, db):
    """Step 1 est toujours accessible (pas de prérequis)."""
    dossier = await _create_dossier(db)
    assert await wf.can_access_step(dossier.id, 1, db) is True


@pytest.mark.asyncio
async def test_step2_not_accessible_when_step1_initial(wf, db):
    """Step 2 n'est pas accessible tant que Step 1 n'est pas validé."""
    dossier = await _create_dossier(db)
    assert await wf.can_access_step(dossier.id, 2, db) is False


@pytest.mark.asyncio
async def test_step2_accessible_when_step1_validated(wf, db):
    """Step 2 est accessible une fois Step 1 validé."""
    dossier = await _create_dossier(db)
    await wf.execute_step(dossier.id, 1, db)
    await wf.validate_step(dossier.id, 1, db)
    assert await wf.can_access_step(dossier.id, 2, db) is True


@pytest.mark.asyncio
async def test_step3_not_accessible_when_step2_only_realise(wf, db):
    """Step 3 n'est pas accessible si Step 2 est seulement réalisé (pas validé)."""
    dossier = await _create_dossier(db)
    await wf.execute_step(dossier.id, 1, db)
    await wf.validate_step(dossier.id, 1, db)
    await wf.execute_step(dossier.id, 2, db)
    # step2 is réalisé but not validé
    assert await wf.can_access_step(dossier.id, 3, db) is False


# ---------------------------------------------------------------------------
# can_execute_step / execute_step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_step1(wf, db):
    """Step 1 peut être exécuté directement (pas de prérequis)."""
    dossier = await _create_dossier(db)
    step = await wf.execute_step(dossier.id, 1, db)
    assert step.statut == STATUT_REALISE
    assert step.executed_at is not None


@pytest.mark.asyncio
async def test_cannot_execute_step_already_realise(wf, db):
    """Un step déjà réalisé ne peut pas être ré-exécuté."""
    dossier = await _create_dossier(db)
    await wf.execute_step(dossier.id, 1, db)
    with pytest.raises(HTTPException) as exc_info:
        await wf.execute_step(dossier.id, 1, db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_cannot_execute_step_already_validated(wf, db):
    """Un step déjà validé ne peut pas être ré-exécuté."""
    dossier = await _create_dossier(db)
    await wf.execute_step(dossier.id, 1, db)
    await wf.validate_step(dossier.id, 1, db)
    with pytest.raises(HTTPException) as exc_info:
        await wf.execute_step(dossier.id, 1, db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_cannot_execute_step2_without_step1_validated(wf, db):
    """Step 2 ne peut pas être exécuté si Step 1 n'est pas validé."""
    dossier = await _create_dossier(db)
    assert await wf.can_execute_step(dossier.id, 2, db) is False
    with pytest.raises(HTTPException) as exc_info:
        await wf.execute_step(dossier.id, 2, db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_execute_step2_after_step1_validated(wf, db):
    """Step 2 peut être exécuté après validation de Step 1."""
    dossier = await _create_dossier(db)
    await wf.execute_step(dossier.id, 1, db)
    await wf.validate_step(dossier.id, 1, db)
    step = await wf.execute_step(dossier.id, 2, db)
    assert step.statut == STATUT_REALISE


# ---------------------------------------------------------------------------
# can_validate_step / validate_step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cannot_validate_initial_step(wf, db):
    """Un step au statut initial ne peut pas être validé."""
    dossier = await _create_dossier(db)
    assert await wf.can_validate_step(dossier.id, 1, db) is False
    with pytest.raises(HTTPException) as exc_info:
        await wf.validate_step(dossier.id, 1, db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_validate_step1(wf, db):
    """Step 1 peut être validé après exécution."""
    dossier = await _create_dossier(db)
    await wf.execute_step(dossier.id, 1, db)
    step = await wf.validate_step(dossier.id, 1, db)
    assert step.statut == STATUT_VALIDE
    assert step.validated_at is not None


@pytest.mark.asyncio
async def test_cannot_validate_already_validated(wf, db):
    """Un step déjà validé ne peut pas être re-validé."""
    dossier = await _create_dossier(db)
    await wf.execute_step(dossier.id, 1, db)
    await wf.validate_step(dossier.id, 1, db)
    with pytest.raises(HTTPException) as exc_info:
        await wf.validate_step(dossier.id, 1, db)
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Full workflow: Step1 → Step2 → Step3 → Step4 → Step5
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_workflow_and_active(wf, db):
    """Après validation des 5 étapes, le dossier reste actif.

    L'expert doit fermer le dossier explicitement via le bouton
    "Fermer le dossier".
    """
    dossier = await _create_dossier(db)

    for step_num in range(1, 6):
        await wf.execute_step(dossier.id, step_num, db)
        await wf.validate_step(dossier.id, step_num, db)

    # Refresh dossier — doit rester actif (plus d'archivage auto)
    await db.refresh(dossier)
    assert dossier.statut == DOSSIER_ACTIF


@pytest.mark.asyncio
async def test_close_dossier_after_all_steps_validated(wf, db):
    """Le dossier peut être fermé après validation de toutes les étapes."""
    dossier = await _create_dossier(db)

    for step_num in range(1, 6):
        await wf.execute_step(dossier.id, step_num, db)
        await wf.validate_step(dossier.id, step_num, db)

    closed = await wf.close_dossier(dossier.id, db)
    assert closed.statut == DOSSIER_FERME


@pytest.mark.asyncio
async def test_cannot_close_dossier_with_pending_steps(wf, db):
    """Le dossier ne peut pas être fermé si des étapes ne sont pas validées."""
    dossier = await _create_dossier(db)
    await wf.execute_step(dossier.id, 1, db)
    await wf.validate_step(dossier.id, 1, db)

    with pytest.raises(HTTPException) as exc_info:
        await wf.close_dossier(dossier.id, db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_archive_blocks_further_operations(wf, db):
    """Un dossier archivé interdit toute exécution ou validation."""
    dossier = await _create_dossier(db, statut=DOSSIER_ARCHIVE)
    assert await wf.can_execute_step(dossier.id, 1, db) is False
    assert await wf.can_validate_step(dossier.id, 1, db) is False


@pytest.mark.asyncio
async def test_ferme_blocks_further_operations(wf, db):
    """Un dossier fermé interdit toute modification (Requirement 5.5, 5.6)."""
    dossier = await _create_dossier(db, statut=DOSSIER_FERME)
    assert await wf.can_execute_step(dossier.id, 1, db) is False
    assert await wf.can_validate_step(dossier.id, 1, db) is False


@pytest.mark.asyncio
async def test_ferme_execute_raises_403(wf, db):
    """execute_step sur dossier fermé lève HTTP 403 avec message explicite."""
    dossier = await _create_dossier(db, statut=DOSSIER_FERME)
    with pytest.raises(HTTPException) as exc_info:
        await wf.execute_step(dossier.id, 1, db)
    assert exc_info.value.status_code == 403
    assert "fermé" in exc_info.value.detail


@pytest.mark.asyncio
async def test_ferme_validate_raises_403(wf, db):
    """validate_step sur dossier fermé lève HTTP 403 avec message explicite."""
    dossier = await _create_dossier(db, statut=DOSSIER_FERME)
    # Set step 1 to réalisé so we test the fermé guard, not the statut guard
    from sqlalchemy import select as sa_select

    result = await db.execute(
        sa_select(Step).where(Step.dossier_id == dossier.id, Step.step_number == 1)
    )
    step = result.scalar_one()
    step.statut = STATUT_REALISE
    await db.flush()

    with pytest.raises(HTTPException) as exc_info:
        await wf.validate_step(dossier.id, 1, db)
    assert exc_info.value.status_code == 403
    assert "fermé" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Guards: require_step_access / require_step_not_validated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_step_access_raises_on_locked(wf, db):
    """require_step_access lève 403 si les étapes précédentes ne sont pas validées."""
    dossier = await _create_dossier(db)
    with pytest.raises(HTTPException) as exc_info:
        await wf.require_step_access(dossier.id, 2, db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_step_access_ok_for_step1(wf, db):
    """require_step_access ne lève pas pour Step 1 (toujours accessible)."""
    dossier = await _create_dossier(db)
    # Should not raise
    await wf.require_step_access(dossier.id, 1, db)


@pytest.mark.asyncio
async def test_require_step_not_validated_raises(wf, db):
    """require_step_not_validated lève 403 si le step est validé."""
    dossier = await _create_dossier(db)
    await wf.execute_step(dossier.id, 1, db)
    await wf.validate_step(dossier.id, 1, db)
    with pytest.raises(HTTPException) as exc_info:
        await wf.require_step_not_validated(dossier.id, 1, db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_step_not_validated_ok_for_initial(wf, db):
    """require_step_not_validated ne lève pas si le step est initial."""
    dossier = await _create_dossier(db)
    # Should not raise
    await wf.require_step_not_validated(dossier.id, 1, db)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dossier_not_found(wf, db):
    """Accès à un dossier inexistant lève 404."""
    with pytest.raises(HTTPException) as exc_info:
        await wf.can_access_step(9999, 1, db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_invalid_step_number(wf, db):
    """Un numéro d'étape invalide (0 ou 6) lève 400."""
    dossier = await _create_dossier(db)
    with pytest.raises(HTTPException) as exc_info:
        await wf.execute_step(dossier.id, 0, db)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_invalid_step_number_too_high(wf, db):
    """Un numéro d'étape > 5 lève 400."""
    dossier = await _create_dossier(db)
    with pytest.raises(HTTPException) as exc_info:
        await wf.execute_step(dossier.id, 6, db)
    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# start_step / fail_step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_step(wf, db):
    """start_step passe le statut à en_cours."""
    dossier = await _create_dossier(db)
    step = await wf.start_step(dossier.id, 1, db)
    assert step.statut == "en_cours"
    assert step.executed_at is not None


@pytest.mark.asyncio
async def test_fail_step_resets_to_initial(wf, db):
    """fail_step remet un step en_cours à initial."""
    dossier = await _create_dossier(db)
    await wf.start_step(dossier.id, 1, db)
    step = await wf.fail_step(dossier.id, 1, db)
    assert step.statut == STATUT_INITIAL


# ---------------------------------------------------------------------------
# reset_step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_step(wf, db):
    """reset_step remet un step réalisé à initial."""
    dossier = await _create_dossier(db)
    await wf.execute_step(dossier.id, 1, db)
    step = await wf.reset_step(dossier.id, 1, db)
    assert step.statut == STATUT_INITIAL


@pytest.mark.asyncio
async def test_cannot_reset_step_if_next_validated(wf, db):
    """reset_step lève 403 si une étape suivante est validée."""
    dossier = await _create_dossier(db)
    await wf.execute_step(dossier.id, 1, db)
    await wf.validate_step(dossier.id, 1, db)
    await wf.execute_step(dossier.id, 2, db)
    await wf.validate_step(dossier.id, 2, db)

    with pytest.raises(HTTPException) as exc_info:
        await wf.reset_step(dossier.id, 1, db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_cannot_reset_initial_step(wf, db):
    """reset_step lève 400 si le step est déjà initial."""
    dossier = await _create_dossier(db)
    with pytest.raises(HTTPException) as exc_info:
        await wf.reset_step(dossier.id, 1, db)
    assert exc_info.value.status_code == 400
