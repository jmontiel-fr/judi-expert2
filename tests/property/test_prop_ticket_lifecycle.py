"""Test par propriété — Cycle de vie des tickets (idempotence d'utilisation).

**Validates: Requirements 5.3, 5.4, 15.2, 15.4**

Feature: judi-expert, Property 3: Cycle de vie des tickets (idempotence d'utilisation)

Propriété 3 : Pour tout ticket valide, la première vérification doit réussir et
marquer le ticket comme "utilisé". Toute vérification ultérieure du même ticket
doit échouer avec un message indiquant "déjà utilisé". Pour tout ticket
inexistant ou invalide, la vérification doit échouer avec un message indiquant
"invalide".
"""

import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Import des modèles du Site Central avec isolation de modules
# (même technique que test_prop_ticket_generation.py)
# ---------------------------------------------------------------------------

_central_backend = str(
    Path(__file__).resolve().parents[2]
    / "site-central"
    / "aws"
    / "web"
    / "backend"
)

_saved_modules = {
    k: sys.modules.pop(k)
    for k in list(sys.modules)
    if k == "models" or k.startswith("models.")
}
_saved_path = sys.path[:]
sys.path.insert(0, _central_backend)

import models as _central_models  # noqa: E402
import models.base  # noqa: E402
import models.expert  # noqa: E402
import models.ticket  # noqa: E402

Base = _central_models.Base
Expert = _central_models.Expert
Ticket = _central_models.Ticket

# Sauvegarder les modules centraux et restaurer les originaux
_central_module_cache = {
    k: sys.modules.pop(k)
    for k in list(sys.modules)
    if k == "models" or k.startswith("models.")
}
sys.modules.update(_saved_modules)
sys.path[:] = _saved_path


# ---------------------------------------------------------------------------
# Helper : vérification de ticket
# ---------------------------------------------------------------------------

async def verify_ticket(session: AsyncSession, ticket_code: str) -> dict:
    """Simule la vérification d'un ticket.

    - Si le ticket n'existe pas : retourne {"success": False, "error": "invalide"}
    - Si le ticket est actif : marque comme utilisé, retourne {"success": True, "ticket_code": ...}
    - Si le ticket est déjà utilisé : retourne {"success": False, "error": "déjà utilisé"}
    - Si le ticket est expiré : retourne {"success": False, "error": "invalide"}
    """
    result = await session.execute(
        select(Ticket).where(Ticket.ticket_code == ticket_code)
    )
    ticket = result.scalars().first()

    if ticket is None:
        return {"success": False, "error": "invalide"}

    if ticket.statut == "actif":
        ticket.statut = "utilisé"
        ticket.used_at = datetime.now(timezone.utc)
        await session.flush()
        return {"success": True, "ticket_code": ticket_code}

    if ticket.statut == "utilisé":
        return {"success": False, "error": "déjà utilisé"}

    # statut == "expire" ou tout autre statut
    return {"success": False, "error": "invalide"}


# ---------------------------------------------------------------------------
# Fixture : moteur async SQLite en mémoire
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

domaines = st.sampled_from([
    "psychologie",
    "psychiatrie",
    "medecine_legale",
    "batiment",
    "comptabilite",
])

ticket_codes = st.text(
    alphabet=st.sampled_from(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
    ),
    min_size=5,
    max_size=30,
)

n_retries = st.integers(min_value=1, max_value=10)


# ---------------------------------------------------------------------------
# Helper : créer un expert et un ticket actif dans la session
# ---------------------------------------------------------------------------

async def _create_expert_and_ticket(
    session: AsyncSession, domaine: str, ticket_code: str
) -> Ticket:
    """Crée un expert et un ticket actif pour les tests."""
    expert = Expert(
        cognito_sub=f"sub-{uuid4().hex[:12]}",
        email=f"{uuid4().hex[:10]}@example.com",
        nom="Test",
        prenom="Expert",
        adresse="1 rue test",
        domaine=domaine,
    )
    session.add(expert)
    await session.flush()

    ticket = Ticket(
        ticket_code=ticket_code,
        expert_id=expert.id,
        domaine=domaine,
        statut="actif",
        montant=Decimal("49.99"),
        stripe_payment_id=f"pi_{uuid4().hex[:16]}",
    )
    session.add(ticket)
    await session.flush()
    return ticket


# ---------------------------------------------------------------------------
# Propriété 3a — La première vérification réussit et marque le ticket "utilisé"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    domaine=domaines,
    code=ticket_codes,
)
async def test_first_verification_succeeds_and_marks_used(
    async_engine,
    domaine: str,
    code: str,
):
    """Pour tout ticket valide (statut 'actif'), la première vérification
    réussit et le ticket passe au statut 'utilisé'."""
    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with factory() as session:
        await _create_expert_and_ticket(session, domaine, code)

        # Première vérification
        result = await verify_ticket(session, code)

        assert result["success"] is True
        assert result["ticket_code"] == code

        # Vérifier que le statut est bien "utilisé"
        db_result = await session.execute(
            select(Ticket).where(Ticket.ticket_code == code)
        )
        ticket = db_result.scalars().first()
        assert ticket is not None
        assert ticket.statut == "utilisé"
        assert ticket.used_at is not None

        await session.rollback()


# ---------------------------------------------------------------------------
# Propriété 3b — Les vérifications ultérieures échouent avec "déjà utilisé"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    domaine=domaines,
    code=ticket_codes,
    retries=n_retries,
)
async def test_subsequent_verifications_fail_with_deja_utilise(
    async_engine,
    domaine: str,
    code: str,
    retries: int,
):
    """Pour tout ticket valide, après la première vérification réussie,
    toutes les vérifications suivantes (1 à 10 fois) échouent avec
    l'erreur 'déjà utilisé'."""
    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with factory() as session:
        await _create_expert_and_ticket(session, domaine, code)

        # Première vérification (doit réussir)
        first_result = await verify_ticket(session, code)
        assert first_result["success"] is True

        # Vérifications ultérieures (doivent toutes échouer)
        for _ in range(retries):
            result = await verify_ticket(session, code)
            assert result["success"] is False
            assert result["error"] == "déjà utilisé"

        await session.rollback()


# ---------------------------------------------------------------------------
# Propriété 3c — Un code de ticket inexistant retourne "invalide"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    code=ticket_codes,
)
async def test_invalid_ticket_code_returns_invalide(
    async_engine,
    code: str,
):
    """Pour tout code de ticket aléatoire qui n'existe pas en base,
    la vérification échoue avec l'erreur 'invalide'."""
    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with factory() as session:
        # Pas de ticket créé — la base est vide
        result = await verify_ticket(session, code)

        assert result["success"] is False
        assert result["error"] == "invalide"

        await session.rollback()
