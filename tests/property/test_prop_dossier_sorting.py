"""Test par propriété — Tri chronologique inverse des dossiers.

**Validates: Requirements 5.6**

Feature: judi-expert, Property 4: Tri chronologique inverse des dossiers

Propriété 4 : Pour toute liste de dossiers avec des dates de création distinctes,
la liste retournée doit être triée par date de création décroissante
(le plus récent en premier).
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ajouter le backend au path pour les imports
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "site-central"
        / "local"
        / "web"
        / "backend"
    ),
)

from models import Base, Dossier


# ---------------------------------------------------------------------------
# Helper : requête des dossiers triés par date de création décroissante
# ---------------------------------------------------------------------------

async def list_dossiers_sorted(session: AsyncSession) -> list[Dossier]:
    """Retourne les dossiers triés par created_at DESC (plus récent en premier)."""
    result = await session.execute(
        select(Dossier).order_by(Dossier.created_at.desc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Fixture : session async SQLite en mémoire
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def async_engine():
    """Crée un moteur SQLite en mémoire et initialise le schéma."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


# ---------------------------------------------------------------------------
# Stratégies Hypothesis
# ---------------------------------------------------------------------------

# Noms de dossiers valides
valid_names = st.text(min_size=1, max_size=80).filter(lambda s: s.strip() != "")

# Identifiants de ticket uniques
ticket_ids = st.text(
    alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"),
    min_size=5,
    max_size=30,
)

# Listes de ticket_ids uniques (1 à 20 éléments)
unique_ticket_lists = st.lists(
    ticket_ids,
    min_size=1,
    max_size=20,
    unique=True,
)


# ---------------------------------------------------------------------------
# Propriété 4 — Tri chronologique inverse des dossiers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    ticket_list=unique_ticket_lists,
)
async def test_dossiers_sorted_by_created_at_descending(
    async_engine,
    ticket_list: list[str],
):
    """Pour toute liste de dossiers avec des dates de création distinctes,
    la requête ORDER BY created_at DESC retourne les dossiers du plus récent
    au plus ancien."""
    base_time = datetime(2025, 1, 1, 12, 0, 0)

    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with factory() as session:
        # Insérer les dossiers avec des timestamps distincts croissants
        for i, tid in enumerate(ticket_list):
            dossier = Dossier(
                nom=f"Dossier-{i}",
                ticket_id=tid,
                domaine="psychologie",
                created_at=base_time + timedelta(hours=i),
            )
            session.add(dossier)
        await session.flush()

        # Requête triée
        sorted_dossiers = await list_dossiers_sorted(session)

        # Vérifications
        assert len(sorted_dossiers) == len(ticket_list)

        # Les dates doivent être en ordre décroissant
        dates = [d.created_at for d in sorted_dossiers]
        for j in range(len(dates) - 1):
            assert dates[j] >= dates[j + 1], (
                f"Dossier à l'index {j} (created_at={dates[j]}) devrait être "
                f"plus récent ou égal au dossier à l'index {j + 1} "
                f"(created_at={dates[j + 1]})"
            )

        await session.rollback()
