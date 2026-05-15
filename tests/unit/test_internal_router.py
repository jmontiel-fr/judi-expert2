"""Tests unitaires pour le router internal (cron subscription-check).

Teste l'endpoint POST /api/internal/cron/subscription-check protégé par
le header X-Cron-Token.

Exigences validées : 5.1, 5.2, 5.3, 5.5
"""

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

_saved_modules = {}
for prefix in _modules_to_isolate:
    for k in list(sys.modules):
        if k == prefix or k.startswith(prefix + "."):
            _saved_modules[k] = sys.modules.pop(k)

_saved_path = sys.path[:]
sys.path.insert(0, _central_backend)

from models import Base as _Base  # noqa: E402
from database import get_db as _get_db  # noqa: E402
from main import app as _app  # noqa: E402

import routers.internal as _internal_mod  # noqa: E402

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

_TEST_CRON_TOKEN = "test-secret-cron-token-12345"


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
# Tests — Authentication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cron_no_token_returns_401(client: AsyncClient):
    """POST sans header X-Cron-Token retourne 401."""
    with patch.object(_internal_mod, "CRON_TOKEN", _TEST_CRON_TOKEN):
        resp = await client.post("/api/internal/cron/subscription-check")

    assert resp.status_code == 401
    assert "invalide" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cron_invalid_token_returns_401(client: AsyncClient):
    """POST avec un token invalide retourne 401."""
    with patch.object(_internal_mod, "CRON_TOKEN", _TEST_CRON_TOKEN):
        resp = await client.post(
            "/api/internal/cron/subscription-check",
            headers={"X-Cron-Token": "wrong-token"},
        )

    assert resp.status_code == 401
    assert "invalide" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cron_empty_env_token_returns_401(client: AsyncClient):
    """POST retourne 401 si CRON_TOKEN n'est pas configuré (vide)."""
    with patch.object(_internal_mod, "CRON_TOKEN", ""):
        resp = await client.post(
            "/api/internal/cron/subscription-check",
            headers={"X-Cron-Token": "some-token"},
        )

    assert resp.status_code == 401
    assert "non configuré" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests — Successful execution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cron_valid_token_returns_200(client: AsyncClient):
    """POST avec un token valide appelle process_payment_failures et retourne 200."""
    mock_result = {"processed": 3, "emails_sent": 2, "blocked": 1}

    with (
        patch.object(_internal_mod, "CRON_TOKEN", _TEST_CRON_TOKEN),
        patch.object(
            _internal_mod.subscription_service,
            "process_payment_failures",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_process,
    ):
        resp = await client.post(
            "/api/internal/cron/subscription-check",
            headers={"X-Cron-Token": _TEST_CRON_TOKEN},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["processed"] == 3
    assert data["emails_sent"] == 2
    assert data["blocked"] == 1
    mock_process.assert_called_once()


@pytest.mark.asyncio
async def test_cron_no_failures_returns_zeros(client: AsyncClient):
    """POST retourne des compteurs à zéro quand aucun abonnement en échec."""
    mock_result = {"processed": 0, "emails_sent": 0, "blocked": 0}

    with (
        patch.object(_internal_mod, "CRON_TOKEN", _TEST_CRON_TOKEN),
        patch.object(
            _internal_mod.subscription_service,
            "process_payment_failures",
            new_callable=AsyncMock,
            return_value=mock_result,
        ),
    ):
        resp = await client.post(
            "/api/internal/cron/subscription-check",
            headers={"X-Cron-Token": _TEST_CRON_TOKEN},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["processed"] == 0
    assert data["emails_sent"] == 0
    assert data["blocked"] == 0
