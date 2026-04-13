"""Tests unitaires pour le router de profil du Site Central."""

import sys
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
    Path(__file__).resolve().parents[2] / "site-central" / "aws" / "web" / "backend"
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
from database import get_db as _get_db  # noqa: E402
from main import app as _app  # noqa: E402

import routers.profile as _central_profile_mod  # noqa: E402

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
    """Crée un expert de test en base."""
    async with session_factory() as session:
        expert = _Expert(
            cognito_sub="sub-123",
            email="expert@example.com",
            nom="Dupont",
            prenom="Jean",
            adresse="12 rue de la Paix, 75001 Paris",
            domaine="psychologie",
            accept_newsletter=False,
        )
        session.add(expert)
        await session.commit()
        await session.refresh(expert)
        return expert


@pytest_asyncio.fixture
async def client(session_factory, seed_expert):
    """AsyncClient wired to the FastAPI app with an in-memory DB and a seeded expert."""

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    _app.dependency_overrides[_get_db] = _override_get_db
    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.clear()


def _auth_header(token: str = "valid-access-token") -> dict:
    return {"Authorization": f"Bearer {token}"}


def _mock_get_user_ok(username: str = "sub-123"):
    """Returns a mock get_user response."""
    return {"Username": username, "UserAttributes": []}


# ---------------------------------------------------------------------------
# GET /api/profile — Récupérer le profil
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_profile_success(client: AsyncClient):
    with patch.object(_central_profile_mod, "cognito_service") as mock_cs:
        mock_cs.get_user.return_value = _mock_get_user_ok()
        resp = await client.get("/api/profile", headers=_auth_header())

    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "expert@example.com"
    assert data["nom"] == "Dupont"
    assert data["prenom"] == "Jean"
    assert data["domaine"] == "psychologie"


# ---------------------------------------------------------------------------
# PUT /api/profile — Mettre à jour le profil
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_profile_success(client: AsyncClient):
    with patch.object(_central_profile_mod, "cognito_service") as mock_cs:
        mock_cs.get_user.return_value = _mock_get_user_ok()
        resp = await client.put(
            "/api/profile",
            headers=_auth_header(),
            json={"nom": "Martin", "accept_newsletter": True},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["nom"] == "Martin"
    assert data["accept_newsletter"] is True
    # Unchanged fields remain
    assert data["prenom"] == "Jean"


# ---------------------------------------------------------------------------
# PUT /api/profile/password — Changer le mot de passe
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_change_password_success(client: AsyncClient):
    with patch.object(_central_profile_mod, "cognito_service") as mock_cs:
        mock_cs.get_user.return_value = _mock_get_user_ok()
        mock_cs.change_password.return_value = {}
        resp = await client.put(
            "/api/profile/password",
            headers=_auth_header(),
            json={"old_password": "OldP@ss1", "new_password": "NewP@ss1"},
        )

    assert resp.status_code == 200
    assert "modifié" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_change_password_wrong_old_password(client: AsyncClient):
    from botocore.exceptions import ClientError

    with patch.object(_central_profile_mod, "cognito_service") as mock_cs:
        mock_cs.get_user.return_value = _mock_get_user_ok()
        mock_cs.change_password.side_effect = ClientError(
            {"Error": {"Code": "NotAuthorizedException", "Message": "Incorrect password"}},
            "ChangePassword",
        )
        resp = await client.put(
            "/api/profile/password",
            headers=_auth_header(),
            json={"old_password": "wrong", "new_password": "NewP@ss1"},
        )

    assert resp.status_code == 400
    assert "incorrect" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# DELETE /api/profile/delete — Supprimer le compte
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_account_success(client: AsyncClient):
    with patch.object(_central_profile_mod, "cognito_service") as mock_cs:
        mock_cs.get_user.return_value = _mock_get_user_ok()
        mock_cs.delete_user.return_value = {}
        resp = await client.delete("/api/profile/delete", headers=_auth_header())

    assert resp.status_code == 200
    assert "supprimé" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_deleted_account_cannot_access_profile(client: AsyncClient, session_factory):
    """After deletion, the expert should no longer be found."""
    # First delete
    with patch.object(_central_profile_mod, "cognito_service") as mock_cs:
        mock_cs.get_user.return_value = _mock_get_user_ok()
        mock_cs.delete_user.return_value = {}
        resp = await client.delete("/api/profile/delete", headers=_auth_header())
    assert resp.status_code == 200

    # Then try to access profile — should fail
    with patch.object(_central_profile_mod, "cognito_service") as mock_cs:
        mock_cs.get_user.return_value = _mock_get_user_ok()
        resp = await client.get("/api/profile", headers=_auth_header())
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Unauthorized access — missing/invalid token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_profile_no_auth_header(client: AsyncClient):
    resp = await client.get("/api/profile")
    assert resp.status_code == 422  # missing required header


@pytest.mark.asyncio
async def test_get_profile_invalid_token(client: AsyncClient):
    from botocore.exceptions import ClientError

    with patch.object(_central_profile_mod, "cognito_service") as mock_cs:
        mock_cs.get_user.side_effect = ClientError(
            {"Error": {"Code": "NotAuthorizedException", "Message": "Invalid token"}},
            "GetUser",
        )
        resp = await client.get("/api/profile", headers=_auth_header("bad-token"))

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_profile_bad_bearer_format(client: AsyncClient):
    resp = await client.get("/api/profile", headers={"Authorization": "Basic abc"})
    assert resp.status_code == 401
