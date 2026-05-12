"""Tests unitaires pour le router d'authentification locale.

Teste les endpoints POST /api/auth/login et GET /api/auth/info
ainsi que les helpers JWT (_create_access_token, get_current_user).

Le login local vérifie les credentials auprès du Site Central via
SiteCentralClient, puis génère un JWT local.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Backend sur le path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend"))

from models import Base, LocalConfig
from database import get_db
from main import app
from routers.auth import _create_access_token, get_current_user


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
    """AsyncClient wired to the FastAPI app with an in-memory DB."""

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------


def test_create_access_token_returns_string():
    token = _create_access_token({"sub": "user@test.com", "domaine": "psychologie"})
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_access_token_contains_claims():
    from jose import jwt as jose_jwt
    from routers.auth import JWT_SECRET, JWT_ALGORITHM

    token = _create_access_token({"sub": "user@test.com", "domaine": "psychologie"})
    payload = jose_jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    assert payload["sub"] == "user@test.com"
    assert payload["domaine"] == "psychologie"
    assert "exp" in payload


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Login succeeds when Site Central returns 200."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "central_token"}

    with patch(
        "routers.auth.SiteCentralClient.post",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        resp = await client.post("/api/auth/login", json={
            "email": "user@test.com",
            "password": "secret123",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["email"] == "user@test.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Login fails with 401 when Site Central returns 401."""
    mock_response = MagicMock()
    mock_response.status_code = 401

    with patch(
        "routers.auth.SiteCentralClient.post",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        resp = await client.post("/api/auth/login", json={
            "email": "user@test.com",
            "password": "wrong",
        })

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_central_unavailable(client: AsyncClient):
    """Login fails with 503 when Site Central is unreachable."""
    from services.site_central_client import SiteCentralError

    with patch(
        "routers.auth.SiteCentralClient.post",
        new_callable=AsyncMock,
        side_effect=SiteCentralError("Connection refused"),
    ):
        resp = await client.post("/api/auth/login", json={
            "email": "user@test.com",
            "password": "secret123",
        })

    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_login_validation_missing_email(client: AsyncClient):
    """Login fails with 422 when email is missing."""
    resp = await client.post("/api/auth/login", json={
        "password": "secret123",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_validation_empty_password(client: AsyncClient):
    """Login fails with 422 when password is empty."""
    resp = await client.post("/api/auth/login", json={
        "email": "user@test.com",
        "password": "",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/auth/info
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_info_no_config(client: AsyncClient):
    """Returns configured=False when no LocalConfig exists."""
    resp = await client.get("/api/auth/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["configured"] is False


@pytest.mark.asyncio
async def test_info_with_config(client: AsyncClient):
    """Returns email and domaine after a successful login."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "central_token"}

    with patch(
        "routers.auth.SiteCentralClient.post",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        await client.post("/api/auth/login", json={
            "email": "user@test.com",
            "password": "secret123",
        })

    resp = await client.get("/api/auth/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["configured"] is True
    assert data["email"] == "user@test.com"
    assert data["domaine"] == "psychologie"


# ---------------------------------------------------------------------------
# Auth dependency (get_current_user)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_token(client: AsyncClient):
    """Verify that get_current_user raises 401 for a bad token."""
    from fastapi import Depends

    @app.get("/api/_test_auth")
    async def _test_route(user: dict = Depends(get_current_user)):
        return user

    resp = await client.get(
        "/api/_test_auth",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401

    # Clean up the temporary route
    app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/api/_test_auth"]


@pytest.mark.asyncio
async def test_get_current_user_accepts_valid_token(client: AsyncClient):
    """Verify that get_current_user accepts a valid JWT."""
    from fastapi import Depends

    token = _create_access_token({"sub": "user@test.com", "domaine": "psychologie"})

    @app.get("/api/_test_auth2")
    async def _test_route(user: dict = Depends(get_current_user)):
        return user

    resp = await client.get(
        "/api/_test_auth2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sub"] == "user@test.com"

    # Clean up
    app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/api/_test_auth2"]
