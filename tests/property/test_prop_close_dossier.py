"""Tests par propriété — Fermeture de dossier.

# Feature: workflow-dossier-refactor, Property 4: Close dossier precondition and postcondition
# Feature: workflow-dossier-refactor, Property 5: Closed dossier blocks all modifications

**Validates: Requirements 5.3, 5.4, 5.5, 5.6, 9.6**
"""

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "local-site"
        / "web"
        / "backend"
    ),
)

from models import Base, Dossier, Step
from services.workflow_engine import (
    DOSSIER_ACTIF,
    DOSSIER_FERME,
    STATUT_INITIAL,
    STATUT_REALISE,
    STATUT_VALIDE,
    WorkflowEngine,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_async(coro):
    """Exécute une coroutine de manière synchrone."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


_STEP_STATUSES = [STATUT_INITIAL, STATUT_REALISE, STATUT_VALIDE]


async def _setup_db(step_statuses: list[str], dossier_statut: str = DOSSIER_ACTIF):
    """Crée une base en mémoire avec un dossier et 4 étapes aux statuts donnés."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        dossier = Dossier(
            nom="Test-Close",
            ticket_id="TICKET-CLOSE",
            domaine="psychologie",
            statut=dossier_statut,
        )
        session.add(dossier)
        await session.flush()

        for i, statut in enumerate(step_statuses):
            session.add(
                Step(
                    dossier_id=dossier.id,
                    step_number=i,
                    statut=statut,
                )
            )
        await session.commit()
        dossier_id = dossier.id

    return engine, session_factory, dossier_id


# ---------------------------------------------------------------------------
# Property 4 — Close dossier precondition and postcondition
# ---------------------------------------------------------------------------

@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    s0=st.sampled_from(_STEP_STATUSES),
    s1=st.sampled_from(_STEP_STATUSES),
    s2=st.sampled_from(_STEP_STATUSES),
    s3=st.sampled_from(_STEP_STATUSES),
)
def test_close_dossier_precondition_postcondition(s0, s1, s2, s3):
    """La fermeture réussit ssi les 4 étapes sont "validé".

    En cas de succès : dossier.statut → "fermé".
    En cas d'échec : dossier.statut reste inchangé, HTTP 403.
    """
    step_statuses = [s0, s1, s2, s3]
    all_validated = all(s == STATUT_VALIDE for s in step_statuses)

    async def _run():
        db_engine, session_factory, dossier_id = await _setup_db(step_statuses)
        we = WorkflowEngine()

        try:
            async with session_factory() as session:
                if all_validated:
                    # Should succeed
                    result = await we.close_dossier(dossier_id, session)
                    assert result.statut == DOSSIER_FERME, (
                        f"Attendu statut fermé, obtenu {result.statut}"
                    )
                    await session.commit()

                    # Verify in a fresh session
                    async with session_factory() as check:
                        res = await check.execute(
                            select(Dossier).where(Dossier.id == dossier_id)
                        )
                        d = res.scalar_one()
                        assert d.statut == DOSSIER_FERME
                else:
                    # Should fail with HTTP 403
                    with pytest.raises(HTTPException) as exc_info:
                        await we.close_dossier(dossier_id, session)
                    assert exc_info.value.status_code == 403
                    assert "Toutes les étapes doivent être validées" in str(
                        exc_info.value.detail
                    )

                    # Verify dossier statut unchanged
                    async with session_factory() as check:
                        res = await check.execute(
                            select(Dossier).where(Dossier.id == dossier_id)
                        )
                        d = res.scalar_one()
                        assert d.statut == DOSSIER_ACTIF, (
                            f"Statut devrait rester actif, obtenu {d.statut}"
                        )
        finally:
            await db_engine.dispose()

    run_async(_run())



# ---------------------------------------------------------------------------
# Property 5 — Closed dossier blocks all modifications
# ---------------------------------------------------------------------------

@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    step_number=st.sampled_from([0, 1, 2, 3]),
    operation=st.sampled_from(["execute_step", "validate_step"]),
)
def test_closed_dossier_blocks_modifications(step_number, operation):
    """Pour tout dossier fermé, execute_step et validate_step sont rejetés HTTP 403."""

    async def _run():
        # Créer un dossier fermé avec toutes les étapes validées
        all_validated = [STATUT_VALIDE] * 4
        db_engine, session_factory, dossier_id = await _setup_db(
            all_validated, dossier_statut=DOSSIER_FERME
        )
        we = WorkflowEngine()

        try:
            async with session_factory() as session:
                with pytest.raises(HTTPException) as exc_info:
                    if operation == "execute_step":
                        await we.execute_step(dossier_id, step_number, session)
                    else:
                        await we.validate_step(dossier_id, step_number, session)

                assert exc_info.value.status_code == 403, (
                    f"Attendu HTTP 403, obtenu {exc_info.value.status_code}"
                )
                assert "fermé" in str(exc_info.value.detail).lower(), (
                    f"Le message devrait mentionner 'fermé': {exc_info.value.detail}"
                )
        finally:
            await db_engine.dispose()

    run_async(_run())
