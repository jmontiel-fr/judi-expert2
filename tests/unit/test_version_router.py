"""Tests unitaires pour les routers de version (local + central).

Valide : Exigences 2.1, 2.5, 3.4, 3.5, 5.3, 7.1, 10.1, 10.3, 11.4
"""

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# ===========================================================================
# Central-site module isolation
# ===========================================================================

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

from models import Base as _CentralBase  # noqa: E402
from models.expert import Expert as _Expert  # noqa: E402
from models.app_version import AppVersion as _AppVersion  # noqa: E402
from database import get_db as _central_get_db  # noqa: E402
from main import app as _central_app  # noqa: E402

import routers.profile as _profile_mod  # noqa: E402
import routers.admin as _admin_mod  # noqa: E402

# Cache central modules and restore original
_central_cache = {}
for prefix in _modules_to_isolate:
    for k in list(sys.modules):
        if k == prefix or k.startswith(prefix + "."):
            _central_cache[k] = sys.modules.pop(k)

sys.modules.update(_saved_modules)
sys.path[:] = _saved_path

# ===========================================================================
# Local-site module setup
# ===========================================================================

_local_backend = str(
    Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend"
)
sys.path.insert(0, _local_backend)

from services.site_central_client import SiteCentralClient, SiteCentralError  # noqa: E402

# ===========================================================================
# Constants
# ===========================================================================

ADMIN_EMAIL = "admin@judi-expert.fr"


# ===========================================================================
# Central-site fixtures
# ===========================================================================


@pytest_asyncio.fixture
async def central_engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(_CentralBase.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def central_session_factory(central_engine):
    return async_sessionmaker(central_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def seed_central_admin(central_session_factory):
    """Crée un expert admin en base centrale."""
    async with central_session_factory() as session:
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


def _fake_get_current_expert(expert):
    """Retourne une dépendance qui simule un expert authentifié."""
    async def _override():
        return (expert, "fake-access-token")
    return _override


@pytest_asyncio.fixture
async def central_admin_client(central_session_factory, seed_central_admin):
    """AsyncClient authentifié en tant qu'admin sur le Site Central."""
    async def _override_get_db():
        async with central_session_factory() as session:
            yield session

    _central_app.dependency_overrides[_central_get_db] = _override_get_db
    _central_app.dependency_overrides[_profile_mod.get_current_expert] = _fake_get_current_expert(seed_central_admin)

    transport = ASGITransport(app=_central_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _central_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def central_public_client(central_session_factory):
    """AsyncClient sans authentification sur le Site Central."""
    async def _override_get_db():
        async with central_session_factory() as session:
            yield session

    _central_app.dependency_overrides[_central_get_db] = _override_get_db

    transport = ASGITransport(app=_central_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _central_app.dependency_overrides.clear()


# ===========================================================================
# Tests — Central-site GET /api/version (Exigence 2.1)
# ===========================================================================


class TestCentralGetVersion:
    """Tests pour GET /api/version sur le Site Central."""

    @pytest.mark.asyncio
    async def test_returns_all_required_fields(
        self, central_admin_client: AsyncClient, central_session_factory
    ):
        """GET /api/version retourne latest_version, download_url, mandatory, release_notes."""
        # Seed a published version
        async with central_session_factory() as session:
            version = _AppVersion(
                version="1.2.0",
                download_url="https://downloads.judi-expert.fr/judi-expert-local-1.2.0.exe",
                mandatory=True,
                release_notes="Correction de bugs",
            )
            session.add(version)
            await session.commit()

        resp = await central_admin_client.get("/api/version")
        assert resp.status_code == 200
        data = resp.json()
        assert "latest_version" in data
        assert "download_url" in data
        assert "mandatory" in data
        assert "release_notes" in data
        assert data["latest_version"] == "1.2.0"
        assert data["mandatory"] is True

    @pytest.mark.asyncio
    async def test_returns_404_when_no_version_published(
        self, central_public_client: AsyncClient
    ):
        """GET /api/version retourne 404 si aucune version publiée."""
        resp = await central_public_client.get("/api/version")
        assert resp.status_code == 404


# ===========================================================================
# Tests — Central-site POST /api/admin/versions (Exigence 2.5)
# ===========================================================================


class TestCentralPostAdminVersions:
    """Tests pour POST /api/admin/versions sur le Site Central."""

    @pytest.mark.asyncio
    async def test_valid_semver_returns_201(self, central_admin_client: AsyncClient):
        """POST /api/admin/versions avec semver valide retourne 201."""
        resp = await central_admin_client.post("/api/admin/versions", json={
            "version": "2.0.0",
            "download_url": "https://downloads.judi-expert.fr/judi-expert-local-2.0.0.exe",
            "mandatory": True,
            "release_notes": "Nouvelle version majeure",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["version"] == "2.0.0"
        assert data["mandatory"] is True
        assert "id" in data
        assert "published_at" in data

    @pytest.mark.asyncio
    async def test_invalid_semver_returns_422(self, central_admin_client: AsyncClient):
        """POST /api/admin/versions avec semver invalide (ex: 'abc') retourne 422."""
        resp = await central_admin_client.post("/api/admin/versions", json={
            "version": "abc",
            "download_url": "https://downloads.judi-expert.fr/invalid.exe",
            "mandatory": True,
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_semver_partial_returns_422(self, central_admin_client: AsyncClient):
        """POST /api/admin/versions avec version partielle (ex: '1.2') retourne 422."""
        resp = await central_admin_client.post("/api/admin/versions", json={
            "version": "1.2",
            "download_url": "https://downloads.judi-expert.fr/invalid.exe",
            "mandatory": True,
        })
        assert resp.status_code == 422


# ===========================================================================
# Tests — Local-site GET /api/version (Exigences 3.4, 3.5, 5.3)
# ===========================================================================


class TestLocalGetVersion:
    """Tests pour GET /api/version sur l'Application Locale."""

    @pytest.mark.asyncio
    async def test_returns_required_fields(self):
        """GET /api/version retourne current_version, current_date, update_available."""
        with patch(
            "routers.version.read_version_file"
        ) as mock_read, patch(
            "routers.version.is_within_business_hours", return_value=False
        ):
            from services.version_reader import VersionInfo
            mock_read.return_value = VersionInfo(version="1.0.0", date="2026-01-15")

            # Import the local app
            from main import app as local_app
            transport = ASGITransport(app=local_app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/version")

            assert resp.status_code == 200
            data = resp.json()
            assert "current_version" in data
            assert "current_date" in data
            assert "update_available" in data
            assert data["current_version"] == "1.0.0"
            assert data["current_date"] == "2026-01-15"

    @pytest.mark.asyncio
    async def test_outside_business_hours_returns_no_update(self):
        """Hors heures ouvrables → update_available=false (Exigence 3.4)."""
        with patch(
            "routers.version.read_version_file"
        ) as mock_read, patch(
            "routers.version.is_within_business_hours", return_value=False
        ):
            from services.version_reader import VersionInfo
            mock_read.return_value = VersionInfo(version="1.0.0", date="2026-01-15")

            from main import app as local_app
            transport = ASGITransport(app=local_app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/version")

            assert resp.status_code == 200
            data = resp.json()
            assert data["update_available"] is False

    @pytest.mark.asyncio
    async def test_site_central_unreachable_returns_graceful_fallback(self):
        """Site Central injoignable → update_available=false (Exigence 3.5)."""
        with patch(
            "routers.version.read_version_file"
        ) as mock_read, patch(
            "routers.version.is_within_business_hours", return_value=True
        ), patch(
            "routers.version.SiteCentralClient"
        ) as mock_client_cls:
            from services.version_reader import VersionInfo
            mock_read.return_value = VersionInfo(version="1.0.0", date="2026-01-15")

            # Simulate SiteCentralClient raising SiteCentralError
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = SiteCentralError("Site Central indisponible")
            mock_client_cls.return_value = mock_instance

            from main import app as local_app
            transport = ASGITransport(app=local_app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/version")

            assert resp.status_code == 200
            data = resp.json()
            assert data["update_available"] is False

    @pytest.mark.asyncio
    async def test_newer_mandatory_version_returns_update_available(self):
        """Site Central retourne version plus récente avec mandatory=true → update_available=true."""
        with patch(
            "routers.version.read_version_file"
        ) as mock_read, patch(
            "routers.version.is_within_business_hours", return_value=True
        ), patch(
            "routers.version.SiteCentralClient"
        ) as mock_client_cls:
            from services.version_reader import VersionInfo
            mock_read.return_value = VersionInfo(version="1.0.0", date="2026-01-15")

            # Simulate Site Central returning a newer mandatory version
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "latest_version": "2.0.0",
                "download_url": "https://downloads.judi-expert.fr/judi-expert-local-2.0.0.exe",
                "mandatory": True,
                "release_notes": "Mise à jour critique",
            }
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_client_cls.return_value = mock_instance

            from main import app as local_app
            transport = ASGITransport(app=local_app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/version")

            assert resp.status_code == 200
            data = resp.json()
            assert data["update_available"] is True
            assert data["latest_version"] == "2.0.0"


# ===========================================================================
# Tests — Local-site GET /api/llm/update-status (Exigence 7.1)
# ===========================================================================


class TestLocalLlmUpdateStatus:
    """Tests pour GET /api/llm/update-status sur l'Application Locale."""

    @pytest.mark.asyncio
    async def test_returns_required_fields(self):
        """GET /api/llm/update-status retourne status, progress, current_model, error_message."""
        with patch(
            "routers.version.LlmUpdateService"
        ) as mock_service_cls:
            mock_instance = AsyncMock()
            mock_instance.get_update_status.return_value = {
                "status": "idle",
                "progress": 0,
                "current_model": "mistral:7b-instruct-v0.3-q4_0",
                "error_message": None,
            }
            mock_service_cls.return_value = mock_instance

            from main import app as local_app
            transport = ASGITransport(app=local_app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/llm/update-status")

            assert resp.status_code == 200
            data = resp.json()
            assert "status" in data
            assert "progress" in data
            assert "current_model" in data
            assert "error_message" in data
            assert data["status"] == "idle"
            assert data["progress"] == 0


# ===========================================================================
# Tests — Central-site GET /api/health (Exigence 11.4)
# ===========================================================================


class TestCentralHealthEndpoint:
    """Tests pour GET /api/health sur le Site Central."""

    @pytest.mark.asyncio
    async def test_health_includes_version_field(self, central_public_client: AsyncClient):
        """GET /api/health retourne un champ 'version'."""
        resp = await central_public_client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert "status" in data
        assert data["status"] == "ok"
        # Version should be a non-empty string
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0


# ===========================================================================
# Tests — Central-site GET /api/downloads/app (Exigences 10.1, 10.3)
# ===========================================================================


class TestCentralDownloadsApp:
    """Tests pour GET /api/downloads/app sur le Site Central."""

    @pytest.mark.asyncio
    async def test_uses_latest_published_version(
        self, central_public_client: AsyncClient, central_session_factory
    ):
        """GET /api/downloads/app utilise la dernière version publiée (Exigence 10.1)."""
        # Seed two versions — the latest should be used
        async with central_session_factory() as session:
            v1 = _AppVersion(
                version="1.0.0",
                download_url="https://downloads.judi-expert.fr/judi-expert-local-1.0.0.exe",
                mandatory=True,
                published_at=datetime(2026, 1, 1, 10, 0, 0),
            )
            v2 = _AppVersion(
                version="1.1.0",
                download_url="https://downloads.judi-expert.fr/judi-expert-local-1.1.0.exe",
                mandatory=True,
                published_at=datetime(2026, 2, 1, 10, 0, 0),
            )
            session.add_all([v1, v2])
            await session.commit()

        resp = await central_public_client.get("/api/downloads/app")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        # Should use the latest version (1.1.0)
        assert "1.1.0" in data["version"]

    @pytest.mark.asyncio
    async def test_falls_back_to_default_version_when_no_version_published(
        self, central_public_client: AsyncClient
    ):
        """GET /api/downloads/app retourne '0.1.0' si aucune version publiée (Exigence 10.3)."""
        resp = await central_public_client.get("/api/downloads/app")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert "1.0.0" in data["version"]
