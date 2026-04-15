"""Tests unitaires pour le router d'authentification du Site Central (Cognito)."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

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

# Save and clear conflicting modules
_saved_modules = {}
for prefix in _modules_to_isolate:
    for k in list(sys.modules):
        if k == prefix or k.startswith(prefix + "."):
            _saved_modules[k] = sys.modules.pop(k)

_saved_path = sys.path[:]
sys.path.insert(0, _central_backend)

# Import central modules
from models import Base as _Base  # noqa: E402
from database import get_db as _get_db  # noqa: E402
from main import app as _app  # noqa: E402

# Grab direct references to the central router module for patching
import routers.auth as _central_auth_mod  # noqa: E402

# Cache central modules, then restore originals
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


def _valid_register_payload(**overrides):
    """Retourne un payload d'inscription valide avec possibilité d'override."""
    base = {
        "email": "expert@example.com",
        "password": "SecureP@ss1",
        "nom": "Dupont",
        "prenom": "Jean",
        "adresse": "12 rue de la Paix",
        "ville": "Paris",
        "code_postal": "75001",
        "telephone": "0612345678",
        "domaine": "psychologie",
        "accept_mentions_legales": True,
        "accept_cgu": True,
        "accept_protection_donnees": True,
        "accept_newsletter": False,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# POST /api/auth/register
# Patch via direct module reference (avoids sys.modules lookup issues)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    with patch.object(_central_auth_mod, "cognito_service") as mock_cs:
        mock_cs.register_user.return_value = {"UserSub": "abc-123-sub"}
        resp = await client.post("/api/auth/register", json=_valid_register_payload())

    assert resp.status_code == 201
    data = resp.json()
    assert data["cognito_sub"] == "abc-123-sub"
    assert "réussie" in data["message"].lower() or "reussie" in data["message"].lower()


@pytest.mark.asyncio
async def test_register_missing_nom(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json=_valid_register_payload(nom=""),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_prenom(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json=_valid_register_payload(prenom=""),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_adresse(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json=_valid_register_payload(adresse=""),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_domaine(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json=_valid_register_payload(domaine=""),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_mentions_legales_not_accepted(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json=_valid_register_payload(accept_mentions_legales=False),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_cgu_not_accepted(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json=_valid_register_payload(accept_cgu=False),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_protection_donnees_not_accepted(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json=_valid_register_payload(accept_protection_donnees=False),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_newsletter_optional_false(client: AsyncClient):
    """Newsletter=False ne doit pas empêcher l'inscription."""
    with patch.object(_central_auth_mod, "cognito_service") as mock_cs:
        mock_cs.register_user.return_value = {"UserSub": "sub-no-newsletter"}
        resp = await client.post(
            "/api/auth/register",
            json=_valid_register_payload(accept_newsletter=False),
        )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_register_newsletter_optional_true(client: AsyncClient):
    """Newsletter=True ne doit pas empêcher l'inscription."""
    with patch.object(_central_auth_mod, "cognito_service") as mock_cs:
        mock_cs.register_user.return_value = {"UserSub": "sub-with-newsletter"}
        resp = await client.post(
            "/api/auth/register",
            json=_valid_register_payload(accept_newsletter=True),
        )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_register_password_too_short(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json=_valid_register_payload(password="short"),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json=_valid_register_payload(email="not-an-email"),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_cognito_duplicate_email(client: AsyncClient):
    from botocore.exceptions import ClientError

    with patch.object(_central_auth_mod, "cognito_service") as mock_cs:
        mock_cs.register_user.side_effect = ClientError(
            {"Error": {"Code": "UsernameExistsException", "Message": "User exists"}},
            "SignUp",
        )
        resp = await client.post("/api/auth/register", json=_valid_register_payload())
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    with (
        patch.object(_central_auth_mod, "captcha_service") as mock_cap,
        patch.object(_central_auth_mod, "cognito_service") as mock_cog,
    ):
        mock_cap.verify_captcha = AsyncMock(return_value=True)
        mock_cog.login_user.return_value = {
            "AccessToken": "access-tok",
            "IdToken": "id-tok",
            "RefreshToken": "refresh-tok",
        }
        resp = await client.post("/api/auth/login", json={
            "email": "expert@example.com",
            "password": "SecureP@ss1",
            "captcha_token": "valid-captcha",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"] == "access-tok"
    assert data["id_token"] == "id-tok"
    assert data["refresh_token"] == "refresh-tok"


@pytest.mark.asyncio
async def test_login_wrong_password_uniform_error(client: AsyncClient):
    """Exigence 14.3 — message uniforme pour mot de passe incorrect."""
    from botocore.exceptions import ClientError

    with (
        patch.object(_central_auth_mod, "captcha_service") as mock_cap,
        patch.object(_central_auth_mod, "cognito_service") as mock_cog,
    ):
        mock_cap.verify_captcha = AsyncMock(return_value=True)
        mock_cog.login_user.side_effect = ClientError(
            {"Error": {"Code": "NotAuthorizedException", "Message": "Incorrect password"}},
            "InitiateAuth",
        )
        resp = await client.post("/api/auth/login", json={
            "email": "expert@example.com",
            "password": "wrong",
            "captcha_token": "valid-captcha",
        })

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Identifiants invalides"


@pytest.mark.asyncio
async def test_login_wrong_email_uniform_error(client: AsyncClient):
    """Exigence 14.3 — message uniforme pour email incorrect."""
    from botocore.exceptions import ClientError

    with (
        patch.object(_central_auth_mod, "captcha_service") as mock_cap,
        patch.object(_central_auth_mod, "cognito_service") as mock_cog,
    ):
        mock_cap.verify_captcha = AsyncMock(return_value=True)
        mock_cog.login_user.side_effect = ClientError(
            {"Error": {"Code": "UserNotFoundException", "Message": "User not found"}},
            "InitiateAuth",
        )
        resp = await client.post("/api/auth/login", json={
            "email": "unknown@example.com",
            "password": "SecureP@ss1",
            "captcha_token": "valid-captcha",
        })

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Identifiants invalides"


@pytest.mark.asyncio
async def test_login_invalid_captcha(client: AsyncClient):
    with patch.object(_central_auth_mod, "captcha_service") as mock_cap:
        mock_cap.verify_captcha = AsyncMock(return_value=False)
        resp = await client.post("/api/auth/login", json={
            "email": "expert@example.com",
            "password": "SecureP@ss1",
            "captcha_token": "bad-captcha",
        })

    assert resp.status_code == 400
    assert "captcha" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_empty_captcha(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={
        "email": "expert@example.com",
        "password": "SecureP@ss1",
        "captcha_token": "",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient):
    with patch.object(_central_auth_mod, "cognito_service") as mock_cog:
        mock_cog.logout_user.return_value = {}
        resp = await client.post("/api/auth/logout", json={
            "access_token": "some-access-token",
        })

    assert resp.status_code == 200
    assert "réussie" in resp.json()["message"].lower() or "reussie" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_logout_invalid_token(client: AsyncClient):
    from botocore.exceptions import ClientError

    with patch.object(_central_auth_mod, "cognito_service") as mock_cog:
        mock_cog.logout_user.side_effect = ClientError(
            {"Error": {"Code": "NotAuthorizedException", "Message": "Invalid token"}},
            "GlobalSignOut",
        )
        resp = await client.post("/api/auth/logout", json={
            "access_token": "invalid-token",
        })

    assert resp.status_code == 400
