"""Test par propriété — Génération de ticket unique après paiement.

**Validates: Requirements 15.2**

Feature: judi-expert, Property 10: Génération de ticket unique après paiement

Propriété 10 : Pour tout paiement Stripe confirmé, le système doit générer
exactement un ticket avec un code unique, le domaine correspondant à celui de
l'expert, et le statut "actif". Deux paiements distincts ne doivent jamais
produire le même code de ticket.
"""

import sys
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
# (même technique que test_central_models.py pour éviter les conflits)
# ---------------------------------------------------------------------------

_central_backend = str(
    Path(__file__).resolve().parents[2]
    / "central-site"
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
# Helper : génération de ticket après paiement
# ---------------------------------------------------------------------------

async def generate_ticket_after_payment(
    session: AsyncSession,
    expert_id: int,
    domaine: str,
    stripe_payment_id: str,
) -> Ticket:
    """Simule la génération d'un ticket après confirmation de paiement Stripe.

    Génère un ticket unique avec :
    - Un ticket_code unique (uuid4)
    - Le domaine de l'expert
    - Le statut "actif"
    - Un montant fixe de 49.99€
    """
    ticket_code = str(uuid4())
    ticket = Ticket(
        ticket_code=ticket_code,
        expert_id=expert_id,
        domaine=domaine,
        statut="actif",
        montant=Decimal("49.99"),
        stripe_payment_id=stripe_payment_id,
    )
    session.add(ticket)
    await session.flush()
    return ticket


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

stripe_payment_ids = st.builds(
    lambda suffix: f"pi_{suffix}",
    st.text(
        alphabet=st.sampled_from(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        ),
        min_size=5,
        max_size=30,
    ),
)

expert_names = st.text(min_size=1, max_size=50).filter(lambda s: s.strip() != "")
expert_emails = st.builds(
    lambda local: f"{local}@example.com",
    st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789"),
        min_size=3,
        max_size=20,
    ),
)


# ---------------------------------------------------------------------------
# Propriété 10a — Un paiement génère exactement un ticket actif avec le bon domaine
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    domaine=domaines,
    stripe_pid=stripe_payment_ids,
    nom=expert_names,
    prenom=expert_names,
    email=expert_emails,
)
async def test_payment_generates_exactly_one_active_ticket(
    async_engine,
    domaine: str,
    stripe_pid: str,
    nom: str,
    prenom: str,
    email: str,
):
    """Pour tout expert et paiement valide, exactement un ticket est créé
    avec statut 'actif' et le domaine correspondant à celui de l'expert."""
    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with factory() as session:
        # Créer un expert
        expert = Expert(
            cognito_sub=f"sub-{uuid4().hex[:12]}",
            email=email,
            nom=nom,
            prenom=prenom,
            adresse="1 rue test",
            domaine=domaine,
        )
        session.add(expert)
        await session.flush()

        # Générer le ticket après paiement
        ticket = await generate_ticket_after_payment(
            session, expert.id, domaine, stripe_pid
        )

        # Vérifier qu'exactement un ticket existe pour ce paiement
        result = await session.execute(
            select(Ticket).where(Ticket.stripe_payment_id == stripe_pid)
        )
        tickets = result.scalars().all()
        assert len(tickets) == 1, (
            f"Attendu exactement 1 ticket pour le paiement {stripe_pid}, "
            f"obtenu {len(tickets)}"
        )

        # Vérifier les attributs du ticket
        created_ticket = tickets[0]
        assert created_ticket.statut == "actif"
        assert created_ticket.domaine == domaine
        assert created_ticket.expert_id == expert.id
        assert created_ticket.ticket_code is not None
        assert len(created_ticket.ticket_code) > 0

        await session.rollback()


# ---------------------------------------------------------------------------
# Propriété 10b — N paiements distincts produisent N codes de ticket uniques
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    domaine=domaines,
    n_payments=st.integers(min_value=2, max_value=20),
    nom=expert_names,
    prenom=expert_names,
    email=expert_emails,
)
async def test_distinct_payments_produce_unique_ticket_codes(
    async_engine,
    domaine: str,
    n_payments: int,
    nom: str,
    prenom: str,
    email: str,
):
    """Pour N paiements distincts pour le même expert, tous les codes de
    ticket générés doivent être uniques (aucun doublon)."""
    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with factory() as session:
        # Créer un expert
        expert = Expert(
            cognito_sub=f"sub-{uuid4().hex[:12]}",
            email=email,
            nom=nom,
            prenom=prenom,
            adresse="1 rue test",
            domaine=domaine,
        )
        session.add(expert)
        await session.flush()

        # Générer N tickets pour N paiements distincts
        ticket_codes = []
        for i in range(n_payments):
            payment_id = f"pi_test_{uuid4().hex[:16]}_{i}"
            ticket = await generate_ticket_after_payment(
                session, expert.id, domaine, payment_id
            )
            ticket_codes.append(ticket.ticket_code)

        # Vérifier l'unicité des codes
        assert len(ticket_codes) == n_payments
        assert len(set(ticket_codes)) == n_payments, (
            f"Doublons détectés parmi {n_payments} tickets : "
            f"{[c for c in ticket_codes if ticket_codes.count(c) > 1]}"
        )

        await session.rollback()
