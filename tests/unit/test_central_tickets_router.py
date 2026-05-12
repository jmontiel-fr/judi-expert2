"""Tests unitaires pour les routers tickets et webhooks du Site Central."""

import json
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Module isolation: load Site Central backend without polluting sys.modules
# ---------------------------------------------------------------------------
_central_backend = str(
    Path(__file__).resolve().parents[2] / "central-site" / "web" / "backend"
)

_modules_to_isolate = [
    "models", "database", "routers", "schemas", "services", "main",
]

_saved_modules = {}
for prefix in _modules_to_isolate:
    for k in list(sys.modules):
        if k == prefix or k.startswith(prefix + "."):
            _saved_modules[k] = sys.modules.pop(k)

_saved_path = sys.path[:]
sys.path.insert(0, _central_backend)

from models import Base as _Base  # noqa: E402
from models.expert import Expert as _Expert  # noqa: E402
from models.ticket import Ticket as _Ticket  # noqa: E402
from database import get_db as _get_db  # noqa: E402
from main import app as _app  # noqa: E402

import routers.tickets as _tickets_mod  # noqa: E402
import routers.webhooks as _webhooks_mod  # noqa: E402
import routers.profile as _profile_mod  # noqa: E402

_central_cache = {}
for prefix in _modules_to_isolate:
    for k in list(sys.modules):
        if k == prefix or k.startswith(prefix + "."):
            _central_cache[k] = sys.modules.pop(k)

sys.modules.update(_saved_modules)
sys.path[:] = _saved_path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def seed_expert(session_factory):
    """Crée un expert de test en base et retourne l'objet."""
    async with session_factory() as session:
        expert = _Expert(
            cognito_sub="sub-test-123",
            email="expert@example.com",
            nom="Dupont",
            prenom="Jean",
            adresse="12 rue de la Paix",
            domaine="psychologie",
        )
        session.add(expert)
        await session.commit()
        await session.refresh(expert)
        return expert


def _fake_get_current_expert(expert):
    """Retourne une dépendance qui simule un expert authentifié."""
    async def _override():
        return (expert, "fake-access-token")
    return _override


@pytest_asyncio.fixture
async def client(session_factory, seed_expert):
    """AsyncClient wired to the FastAPI app with an in-memory DB."""

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    _app.dependency_overrides[_get_db] = _override_get_db
    _app.dependency_overrides[_profile_mod.get_current_expert] = _fake_get_current_expert(seed_expert)

    # Restore central backend modules for the duration of the test
    saved = {}
    for k, v in _central_cache.items():
        if k in sys.modules:
            saved[k] = sys.modules[k]
        sys.modules[k] = v
    sys.path.insert(0, _central_backend)

    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Cleanup
    sys.path.remove(_central_backend)
    for k in list(_central_cache.keys()):
        sys.modules.pop(k, None)
    sys.modules.update(saved)
    _app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauth_client(session_factory):
    """AsyncClient without authentication override (for verify endpoint)."""

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    _app.dependency_overrides[_get_db] = _override_get_db

    # Restore central backend modules for the duration of the test
    saved = {}
    for k, v in _central_cache.items():
        if k in sys.modules:
            saved[k] = sys.modules[k]
        sys.modules[k] = v
    sys.path.insert(0, _central_backend)

    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Cleanup
    sys.path.remove(_central_backend)
    for k in list(_central_cache.keys()):
        sys.modules.pop(k, None)
    sys.modules.update(saved)
    _app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/tickets/purchase — Création session Stripe
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_purchase_creates_stripe_session(client: AsyncClient):
    """L'achat crée une session Stripe et retourne l'URL checkout."""
    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/pay/cs_test_123"

    with patch.object(_tickets_mod, "stripe_service") as mock_ss:
        mock_ss.create_checkout_session.return_value = mock_session
        resp = await client.post("/api/tickets/purchase", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["checkout_url"] == "https://checkout.stripe.com/pay/cs_test_123"


# ---------------------------------------------------------------------------
# GET /api/tickets/list — Liste des tickets de l'expert
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_tickets_returns_expert_tickets(
    client: AsyncClient, session_factory, seed_expert,
):
    """La liste retourne les tickets de l'expert connecté."""
    async with session_factory() as session:
        for i in range(3):
            ticket = _Ticket(
                ticket_code=f"ticket-{uuid4().hex[:8]}",
                expert_id=seed_expert.id,
                domaine="psychologie",
                statut="actif",
                montant=Decimal("49.99"),
                stripe_payment_id=f"pi_test_{i}",
            )
            session.add(ticket)
        await session.commit()

    resp = await client.get("/api/tickets/list")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert all(t["domaine"] == "psychologie" for t in data)


# ---------------------------------------------------------------------------
# POST /api/tickets/verify — Vérification de ticket
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_ticket_success(unauth_client: AsyncClient, session_factory, seed_expert):
    """Un ticket actif est marqué 'utilisé' et retourne success."""
    code = f"ticket-{uuid4().hex[:8]}"
    async with session_factory() as session:
        ticket = _Ticket(
            ticket_code=code,
            expert_id=seed_expert.id,
            domaine="psychologie",
            statut="actif",
            montant=Decimal("49.99"),
            stripe_payment_id="pi_test_verify",
        )
        session.add(ticket)
        await session.commit()

    # Mock verify_ticket_token to return a valid payload
    with patch.object(_tickets_mod, "verify_ticket_token", return_value={
        "valid": True,
        "payload": {"ticket_code": code, "email": "expert@example.com"},
    }):
        resp = await unauth_client.post("/api/tickets/verify", json={"ticket_token": "signed-token-123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["ticket_code"] == code
    assert data.get("error") is None


@pytest.mark.asyncio
async def test_verify_ticket_already_used(unauth_client: AsyncClient, session_factory, seed_expert):
    """Un ticket déjà utilisé retourne l'erreur 'déjà utilisé'."""
    code = f"ticket-{uuid4().hex[:8]}"
    async with session_factory() as session:
        ticket = _Ticket(
            ticket_code=code,
            expert_id=seed_expert.id,
            domaine="psychologie",
            statut="utilisé",
            montant=Decimal("49.99"),
            stripe_payment_id="pi_test_used",
        )
        session.add(ticket)
        await session.commit()

    with patch.object(_tickets_mod, "verify_ticket_token", return_value={
        "valid": True,
        "payload": {"ticket_code": code, "email": "expert@example.com"},
    }):
        resp = await unauth_client.post("/api/tickets/verify", json={"ticket_token": "signed-token-used"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error"] == "déjà utilisé"


@pytest.mark.asyncio
async def test_verify_ticket_not_found(unauth_client: AsyncClient):
    """Un ticket inexistant retourne l'erreur 'invalide'."""
    with patch.object(_tickets_mod, "verify_ticket_token", return_value={
        "valid": True,
        "payload": {"ticket_code": "nonexistent-code", "email": "test@example.com"},
    }):
        resp = await unauth_client.post(
            "/api/tickets/verify",
            json={"ticket_token": "signed-token-notfound"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error"] == "invalide"


# ---------------------------------------------------------------------------
# POST /api/webhooks/stripe — Webhook Stripe
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_webhook_processes_payment_and_creates_ticket(
    unauth_client: AsyncClient, session_factory, seed_expert,
):
    """Le webhook checkout.session.completed crée un ticket et envoie un email."""
    event_data = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {
                    "expert_id": str(seed_expert.id),
                    "domaine": "psychologie",
                },
                "customer_email": "expert@example.com",
                "payment_intent": "pi_webhook_test",
                "amount_total": 4999,
            }
        },
    }

    with (
        patch.object(_webhooks_mod, "stripe_service") as mock_ss,
        patch.object(_webhooks_mod, "email_service") as mock_es,
    ):
        mock_ss.verify_webhook_signature.return_value = event_data
        mock_es.send_ticket_email.return_value = {}

        resp = await unauth_client.post(
            "/api/webhooks/stripe",
            content=b"raw-payload",
            headers={"stripe-signature": "sig_test"},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Vérifier que le ticket a été créé en base
    async with session_factory() as session:
        result = await session.execute(
            select(_Ticket).where(_Ticket.expert_id == seed_expert.id)
        )
        tickets = result.scalars().all()
        assert len(tickets) == 1
        assert tickets[0].statut == "actif"
        assert tickets[0].domaine == "psychologie"
        assert tickets[0].montant == Decimal("49.99")

    mock_es.send_ticket_email.assert_called_once()
