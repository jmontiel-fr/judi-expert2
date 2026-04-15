"""Tests d'intégration — Flux de paiement Stripe (mode test).

Teste le cycle complet : achat de ticket → webhook Stripe →
génération de ticket → vérification → marquage comme utilisé.

Valide : Exigences 15.1
"""

import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Module isolation : charger le backend Site Central sans conflit
# ---------------------------------------------------------------------------

_central_backend = str(
    Path(__file__).resolve().parents[2]
    / "central-site" / "web" / "backend"
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

# Sauvegarder les modules du Site Central et restaurer les originaux
_central_cache = {}
for prefix in _modules_to_isolate:
    for k in list(sys.modules):
        if k == prefix or k.startswith(prefix + "."):
            _central_cache[k] = sys.modules.pop(k)

sys.modules.update(_saved_modules)
sys.path[:] = _saved_path

pytestmark = pytest.mark.integration


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
    """Crée un expert de test en base."""
    async with session_factory() as session:
        expert = _Expert(
            cognito_sub="sub-stripe-test-123",
            email="expert.stripe@example.com",
            nom="Martin",
            prenom="Sophie",
            adresse="45 avenue des Champs",
            domaine="psychologie",
        )
        session.add(expert)
        await session.commit()
        await session.refresh(expert)
        return expert


def _fake_get_current_expert(expert):
    """Simule un expert authentifié."""
    async def _override():
        return (expert, "fake-access-token")
    return _override


@pytest_asyncio.fixture
async def auth_client(session_factory, seed_expert):
    """Client authentifié (pour purchase et list)."""

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    _app.dependency_overrides[_get_db] = _override_get_db
    _app.dependency_overrides[_profile_mod.get_current_expert] = (
        _fake_get_current_expert(seed_expert)
    )

    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauth_client(session_factory):
    """Client non authentifié (pour webhook et verify)."""

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    _app.dependency_overrides[_get_db] = _override_get_db
    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test E2E : Flux complet Stripe — achat → webhook → vérification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_stripe_payment_flow(
    auth_client: AsyncClient,
    unauth_client: AsyncClient,
    session_factory,
    seed_expert,
):
    """Flux complet : achat → webhook → ticket généré → vérification → utilisé.

    1. Créer une session Stripe Checkout via POST /api/tickets/purchase
    2. Simuler le webhook checkout.session.completed
    3. Vérifier que le ticket est créé avec le bon domaine et statut "actif"
    4. Vérifier que le ticket apparaît dans GET /api/tickets/list
    5. Vérifier le ticket via POST /api/tickets/verify
    6. Vérifier que le ticket est marqué "utilisé" après vérification
    """

    # ── 1. Créer une session Stripe Checkout ──
    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/pay/cs_test_e2e_123"

    with patch.object(_tickets_mod, "stripe_service") as mock_ss:
        mock_ss.create_checkout_session.return_value = mock_session
        resp = await auth_client.post("/api/tickets/purchase", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["checkout_url"] == "https://checkout.stripe.com/pay/cs_test_e2e_123"

    # ── 2. Simuler le webhook Stripe (checkout.session.completed) ──
    event_data = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {
                    "expert_id": str(seed_expert.id),
                    "domaine": "psychologie",
                },
                "customer_email": "expert.stripe@example.com",
                "payment_intent": "pi_e2e_test_001",
                "amount_total": 4999,  # 49.99 €
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
            content=b"raw-stripe-payload",
            headers={"stripe-signature": "sig_test_e2e"},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # ── 3. Vérifier que le ticket est créé en base ──
    async with session_factory() as session:
        result = await session.execute(
            select(_Ticket).where(_Ticket.expert_id == seed_expert.id)
        )
        tickets = result.scalars().all()

    assert len(tickets) == 1
    ticket = tickets[0]
    assert ticket.domaine == "psychologie"
    assert ticket.statut == "actif"
    assert ticket.montant == Decimal("49.99")
    assert ticket.stripe_payment_id == "pi_e2e_test_001"
    ticket_code = ticket.ticket_code
    assert len(ticket_code) > 0  # UUID non vide

    # ── 4. Vérifier que le ticket apparaît dans la liste ──
    resp = await auth_client.get("/api/tickets/list")
    assert resp.status_code == 200
    ticket_list = resp.json()
    assert len(ticket_list) == 1
    assert ticket_list[0]["ticket_code"] == ticket_code
    assert ticket_list[0]["domaine"] == "psychologie"
    assert ticket_list[0]["statut"] == "actif"

    # ── 5. Vérifier le ticket via POST /api/tickets/verify ──
    resp = await unauth_client.post(
        "/api/tickets/verify",
        json={"ticket_code": ticket_code},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["ticket_code"] == ticket_code
    assert data.get("error") is None

    # ── 6. Vérifier que le ticket est maintenant "utilisé" ──
    async with session_factory() as session:
        result = await session.execute(
            select(_Ticket).where(_Ticket.ticket_code == ticket_code)
        )
        updated_ticket = result.scalar_one()

    assert updated_ticket.statut == "utilisé"
    assert updated_ticket.used_at is not None

    # ── 7. Re-vérifier le ticket → doit échouer ("déjà utilisé") ──
    resp = await unauth_client.post(
        "/api/tickets/verify",
        json={"ticket_code": ticket_code},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error"] == "déjà utilisé"


# ---------------------------------------------------------------------------
# Test : Ticket inexistant
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_nonexistent_ticket(unauth_client: AsyncClient):
    """La vérification d'un ticket inexistant retourne 'invalide'."""
    resp = await unauth_client.post(
        "/api/tickets/verify",
        json={"ticket_code": "TICKET-INEXISTANT-XYZ"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error"] == "invalide"


# ---------------------------------------------------------------------------
# Test : Webhook avec signature invalide
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_invalid_signature(unauth_client: AsyncClient):
    """Un webhook avec une signature invalide est rejeté."""
    import stripe as _stripe

    with patch.object(_webhooks_mod, "stripe_service") as mock_ss:
        mock_ss.verify_webhook_signature.side_effect = (
            _stripe.error.SignatureVerificationError("Invalid signature", "sig_header")
        )

        resp = await unauth_client.post(
            "/api/webhooks/stripe",
            content=b"tampered-payload",
            headers={"stripe-signature": "sig_invalid"},
        )

    assert resp.status_code == 400
    assert "signature" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test : Plusieurs achats génèrent des tickets uniques
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_purchases_unique_tickets(
    unauth_client: AsyncClient,
    session_factory,
    seed_expert,
):
    """Deux paiements distincts génèrent des tickets avec des codes différents."""
    ticket_codes = []

    for i in range(2):
        event_data = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {
                        "expert_id": str(seed_expert.id),
                        "domaine": "psychologie",
                    },
                    "customer_email": "expert.stripe@example.com",
                    "payment_intent": f"pi_multi_{i}",
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
                content=f"payload-{i}".encode(),
                headers={"stripe-signature": f"sig_{i}"},
            )
        assert resp.status_code == 200

    # Vérifier que 2 tickets distincts ont été créés
    async with session_factory() as session:
        result = await session.execute(
            select(_Ticket).where(_Ticket.expert_id == seed_expert.id)
        )
        tickets = result.scalars().all()

    assert len(tickets) == 2
    codes = [t.ticket_code for t in tickets]
    assert codes[0] != codes[1], "Les codes de ticket doivent être uniques"
    assert all(t.statut == "actif" for t in tickets)
    assert all(t.domaine == "psychologie" for t in tickets)


# ---------------------------------------------------------------------------
# Test : Le ticket contient le bon montant
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ticket_amount_correct(
    unauth_client: AsyncClient,
    session_factory,
    seed_expert,
):
    """Le montant du ticket correspond au montant Stripe (centimes → euros)."""
    event_data = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {
                    "expert_id": str(seed_expert.id),
                    "domaine": "psychologie",
                },
                "customer_email": "expert.stripe@example.com",
                "payment_intent": "pi_amount_test",
                "amount_total": 9900,  # 99.00 €
            }
        },
    }

    with (
        patch.object(_webhooks_mod, "stripe_service") as mock_ss,
        patch.object(_webhooks_mod, "email_service") as mock_es,
    ):
        mock_ss.verify_webhook_signature.return_value = event_data
        mock_es.send_ticket_email.return_value = {}

        await unauth_client.post(
            "/api/webhooks/stripe",
            content=b"payload-amount",
            headers={"stripe-signature": "sig_amount"},
        )

    async with session_factory() as session:
        result = await session.execute(
            select(_Ticket).where(_Ticket.stripe_payment_id == "pi_amount_test")
        )
        ticket = result.scalar_one()

    assert ticket.montant == Decimal("99.00")
