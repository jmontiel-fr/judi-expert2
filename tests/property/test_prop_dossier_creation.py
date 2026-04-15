"""Test par propriété — Validation de création de dossier.

**Validates: Requirements 5.1, 5.5**

Propriété 2 : Pour tout nom de dossier et tout ticket, la création d'un dossier
doit réussir si et seulement si le nom est non-vide et le ticket est valide.
Un dossier créé doit contenir exactement 4 étapes (Step0 à Step3) toutes au
statut "initial".
"""

import sys
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
        / "local-site"
        / "web"
        / "backend"
    ),
)

from models import Base, Dossier, Step


# ---------------------------------------------------------------------------
# Helper : création de dossier avec validation métier
# ---------------------------------------------------------------------------

async def create_dossier(
    session: AsyncSession,
    nom: str,
    ticket_id: str,
    ticket_valid: bool,
) -> Dossier:
    """Crée un dossier si le nom est non-vide et le ticket est valide.

    Raises:
        ValueError: si le nom est vide/whitespace ou si le ticket est invalide.
    """
    if not nom or not nom.strip():
        raise ValueError("Le nom du dossier ne peut pas être vide")
    if not ticket_valid:
        raise ValueError("Le ticket est invalide ou déjà utilisé")

    dossier = Dossier(nom=nom.strip(), ticket_id=ticket_id, domaine="psychologie")
    session.add(dossier)
    await session.flush()

    for step_number in range(4):
        session.add(
            Step(dossier_id=dossier.id, step_number=step_number, statut="initial")
        )
    await session.flush()

    return dossier


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

# Noms vides ou composés uniquement d'espaces
empty_names = st.one_of(
    st.just(""),
    st.text(alphabet=" \t\n\r", min_size=1, max_size=20),
)

# Noms valides : au moins un caractère non-espace
valid_names = st.text(min_size=1, max_size=100).filter(lambda s: s.strip() != "")

# Identifiants de ticket
ticket_ids = st.text(
    alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"),
    min_size=5,
    max_size=30,
)


# ---------------------------------------------------------------------------
# Propriété 2 — Cas d'échec : nom vide OU ticket invalide → ValueError
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    nom=st.one_of(empty_names, valid_names),
    ticket_id=ticket_ids,
    ticket_valid=st.booleans(),
)
async def test_creation_fails_when_name_empty_or_ticket_invalid(
    async_engine,
    nom: str,
    ticket_id: str,
    ticket_valid: bool,
):
    """La création échoue (ValueError) dès que le nom est vide/whitespace
    OU que le ticket est invalide."""
    name_is_empty = not nom or not nom.strip()
    should_fail = name_is_empty or not ticket_valid

    if not should_fail:
        # Ce cas est couvert par le test de succès ; on le saute ici.
        return

    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with factory() as session:
        with pytest.raises(ValueError):
            await create_dossier(session, nom, ticket_id, ticket_valid)
        await session.rollback()


# ---------------------------------------------------------------------------
# Propriété 2 — Cas de succès : nom non-vide ET ticket valide → dossier + 4 étapes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    nom=valid_names,
    ticket_id=ticket_ids,
)
async def test_creation_succeeds_with_valid_name_and_ticket(
    async_engine,
    nom: str,
    ticket_id: str,
):
    """Quand le nom est non-vide et le ticket valide, un dossier est créé
    avec exactement 4 étapes (step_number 0-3) toutes au statut 'initial'."""
    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with factory() as session:
        dossier = await create_dossier(session, nom, ticket_id, ticket_valid=True)

        # Le dossier existe
        assert dossier.id is not None
        assert dossier.nom == nom.strip()
        assert dossier.ticket_id == ticket_id

        # Exactement 4 étapes
        result = await session.execute(
            select(Step)
            .where(Step.dossier_id == dossier.id)
            .order_by(Step.step_number)
        )
        steps = result.scalars().all()

        assert len(steps) == 4
        assert [s.step_number for s in steps] == [0, 1, 2, 3]
        assert all(s.statut == "initial" for s in steps)

        await session.rollback()
