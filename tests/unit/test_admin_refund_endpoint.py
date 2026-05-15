"""Tests unitaires pour l'endpoint admin de remboursement de ticket.

Teste l'endpoint POST /api/admin/tickets/{ticket_id}/refund ajouté dans
routers/admin.py.

Exigences validées : 4.1, 4.2, 4.3, 4.4, 4.5
"""

import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
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

import routers.admin as _admin_mod  # noqa: E402
import routers.profile as _profile_mod  # noqa: E402

# Cache central modules, then restore originals
_central_cache = {}
for prefix in _modules_to_isolate:
    for k in list(sys.modules):
        if k == prefix or k.startswith(prefix + "."):
            _central_cache[k] = sys.modules.pop(k)

sys.modules.update(_saved_modules)
sys.path[:] = _saved_path


# ---------------------------------------------------------------------------
# Admin email (matches default in routers/admin.py)
# ---------------------------------------------------------------------------
_ADMIN_EMAIL = "admin@judi-expert.fr"


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
async def client(session_factory):
    """AsyncClient wired to the FastAPI app with an in-memory DB."""

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    _app.dependency_overrides[_get_db] = _override_get_db
    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_admin_expert() -> _Expert:
    """Return an Expert instance with admin email."""
    return _Expert(
        id=1,
        cognito_sub="admin-sub-001",
        email=_ADMIN_EMAIL,
        nom="Admin",
        prenom="Super",
        adresse="1 rue Admin",
        ville="Paris",
        code_postal="75001",
        telephone="0100000000",
        domaine="psychologie",
        accept_newsletter=False,
        is_deleted=False,
    )


def _make_active_ticket(
    ticket_id: int = 10,
    stripe_payment_id: str = "pi_abc123",
) -> _Ticket:
    """Return a Ticket with status 'actif' and a valid stripe_payment_id."""
    return _Ticket(
        id=ticket_id,
        ticket_code="TK-TEST-001",
        expert_id=1,
        domaine="psychologie",
        statut="actif",
        montant=Decimal("58.80"),
        stripe_payment_id=stripe_payment_id,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


async def _seed_admin_and_ticket(session_factory, **ticket_kwargs):
    """Seed the DB with an admin expert and a ticket."""
    async with session_factory() as session:
        admin = _make_admin_expert()
        session.add(admin)
        await session.flush()

        ticket = _make_active_ticket(**ticket_kwargs)
        ticket.expert_id = admin.id
        session.add(ticket)
        await session.commit()
        return ticket.id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refund_ticket_not_found(client: AsyncClient, session_factory):
    """POST /api/admin/tickets/999/refund retourne 404 si ticket inexistant."""
    admin = _make_admin_expert()

    async with session_factory() as session:
        session.add(admin)
        await session.commit()

    async def _override_admin():
        return admin

    _app.dependency_overrides[_admin_mod.get_admin_expert] = _override_admin
    try:
        resp = await client.post("/api/admin/tickets/999/refund")
    finally:
        _app.dependency_overrides.pop(_admin_mod.get_admin_expert, None)

    assert resp.status_code == 404
    assert "introuvable" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_refund_ticket_wrong_status(client: AsyncClient, session_factory):
    """POST refund retourne 400 si le ticket n'est pas 'actif'."""
    async with session_factory() as session:
        admin = _make_admin_expert()
        session.add(admin)
        await session.flush()

        ticket = _Ticket(
            id=20,
            ticket_code="TK-USED-001",
            expert_id=admin.id,
            domaine="psychologie",
            statut="utilise",
            montant=Decimal("58.80"),
            stripe_payment_id="pi_xyz789",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        session.add(ticket)
        await session.commit()

    async def _override_admin():
        return admin

    _app.dependency_overrides[_admin_mod.get_admin_expert] = _override_admin
    try:
        resp = await client.post("/api/admin/tickets/20/refund")
    finally:
        _app.dependency_overrides.pop(_admin_mod.get_admin_expert, None)

    assert resp.status_code == 400
    assert "utilise" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_refund_ticket_pending_payment(client: AsyncClient, session_factory):
    """POST refund retourne 400 si stripe_payment_id commence par 'pending-'."""
    async with session_factory() as session:
        admin = _make_admin_expert()
        session.add(admin)
        await session.flush()

        ticket = _Ticket(
            id=30,
            ticket_code="TK-PEND-001",
            expert_id=admin.id,
            domaine="psychologie",
            statut="actif",
            montant=Decimal("58.80"),
            stripe_payment_id="pending-abc123",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        session.add(ticket)
        await session.commit()

    async def _override_admin():
        return admin

    _app.dependency_overrides[_admin_mod.get_admin_expert] = _override_admin
    try:
        resp = await client.post("/api/admin/tickets/30/refund")
    finally:
        _app.dependency_overrides.pop(_admin_mod.get_admin_expert, None)

    assert resp.status_code == 400
    assert "non finalisé" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_refund_ticket_stripe_error(client: AsyncClient, session_factory):
    """POST refund retourne 502 si Stripe renvoie une erreur."""
    import stripe as _stripe

    ticket_id = await _seed_admin_and_ticket(session_factory)
    admin = _make_admin_expert()

    mock_error = _stripe.error.StripeError("Le paiement a été refusé")

    async def _override_admin():
        return admin

    _app.dependency_overrides[_admin_mod.get_admin_expert] = _override_admin
    try:
        with patch.object(_stripe.Refund, "create", side_effect=mock_error):
            resp = await client.post(f"/api/admin/tickets/{ticket_id}/refund")
    finally:
        _app.dependency_overrides.pop(_admin_mod.get_admin_expert, None)

    assert resp.status_code == 502
    assert "stripe" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_refund_ticket_success(client: AsyncClient, session_factory):
    """POST refund réussit : statut 'rembourse', refunded_at et stripe_refund_id."""
    import stripe as _stripe

    ticket_id = await _seed_admin_and_ticket(session_factory)
    admin = _make_admin_expert()

    mock_refund = MagicMock()
    mock_refund.id = "re_test_refund_123"

    async def _override_admin():
        return admin

    _app.dependency_overrides[_admin_mod.get_admin_expert] = _override_admin
    try:
        with patch.object(_stripe.Refund, "create", return_value=mock_refund):
            resp = await client.post(f"/api/admin/tickets/{ticket_id}/refund")
    finally:
        _app.dependency_overrides.pop(_admin_mod.get_admin_expert, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Remboursement effectué"
    assert "refunded_at" in data

    # Verify DB state
    from sqlalchemy import select as _select

    async with session_factory() as session:
        result = await session.execute(
            _select(_Ticket).where(_Ticket.id == ticket_id)
        )
        ticket = result.scalar_one()
        assert ticket.statut == "rembourse"
        assert ticket.refunded_at is not None
        assert ticket.stripe_refund_id == "re_test_refund_123"
