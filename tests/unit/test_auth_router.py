"""Tests unitaires pour le router d'authentification locale."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Backend sur le path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "site-central" / "local" / "web" / "backend"))

from models import Base, LocalConfig
from database import get_db
from main import app
from routers.auth import _verify_password, _hash_password, _create_access_token, get_current_user

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

def test_hash_and_verify_password():
    hashed = _hash_password("monmotdepasse")
    assert hashed != "monmotdepasse"
    assert _verify_password("monmotdepasse", hashed) is True
    assert _verify_password("mauvais", hashed) is False


def test_create_access_token_returns_string():
    token = _create_access_token({"sub": "local_admin", "domaine": "psychologie"})
    assert isinstance(token, str)
    assert len(token) > 0


# ---------------------------------------------------------------------------
# POST /api/auth/setup
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_setup_success(client: AsyncClient):
    resp = await client.post("/api/auth/setup", json={
        "password": "secret123",
        "domaine": "psychologie",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["domaine"] == "psychologie"
    assert "réussie" in data["message"].lower() or "reussie" in data["message"].lower()


@pytest.mark.asyncio
async def test_setup_conflict_when_already_configured(client: AsyncClient):
    # First setup
    resp1 = await client.post("/api/auth/setup", json={
        "password": "secret123",
        "domaine": "psychologie",
    })
    assert resp1.status_code == 201

    # Second setup should fail
    resp2 = await client.post("/api/auth/setup", json={
        "password": "other",
        "domaine": "batiment",
    })
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_setup_validation_empty_password(client: AsyncClient):
    resp = await client.post("/api/auth/setup", json={
        "password": "ab",
        "domaine": "psychologie",
    })
    assert resp.status_code == 422  # pydantic validation (min_length=4)


@pytest.mark.asyncio
async def test_setup_validation_empty_domaine(client: AsyncClient):
    resp = await client.post("/api/auth/setup", json={
        "password": "secret123",
        "domaine": "",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/auth/setup", json={
        "password": "secret123",
        "domaine": "psychologie",
    })
    resp = await client.post("/api/auth/login", json={"password": "secret123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/setup", json={
        "password": "secret123",
        "domaine": "psychologie",
    })
    resp = await client.post("/api/auth/login", json={"password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_no_config(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={"password": "anything"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Auth dependency (get_current_user)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_protected_endpoint_with_valid_token(client: AsyncClient):
    # Setup + login
    await client.post("/api/auth/setup", json={
        "password": "secret123",
        "domaine": "psychologie",
    })
    login_resp = await client.post("/api/auth/login", json={"password": "secret123"})
    token = login_resp.json()["access_token"]

    # Access health endpoint (not protected, but we can verify the token decodes)
    from jose import jwt as jose_jwt
    from routers.auth import JWT_SECRET, JWT_ALGORITHM
    payload = jose_jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    assert payload["sub"] == "local_admin"
    assert payload["domaine"] == "psychologie"
    assert "exp" in payload


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_token(client: AsyncClient):
    """Verify that get_current_user raises 401 for a bad token."""
    from fastapi import Depends
    from starlette.testclient import TestClient

    # We'll call the dependency directly via a temporary route
    @app.get("/api/_test_auth")
    async def _test_route(user: dict = Depends(get_current_user)):
        return user

    resp = await client.get("/api/_test_auth", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401

    # Clean up the temporary route
    app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/api/_test_auth"]
