"""Tests unitaires pour le router de gestion des dossiers."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Backend sur le path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend"))

from models import Base, LocalConfig, Dossier, Step
from database import get_db
from main import app
from routers.auth import get_current_user

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
async def client(session_factory):
    """AsyncClient with in-memory DB and mocked auth."""

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    async def _override_auth():
        return {"sub": "local_admin", "domaine": "psychologie"}

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_auth
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _setup_config(client: AsyncClient):
    """Helper: create initial config via setup endpoint."""
    original_auth = app.dependency_overrides.get(get_current_user)
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]

    resp = await client.post("/api/auth/setup", json={
        "password": "secret123",
        "domaine": "psychologie",
    })
    assert resp.status_code == 201

    if original_auth is not None:
        app.dependency_overrides[get_current_user] = original_auth

    # Install RAG so config is complete — mock the Site Central call
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []
    with patch("routers.config.SiteCentralClient.get", new_callable=AsyncMock, return_value=mock_resp):
        resp = await client.post("/api/config/rag-install", json={"version": "1.0.0"})
    assert resp.status_code == 200


def _mock_verify_ticket_success():
    """Patch _verify_ticket to return valid."""
    return patch(
        "routers.dossiers._verify_ticket",
        new_callable=AsyncMock,
        return_value={"valid": True, "message": "Ticket valide"},
    )


def _mock_verify_ticket_failure(message: str = "Ticket invalide"):
    """Patch _verify_ticket to return invalid."""
    return patch(
        "routers.dossiers._verify_ticket",
        new_callable=AsyncMock,
        return_value={"valid": False, "message": message},
    )


# ---------------------------------------------------------------------------
# GET /api/dossiers — list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_dossiers_empty(client: AsyncClient):
    await _setup_config(client)
    resp = await client.get("/api/dossiers")
    assert resp.status_code == 200
    assert resp.json()["dossiers"] == []


@pytest.mark.asyncio
async def test_list_dossiers_sorted_desc(client: AsyncClient):
    """Dossiers should be returned most recent first."""
    await _setup_config(client)

    with _mock_verify_ticket_success():
        await client.post("/api/dossiers", json={"nom": "Dossier A", "ticket_id": "T-001"})
        await client.post("/api/dossiers", json={"nom": "Dossier B", "ticket_id": "T-002"})

    resp = await client.get("/api/dossiers")
    assert resp.status_code == 200
    dossiers = resp.json()["dossiers"]
    assert len(dossiers) == 2
    # Most recent first (tiebreaker on id DESC)
    assert dossiers[0]["nom"] == "Dossier B"
    assert dossiers[1]["nom"] == "Dossier A"


# ---------------------------------------------------------------------------
# POST /api/dossiers — create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_dossier_success(client: AsyncClient):
    await _setup_config(client)

    with _mock_verify_ticket_success():
        resp = await client.post("/api/dossiers", json={"nom": "Mon dossier", "ticket_id": "T-100"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["nom"] == "Mon dossier"
    assert data["ticket_id"] == "T-100"
    assert data["domaine"] == "psychologie"
    assert data["statut"] == "actif"
    # 4 steps created
    assert len(data["steps"]) == 4
    for i, step in enumerate(data["steps"]):
        assert step["step_number"] == i
        assert step["statut"] == "initial"


@pytest.mark.asyncio
async def test_create_dossier_empty_nom(client: AsyncClient):
    await _setup_config(client)
    resp = await client.post("/api/dossiers", json={"nom": "", "ticket_id": "T-100"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_dossier_missing_ticket(client: AsyncClient):
    await _setup_config(client)
    resp = await client.post("/api/dossiers", json={"nom": "Test"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_dossier_ticket_invalid(client: AsyncClient):
    await _setup_config(client)

    with _mock_verify_ticket_failure("Ticket invalide"):
        resp = await client.post("/api/dossiers", json={"nom": "Test", "ticket_id": "BAD"})

    assert resp.status_code == 400
    assert "invalide" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_dossier_duplicate_ticket(client: AsyncClient):
    await _setup_config(client)

    with _mock_verify_ticket_success():
        resp1 = await client.post("/api/dossiers", json={"nom": "D1", "ticket_id": "T-DUP"})
        assert resp1.status_code == 201

        resp2 = await client.post("/api/dossiers", json={"nom": "D2", "ticket_id": "T-DUP"})
        assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_create_dossier_site_central_unavailable(client: AsyncClient):
    """When Site Central is unreachable, return 503."""
    await _setup_config(client)

    import httpx as httpx_mod
    with patch(
        "routers.dossiers._verify_ticket",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=503, detail="Site Central indisponible"),
    ):
        resp = await client.post("/api/dossiers", json={"nom": "Test", "ticket_id": "T-NET"})

    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# GET /api/dossiers/{id} — detail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_dossier_detail(client: AsyncClient):
    await _setup_config(client)

    with _mock_verify_ticket_success():
        create_resp = await client.post("/api/dossiers", json={"nom": "Detail", "ticket_id": "T-DET"})
    dossier_id = create_resp.json()["id"]

    resp = await client.get(f"/api/dossiers/{dossier_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["nom"] == "Detail"
    assert len(data["steps"]) == 4


@pytest.mark.asyncio
async def test_get_dossier_not_found(client: AsyncClient):
    await _setup_config(client)
    resp = await client.get("/api/dossiers/9999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/dossiers/{id}/steps/{step} — step detail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_step_detail(client: AsyncClient):
    await _setup_config(client)

    with _mock_verify_ticket_success():
        create_resp = await client.post("/api/dossiers", json={"nom": "Steps", "ticket_id": "T-STP"})
    dossier_id = create_resp.json()["id"]

    for step_num in range(4):
        resp = await client.get(f"/api/dossiers/{dossier_id}/steps/{step_num}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["step_number"] == step_num
        assert data["statut"] == "initial"
        assert data["files"] == []


@pytest.mark.asyncio
async def test_get_step_invalid_number(client: AsyncClient):
    await _setup_config(client)

    with _mock_verify_ticket_success():
        create_resp = await client.post("/api/dossiers", json={"nom": "Bad", "ticket_id": "T-BAD"})
    dossier_id = create_resp.json()["id"]

    resp = await client.get(f"/api/dossiers/{dossier_id}/steps/5")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_step_dossier_not_found(client: AsyncClient):
    await _setup_config(client)
    resp = await client.get("/api/dossiers/9999/steps/0")
    assert resp.status_code == 404


# We need the import for the side_effect test
from fastapi import HTTPException
