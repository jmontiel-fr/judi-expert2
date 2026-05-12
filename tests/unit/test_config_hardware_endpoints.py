"""Tests unitaires pour les endpoints hardware performance du router config.

Teste les endpoints :
- GET /api/config/hardware-info
- GET /api/config/performance-profile
- PUT /api/config/performance-profile/override
- GET /api/config/model-download-status

Valide : Exigences 3.5, 4.1, 4.2, 5.1, 5.2, 5.4
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Backend sur le path
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend")
)

from models import Base, LocalConfig
from database import get_db
from main import app
from routers.auth import get_current_user
from services.hardware_service import HardwareInfo, PerformanceProfile, PROFILES
from services.llm_service import ActiveProfile


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_active_profile():
    """Reset ActiveProfile singleton state between tests."""
    ActiveProfile._profile = None
    ActiveProfile._hardware_info = None
    yield
    ActiveProfile._profile = None
    ActiveProfile._hardware_info = None


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


@pytest.fixture
def sample_hardware_info() -> HardwareInfo:
    """Sample hardware info for testing."""
    return HardwareInfo(
        cpu_model="Intel Core i7-10750H",
        cpu_freq_ghz=2.6,
        cpu_cores=6,
        ram_total_gb=31.7,
        gpu_name="NVIDIA GeForce RTX 3060",
        gpu_vram_gb=6.0,
    )


@pytest.fixture
def high_profile() -> PerformanceProfile:
    """High performance profile with computed tokens_per_sec."""
    return PerformanceProfile(
        name="high",
        display_name="Haute performance",
        ram_range="≥ 32 Go",
        ctx_max=8192,
        model="mistral:7b-instruct-v0.3-q4_0",
        rag_chunks=6,
        tokens_per_sec=7.8,
    )


async def _seed_local_config(sf):
    """Helper: insert a LocalConfig row directly into the in-memory DB."""
    async with sf() as session:
        config = LocalConfig(
            password_hash="fake_hash",
            domaine="psychologie",
            is_configured=True,
            rag_version="1.0.0",
        )
        session.add(config)
        await session.commit()


# ---------------------------------------------------------------------------
# Tests: GET /api/config/hardware-info
# ---------------------------------------------------------------------------


class TestGetHardwareInfo:
    """Test GET /hardware-info endpoint.

    Validates: Requirements 3.5, 4.1
    """

    @pytest.mark.asyncio
    async def test_get_hardware_info_response_shape(
        self, client: AsyncClient, sample_hardware_info, high_profile
    ):
        """GET /hardware-info returns correct schema with all fields."""
        ActiveProfile.set(high_profile, sample_hardware_info)

        resp = await client.get("/api/config/hardware-info")
        assert resp.status_code == 200

        data = resp.json()
        assert data["cpu_model"] == "Intel Core i7-10750H"
        assert data["cpu_freq_ghz"] == 2.6
        assert data["cpu_cores"] == 6
        assert data["ram_total_gb"] == 31.7
        assert data["gpu_name"] == "NVIDIA GeForce RTX 3060"
        assert data["gpu_vram_gb"] == 6.0

    @pytest.mark.asyncio
    async def test_get_hardware_info_no_gpu(
        self, client: AsyncClient, high_profile
    ):
        """GET /hardware-info returns null for GPU fields when no GPU."""
        hw_no_gpu = HardwareInfo(
            cpu_model="AMD Ryzen 5 3600",
            cpu_freq_ghz=3.6,
            cpu_cores=6,
            ram_total_gb=16.0,
            gpu_name=None,
            gpu_vram_gb=None,
        )
        ActiveProfile.set(high_profile, hw_no_gpu)

        resp = await client.get("/api/config/hardware-info")
        assert resp.status_code == 200

        data = resp.json()
        assert data["gpu_name"] is None
        assert data["gpu_vram_gb"] is None

    @pytest.mark.asyncio
    async def test_get_hardware_info_503_when_not_detected(
        self, client: AsyncClient
    ):
        """GET /hardware-info returns 503 when hardware not yet detected."""
        # ActiveProfile not initialized (reset by fixture)
        resp = await client.get("/api/config/hardware-info")
        assert resp.status_code == 503
        assert "not yet detected" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Tests: GET /api/config/performance-profile
# ---------------------------------------------------------------------------


class TestGetPerformanceProfile:
    """Test GET /performance-profile endpoint.

    Validates: Requirements 3.5, 4.1, 4.2
    """

    @pytest.mark.asyncio
    async def test_get_performance_profile_returns_all_profiles(
        self, client: AsyncClient, session_factory, sample_hardware_info, high_profile
    ):
        """GET /performance-profile returns all 4 profiles with active highlighted."""
        await _seed_local_config(session_factory)
        ActiveProfile.set(high_profile, sample_hardware_info)

        resp = await client.get("/api/config/performance-profile")
        assert resp.status_code == 200

        data = resp.json()
        # Check top-level structure
        assert "active_profile" in data
        assert "is_override" in data
        assert "auto_detected_profile" in data
        assert "all_profiles" in data
        assert "hardware_info" in data

        # All 4 profiles present
        assert len(data["all_profiles"]) == 4
        profile_names = [p["name"] for p in data["all_profiles"]]
        assert "high" in profile_names
        assert "medium" in profile_names
        assert "low" in profile_names
        assert "minimal" in profile_names

        # Each profile has required fields
        for p in data["all_profiles"]:
            assert "name" in p
            assert "display_name" in p
            assert "ram_range" in p
            assert "ctx_max" in p
            assert "model" in p
            assert "rag_chunks" in p
            assert "tokens_per_sec" in p
            assert "step_durations" in p

    @pytest.mark.asyncio
    async def test_get_performance_profile_active_profile_details(
        self, client: AsyncClient, session_factory, sample_hardware_info, high_profile
    ):
        """GET /performance-profile returns correct active profile details."""
        await _seed_local_config(session_factory)
        ActiveProfile.set(high_profile, sample_hardware_info)

        resp = await client.get("/api/config/performance-profile")
        assert resp.status_code == 200

        data = resp.json()
        active = data["active_profile"]
        assert active["name"] == "high"
        assert active["display_name"] == "Haute performance"
        assert active["ctx_max"] == 8192
        assert active["model"] == "mistral:7b-instruct-v0.3-q4_0"
        assert active["rag_chunks"] == 6

    @pytest.mark.asyncio
    async def test_get_performance_profile_is_override_false(
        self, client: AsyncClient, session_factory, sample_hardware_info, high_profile
    ):
        """GET /performance-profile shows is_override=false when no override set."""
        await _seed_local_config(session_factory)
        ActiveProfile.set(high_profile, sample_hardware_info)

        resp = await client.get("/api/config/performance-profile")
        assert resp.status_code == 200

        data = resp.json()
        assert data["is_override"] is False

    @pytest.mark.asyncio
    async def test_get_performance_profile_hardware_info_included(
        self, client: AsyncClient, session_factory, sample_hardware_info, high_profile
    ):
        """GET /performance-profile includes hardware_info in response."""
        await _seed_local_config(session_factory)
        ActiveProfile.set(high_profile, sample_hardware_info)

        resp = await client.get("/api/config/performance-profile")
        assert resp.status_code == 200

        hw = resp.json()["hardware_info"]
        assert hw["cpu_model"] == "Intel Core i7-10750H"
        assert hw["cpu_freq_ghz"] == 2.6
        assert hw["cpu_cores"] == 6
        assert hw["ram_total_gb"] == 31.7

    @pytest.mark.asyncio
    async def test_get_performance_profile_503_when_not_initialized(
        self, client: AsyncClient
    ):
        """GET /performance-profile returns 503 when not initialized."""
        resp = await client.get("/api/config/performance-profile")
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Tests: PUT /api/config/performance-profile/override
# ---------------------------------------------------------------------------


class TestPutOverride:
    """Test PUT /performance-profile/override endpoint.

    Validates: Requirements 5.1, 5.2, 5.4
    """

    @pytest.mark.asyncio
    async def test_put_override_with_valid_profile(
        self, client: AsyncClient, session_factory, sample_hardware_info, high_profile
    ):
        """PUT /override with valid profile name applies it."""
        await _seed_local_config(session_factory)
        ActiveProfile.set(high_profile, sample_hardware_info)

        with patch(
            "routers.config._download_manager.check_and_pull_if_needed",
            new_callable=AsyncMock,
        ):
            resp = await client.put(
                "/api/config/performance-profile/override",
                json={"profile_name": "low"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["active_profile"] == "low"

        # Verify ActiveProfile was updated
        assert ActiveProfile.get_ctx_max() == 4096
        assert ActiveProfile.get_model() == "mistral:7b-instruct-v0.3-q4_0"

    @pytest.mark.asyncio
    async def test_put_override_with_null_reverts_to_auto(
        self, client: AsyncClient, session_factory, sample_hardware_info, high_profile
    ):
        """PUT /override with null reverts to auto-detected profile."""
        await _seed_local_config(session_factory)
        ActiveProfile.set(high_profile, sample_hardware_info)

        with patch(
            "routers.config._download_manager.check_and_pull_if_needed",
            new_callable=AsyncMock,
        ):
            # First set an override
            resp = await client.put(
                "/api/config/performance-profile/override",
                json={"profile_name": "minimal"},
            )
            assert resp.status_code == 200
            assert resp.json()["active_profile"] == "minimal"

            # Then revert to auto
            resp = await client.put(
                "/api/config/performance-profile/override",
                json={"profile_name": None},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        # 31.7 GB RAM → auto-detected is "medium"
        assert data["active_profile"] == "medium"

    @pytest.mark.asyncio
    async def test_put_override_with_invalid_name_returns_400(
        self, client: AsyncClient, session_factory, sample_hardware_info, high_profile
    ):
        """PUT /override with invalid profile name returns 400."""
        await _seed_local_config(session_factory)
        ActiveProfile.set(high_profile, sample_hardware_info)

        resp = await client.put(
            "/api/config/performance-profile/override",
            json={"profile_name": "nonexistent"},
        )

        assert resp.status_code == 400
        assert "Profil inconnu" in resp.json()["detail"]
        assert "nonexistent" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_put_override_triggers_model_download(
        self, client: AsyncClient, session_factory, sample_hardware_info, high_profile
    ):
        """PUT /override triggers model download check."""
        await _seed_local_config(session_factory)
        ActiveProfile.set(high_profile, sample_hardware_info)

        with patch(
            "routers.config._download_manager.check_and_pull_if_needed",
            new_callable=AsyncMock,
        ) as mock_download:
            resp = await client.put(
                "/api/config/performance-profile/override",
                json={"profile_name": "low"},
            )

        assert resp.status_code == 200
        # Model download should have been triggered with the low profile's model
        mock_download.assert_called_once_with("mistral:7b-instruct-v0.3-q4_0")

    @pytest.mark.asyncio
    async def test_put_override_persists_to_db(
        self, client: AsyncClient, session_factory, sample_hardware_info, high_profile
    ):
        """PUT /override persists the override to the database."""
        await _seed_local_config(session_factory)
        ActiveProfile.set(high_profile, sample_hardware_info)

        with patch(
            "routers.config._download_manager.check_and_pull_if_needed",
            new_callable=AsyncMock,
        ):
            resp = await client.put(
                "/api/config/performance-profile/override",
                json={"profile_name": "low"},
            )
        assert resp.status_code == 200

        # Verify DB persistence
        from sqlalchemy import select as sa_select

        async with session_factory() as session:
            result = await session.execute(sa_select(LocalConfig).limit(1))
            config = result.scalar_one()
            assert config.performance_profile_override == "low"

    @pytest.mark.asyncio
    async def test_put_override_null_clears_db(
        self, client: AsyncClient, session_factory, sample_hardware_info, high_profile
    ):
        """PUT /override with null clears the override in the database."""
        await _seed_local_config(session_factory)
        ActiveProfile.set(high_profile, sample_hardware_info)

        with patch(
            "routers.config._download_manager.check_and_pull_if_needed",
            new_callable=AsyncMock,
        ):
            # Set override first
            await client.put(
                "/api/config/performance-profile/override",
                json={"profile_name": "low"},
            )
            # Clear override
            await client.put(
                "/api/config/performance-profile/override",
                json={"profile_name": None},
            )

        # Verify DB cleared
        from sqlalchemy import select as sa_select

        async with session_factory() as session:
            result = await session.execute(sa_select(LocalConfig).limit(1))
            config = result.scalar_one()
            assert config.performance_profile_override is None


# ---------------------------------------------------------------------------
# Tests: GET /api/config/model-download-status
# ---------------------------------------------------------------------------


class TestGetModelDownloadStatus:
    """Test GET /model-download-status endpoint.

    Validates: Requirements 7.2, 7.4
    """

    @pytest.mark.asyncio
    async def test_get_model_download_status_idle(self, client: AsyncClient):
        """GET /model-download-status returns idle status when no download."""
        resp = await client.get("/api/config/model-download-status")
        assert resp.status_code == 200

        data = resp.json()
        assert "needed" in data
        assert "in_progress" in data
        assert "progress_percent" in data
        assert "error" in data
        assert data["in_progress"] is False
