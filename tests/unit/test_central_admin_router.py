"""Tests unitaires pour les routers contact et administration du Site Central."""

import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

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
from models.contact_message import ContactMessage as _ContactMessage  # noqa: E402
from database import get_db as _get_db  # noqa: E402
from main import app as _app  # noqa: E402

import routers.profile as _profile_mod  # noqa: E402
import routers.admin as _admin_mod  # noqa: E402

_central_cache = {}
for prefix in _modules_to_isolate:
    for k in list(sys.modules):
        if k == prefix or k.startswith(prefix + "."):
            _central_cache[k] = sys.modules.pop(k)

sys.modules.update(_saved_modules)
sys.path[:] = _saved_path

ADMIN_EMAIL = "admin@judi-expert.fr"


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
async def seed_admin(session_factory):
    """Crée un expert admin en base."""
    async with session_factory() as session:
        expert = _Expert(
            cognito_sub="sub-admin-001",
            email=ADMIN_EMAIL,
            nom="Admin",
            prenom="Super",
            adresse="1 rue Admin",
            domaine="psychologie",
        )
        session.add(expert)
        await session.commit()
        await session.refresh(expert)
        return expert


@pytest_asyncio.fixture
async def seed_regular_expert(session_factory):
    """Crée un expert non-admin en base."""
    async with session_factory() as session:
        expert = _Expert(
            cognito_sub="sub-regular-001",
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
async def admin_client(session_factory, seed_admin):
    """AsyncClient authentifié en tant qu'admin."""
    async def _override_get_db():
        async with session_factory() as session:
            yield session

    _app.dependency_overrides[_get_db] = _override_get_db
    _app.dependency_overrides[_profile_mod.get_current_expert] = _fake_get_current_expert(seed_admin)

    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def regular_client(session_factory, seed_regular_expert):
    """AsyncClient authentifié en tant qu'expert non-admin."""
    async def _override_get_db():
        async with session_factory() as session:
            yield session

    _app.dependency_overrides[_get_db] = _override_get_db
    _app.dependency_overrides[_profile_mod.get_current_expert] = _fake_get_current_expert(seed_regular_expert)

    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauth_client(session_factory):
    """AsyncClient sans authentification."""
    async def _override_get_db():
        async with session_factory() as session:
            yield session

    _app.dependency_overrides[_get_db] = _override_get_db
    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/contact — Formulaire de contact
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_contact_submit_success(unauth_client: AsyncClient):
    """Soumission d'un message de contact sans authentification."""
    resp = await unauth_client.post("/api/contact", json={
        "domaine": "psychologie",
        "objet": "Problème",
        "message": "J'ai un problème avec mon compte.",
        "captcha_token": "test-captcha-token",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "succès" in data["message"].lower() or "succes" in data["message"].lower()


@pytest.mark.asyncio
async def test_contact_submit_missing_fields(unauth_client: AsyncClient):
    """Soumission avec champs manquants retourne 422."""
    # Missing message
    resp = await unauth_client.post("/api/contact", json={
        "domaine": "psychologie",
        "objet": "Problème",
    })
    assert resp.status_code == 422

    # Missing objet
    resp = await unauth_client.post("/api/contact", json={
        "domaine": "psychologie",
        "message": "Un message",
    })
    assert resp.status_code == 422

    # Missing domaine
    resp = await unauth_client.post("/api/contact", json={
        "objet": "Autre",
        "message": "Un message",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_contact_submit_empty_fields(unauth_client: AsyncClient):
    """Soumission avec champs vides retourne 422."""
    resp = await unauth_client.post("/api/contact", json={
        "domaine": "",
        "objet": "Problème",
        "message": "Un message",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/admin/experts — Liste des experts (admin)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_list_experts_as_admin(admin_client: AsyncClient, session_factory):
    """L'admin peut lister les experts inscrits."""
    # Seed a second expert
    async with session_factory() as session:
        expert2 = _Expert(
            cognito_sub="sub-expert-002",
            email="expert2@example.com",
            nom="Martin",
            prenom="Marie",
            adresse="5 avenue des Champs",
            domaine="batiment",
        )
        session.add(expert2)
        await session.commit()

    resp = await admin_client.get("/api/admin/experts")
    assert resp.status_code == 200
    data = resp.json()
    # Admin + expert2
    assert len(data) >= 2
    emails = [e["email"] for e in data]
    assert ADMIN_EMAIL in emails
    assert "expert2@example.com" in emails


@pytest.mark.asyncio
async def test_admin_list_experts_as_non_admin(regular_client: AsyncClient):
    """Un expert non-admin reçoit 403."""
    resp = await regular_client.get("/api/admin/experts")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /api/admin/stats/tickets — Statistiques tickets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_stats_tickets_tous(admin_client: AsyncClient, session_factory, seed_admin):
    """Statistiques avec filtre 'Tous' retourne tous les tickets."""
    now = datetime.now(timezone.utc)
    async with session_factory() as session:
        # Ticket today
        t1 = _Ticket(
            ticket_code="ticket-today-001",
            expert_id=seed_admin.id,
            domaine="psychologie",
            statut="actif",
            montant=Decimal("49.99"),
            stripe_payment_id="pi_today_1",
            created_at=now,
        )
        # Ticket last month
        last_month = now.replace(day=1) - timedelta(days=1)
        t2 = _Ticket(
            ticket_code="ticket-past-001",
            expert_id=seed_admin.id,
            domaine="batiment",
            statut="actif",
            montant=Decimal("29.99"),
            stripe_payment_id="pi_past_1",
            created_at=last_month,
        )
        session.add_all([t1, t2])
        await session.commit()

    resp = await admin_client.get("/api/admin/stats/tickets", params={"domaine": "Tous"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["today_count"] >= 1
    assert float(data["today_amount"]) >= 49.99
    assert data["month_count"] >= 1


@pytest.mark.asyncio
async def test_admin_stats_tickets_domain_filter(admin_client: AsyncClient, session_factory, seed_admin):
    """Statistiques avec filtre par domaine retourne uniquement ce domaine."""
    now = datetime.now(timezone.utc)
    async with session_factory() as session:
        t1 = _Ticket(
            ticket_code="ticket-psy-001",
            expert_id=seed_admin.id,
            domaine="psychologie",
            statut="actif",
            montant=Decimal("49.99"),
            stripe_payment_id="pi_psy_1",
            created_at=now,
        )
        t2 = _Ticket(
            ticket_code="ticket-bat-001",
            expert_id=seed_admin.id,
            domaine="batiment",
            statut="actif",
            montant=Decimal("29.99"),
            stripe_payment_id="pi_bat_1",
            created_at=now,
        )
        session.add_all([t1, t2])
        await session.commit()

    resp = await admin_client.get("/api/admin/stats/tickets", params={"domaine": "psychologie"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["today_count"] == 1
    assert float(data["today_amount"]) == pytest.approx(49.99, abs=0.01)

    resp2 = await admin_client.get("/api/admin/stats/tickets", params={"domaine": "batiment"})
    data2 = resp2.json()
    assert data2["today_count"] == 1
    assert float(data2["today_amount"]) == pytest.approx(29.99, abs=0.01)
