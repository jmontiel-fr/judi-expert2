"""Tests unitaires pour le router de vérification de ticket standalone.

Valide : Exigences 5.2, 5.3, 5.4, 35.6, 35.7
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend"))

from models import Base
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_httpx_response(status_code: int = 200, json_body: dict | None = None):
    """Create a mock httpx.Response."""
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_body or {}
    return mock_resp


# ---------------------------------------------------------------------------
# POST /api/tickets/verify — success (Site Central returns success=True)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_ticket_valid(client: AsyncClient):
    mock_resp = _mock_httpx_response(200, {"success": True, "ticket_code": "T-VALID"})
    with patch("services.site_central_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        resp = await client.post("/api/tickets/verify", json={"ticket_code": "T-VALID"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["message"] == "Ticket valide"


# ---------------------------------------------------------------------------
# POST /api/tickets/verify — invalid ticket (Site Central returns success=False)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_ticket_invalid(client: AsyncClient):
    mock_resp = _mock_httpx_response(200, {
        "success": False, "ticket_code": "T-BAD", "error": "invalide"
    })
    with patch("services.site_central_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        resp = await client.post("/api/tickets/verify", json={"ticket_code": "T-BAD"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert "invalide" in data["message"].lower()


@pytest.mark.asyncio
async def test_verify_ticket_already_used(client: AsyncClient):
    mock_resp = _mock_httpx_response(200, {
        "success": False, "ticket_code": "T-USED", "error": "déjà utilisé"
    })
    with patch("services.site_central_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        resp = await client.post("/api/tickets/verify", json={"ticket_code": "T-USED"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert "utilisé" in data["message"]


# ---------------------------------------------------------------------------
# POST /api/tickets/verify — network errors (SiteCentralError after retries)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_ticket_connect_error(client: AsyncClient):
    with patch("services.site_central_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        # Patch sleep to avoid waiting during retries
        with patch("services.site_central_client.asyncio.sleep", new_callable=AsyncMock):
            resp = await client.post("/api/tickets/verify", json={"ticket_code": "T-NET"})

    assert resp.status_code == 503
    assert "indisponible" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_verify_ticket_timeout(client: AsyncClient):
    with patch("services.site_central_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ReadTimeout("Timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with patch("services.site_central_client.asyncio.sleep", new_callable=AsyncMock):
            resp = await client.post("/api/tickets/verify", json={"ticket_code": "T-TIMEOUT"})

    assert resp.status_code == 503
    assert "délai" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_verify_ticket_other_http_error(client: AsyncClient):
    with patch("services.site_central_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.HTTPError("Some error")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with patch("services.site_central_client.asyncio.sleep", new_callable=AsyncMock):
            resp = await client.post("/api/tickets/verify", json={"ticket_code": "T-ERR"})

    assert resp.status_code == 503
    assert "erreur réseau" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /api/tickets/verify — validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_ticket_empty_code(client: AsyncClient):
    resp = await client.post("/api/tickets/verify", json={"ticket_code": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_verify_ticket_missing_body(client: AsyncClient):
    resp = await client.post("/api/tickets/verify", json={})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/tickets/verify — business hours message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_ticket_unavailable_outside_business_hours(client: AsyncClient):
    """When Site Central is down outside business hours, message should mention hours."""
    with patch("services.site_central_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with patch("services.site_central_client.asyncio.sleep", new_callable=AsyncMock):
            with patch("services.site_central_client.is_within_business_hours", return_value=False):
                resp = await client.post("/api/tickets/verify", json={"ticket_code": "T-NIGHT"})

    assert resp.status_code == 503
    detail = resp.json()["detail"]
    assert "8h" in detail and "20h" in detail
