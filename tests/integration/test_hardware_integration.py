"""Tests d'intégration — Hardware Performance Tuning.

Teste les flux complets :
- Startup flow: detect → persist → profile active → LLM uses profile CTX_MAX
- Override applies to LLM calls (new model/ctx_max used after override)
- Hardware info persisted to DB after startup

Valide : Exigences 1.4, 3.1, 3.4, 5.2
"""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Backend sur le path
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend")
)

from models import Base, LocalConfig
from database import get_db
from main import app
from routers.auth import get_current_user
from services.hardware_service import (
    HardwareDetector,
    HardwareInfo,
    PerformanceProfile,
    ProfileSelector,
    PROFILES,
)
from services.llm_service import ActiveProfile, compute_num_ctx

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Mock hardware info (deterministic, avoids platform-specific behavior)
# ---------------------------------------------------------------------------

MOCK_HARDWARE_INFO = HardwareInfo(
    cpu_model="Intel Core i7-10750H",
    cpu_freq_ghz=2.6,
    cpu_cores=6,
    ram_total_gb=31.7,
    gpu_name="NVIDIA GeForce RTX 3060",
    gpu_vram_gb=6.0,
)


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
    """In-memory SQLite engine for test isolation."""
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def seed_local_config(session_factory):
    """Insert a LocalConfig row for tests that need it."""
    async with session_factory() as session:
        config = LocalConfig(
            password_hash="fake_hash",
            domaine="psychologie",
            is_configured=True,
            rag_version="1.0.0",
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)
        return config


async def _run_startup_lifespan(session_factory):
    """Simulate the lifespan startup logic with mocked hardware detection.

    This replicates the logic in main.py lifespan:
    1. Detect hardware (mocked)
    2. Read override from DB
    3. Select profile
    4. Store hardware JSON in DB
    5. Apply profile to ActiveProfile singleton
    """
    hardware_info = MOCK_HARDWARE_INFO

    # Read override from DB
    override: str | None = None
    async with session_factory() as session:
        result = await session.execute(select(LocalConfig).limit(1))
        local_config = result.scalar_one_or_none()
        if local_config:
            override = local_config.performance_profile_override

    # Select profile
    selector = ProfileSelector()
    active_profile = selector.get_active_profile(hardware_info, override)

    # Store hardware info in DB
    hardware_json = json.dumps({
        "cpu_model": hardware_info.cpu_model,
        "cpu_freq_ghz": hardware_info.cpu_freq_ghz,
        "cpu_cores": hardware_info.cpu_cores,
        "ram_total_gb": hardware_info.ram_total_gb,
        "gpu_name": hardware_info.gpu_name,
        "gpu_vram_gb": hardware_info.gpu_vram_gb,
    })
    async with session_factory() as session:
        result = await session.execute(select(LocalConfig).limit(1))
        config_row = result.scalar_one_or_none()
        if config_row:
            config_row.detected_hardware_json = hardware_json
            session.add(config_row)
            await session.commit()

    # Apply profile to ActiveProfile singleton
    ActiveProfile.set(active_profile, hardware_info)


@pytest_asyncio.fixture
async def client_with_startup(session_factory, seed_local_config):
    """AsyncClient with full startup flow executed (lifespan simulated).

    Runs the startup logic (detect → persist → profile active) then
    provides an HTTP client for API calls.
    """
    # Run the startup lifespan logic
    await _run_startup_lifespan(session_factory)

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    async def _override_auth():
        return {"sub": "local_admin", "domaine": "psychologie"}

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_auth

    # Mock model download manager to avoid network calls
    with patch(
        "routers.config._download_manager.check_and_pull_if_needed",
        new_callable=AsyncMock,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 1: Full startup flow integration
# ---------------------------------------------------------------------------


class TestFullStartupFlow:
    """Test full lifespan: detect → persist → profile active → LLM uses profile.

    Validates: Requirements 1.4, 3.1
    """

    @pytest.mark.asyncio
    async def test_startup_sets_active_profile(
        self, client_with_startup: AsyncClient
    ):
        """After startup, ActiveProfile is populated with detected hardware."""
        profile = ActiveProfile.get_profile()
        assert profile is not None, "ActiveProfile should be set after startup"

        hw = ActiveProfile.get_hardware_info()
        assert hw is not None, "HardwareInfo should be set after startup"

    @pytest.mark.asyncio
    async def test_startup_profile_has_valid_ctx_max(
        self, client_with_startup: AsyncClient
    ):
        """After startup, CTX_MAX is one of the valid profile values."""
        ctx_max = ActiveProfile.get_ctx_max()
        valid_ctx_values = {2048, 4096, 6144, 8192}
        assert ctx_max in valid_ctx_values, (
            f"CTX_MAX should be one of {valid_ctx_values}, got {ctx_max}"
        )

    @pytest.mark.asyncio
    async def test_startup_profile_has_valid_model(
        self, client_with_startup: AsyncClient
    ):
        """After startup, model is one of the valid model names."""
        model = ActiveProfile.get_model()
        valid_models = {
            "qwen2.5:7b-instruct-q3_K_M",
            "qwen2.5:3b-instruct-q3_K_M",
        }
        assert model in valid_models, (
            f"Model should be one of {valid_models}, got {model}"
        )

    @pytest.mark.asyncio
    async def test_startup_selects_correct_profile_for_ram(
        self, client_with_startup: AsyncClient
    ):
        """With 31.7 GB RAM, the auto-detected profile should be 'medium'."""
        # 31.7 GB is >= 16 but < 32, so "medium" profile
        profile = ActiveProfile.get_profile()
        assert profile is not None
        assert profile.name == "medium"
        assert profile.ctx_max == 6144
        assert profile.model == "qwen2.5:7b-instruct-q3_K_M"

    @pytest.mark.asyncio
    async def test_startup_hardware_info_matches_mock(
        self, client_with_startup: AsyncClient
    ):
        """After startup, stored HardwareInfo matches the mocked values."""
        hw = ActiveProfile.get_hardware_info()
        assert hw is not None
        assert hw.cpu_model == "Intel Core i7-10750H"
        assert hw.cpu_freq_ghz == 2.6
        assert hw.cpu_cores == 6
        assert hw.ram_total_gb == 31.7
        assert hw.gpu_name == "NVIDIA GeForce RTX 3060"
        assert hw.gpu_vram_gb == 6.0

    @pytest.mark.asyncio
    async def test_llm_service_uses_active_profile_ctx_max(
        self, client_with_startup: AsyncClient
    ):
        """LLM compute_num_ctx respects the active profile's CTX_MAX ceiling."""
        # With medium profile, CTX_MAX = 6144
        # A very large input should be capped at 6144
        large_text = "x" * 100_000  # ~28571 tokens estimated
        num_ctx = compute_num_ctx(large_text)
        assert num_ctx <= 6144, (
            f"compute_num_ctx should be capped at profile CTX_MAX (6144), got {num_ctx}"
        )


# ---------------------------------------------------------------------------
# Test 2: Override applies to LLM calls
# ---------------------------------------------------------------------------


class TestOverrideAppliesToLLM:
    """Test that override changes are reflected in LLM service parameters.

    Validates: Requirements 3.4, 5.2
    """

    @pytest.mark.asyncio
    async def test_override_minimal_changes_ctx_max(
        self, client_with_startup: AsyncClient
    ):
        """After override to 'minimal', CTX_MAX becomes 2048."""
        resp = await client_with_startup.put(
            "/api/config/performance-profile/override",
            json={"profile_name": "minimal"},
        )
        assert resp.status_code == 200

        assert ActiveProfile.get_ctx_max() == 2048

    @pytest.mark.asyncio
    async def test_override_minimal_changes_model(
        self, client_with_startup: AsyncClient
    ):
        """After override to 'minimal', model becomes qwen2.5:3b-instruct-q3_K_M."""
        resp = await client_with_startup.put(
            "/api/config/performance-profile/override",
            json={"profile_name": "minimal"},
        )
        assert resp.status_code == 200

        assert ActiveProfile.get_model() == "qwen2.5:3b-instruct-q3_K_M"

    @pytest.mark.asyncio
    async def test_override_then_revert_restores_auto(
        self, client_with_startup: AsyncClient
    ):
        """After override then revert (null), profile returns to auto-detected."""
        # Override to minimal
        resp = await client_with_startup.put(
            "/api/config/performance-profile/override",
            json={"profile_name": "minimal"},
        )
        assert resp.status_code == 200
        assert ActiveProfile.get_ctx_max() == 2048

        # Revert to auto
        resp = await client_with_startup.put(
            "/api/config/performance-profile/override",
            json={"profile_name": None},
        )
        assert resp.status_code == 200

        # 31.7 GB RAM → medium profile → ctx_max 6144
        assert ActiveProfile.get_ctx_max() == 6144
        assert ActiveProfile.get_model() == "qwen2.5:7b-instruct-q3_K_M"

    @pytest.mark.asyncio
    async def test_override_affects_compute_num_ctx(
        self, client_with_startup: AsyncClient
    ):
        """After override to 'low', compute_num_ctx is capped at 4096."""
        resp = await client_with_startup.put(
            "/api/config/performance-profile/override",
            json={"profile_name": "low"},
        )
        assert resp.status_code == 200

        # With low profile, ctx_max = 4096
        # A very large input should be capped at 4096
        # (CTX_MIN is also 4096, so the result is exactly 4096)
        large_text = "x" * 100_000
        num_ctx = compute_num_ctx(large_text)
        assert num_ctx <= 4096, (
            f"After override to low, compute_num_ctx should cap at 4096, got {num_ctx}"
        )

    @pytest.mark.asyncio
    async def test_override_high_profile_applies(
        self, client_with_startup: AsyncClient
    ):
        """After override to 'high', CTX_MAX becomes 8192 and model is 7b."""
        resp = await client_with_startup.put(
            "/api/config/performance-profile/override",
            json={"profile_name": "high"},
        )
        assert resp.status_code == 200

        assert ActiveProfile.get_ctx_max() == 8192
        assert ActiveProfile.get_model() == "qwen2.5:7b-instruct-q3_K_M"


# ---------------------------------------------------------------------------
# Test 3: Hardware info persisted to DB
# ---------------------------------------------------------------------------


class TestHardwarePersistence:
    """Test that hardware info is persisted to the database after startup.

    Validates: Requirements 1.4, 5.2
    """

    @pytest.mark.asyncio
    async def test_hardware_json_persisted_to_db(
        self, client_with_startup: AsyncClient, session_factory
    ):
        """After startup, detected_hardware_json is stored in local_config."""
        async with session_factory() as session:
            result = await session.execute(select(LocalConfig).limit(1))
            config = result.scalar_one_or_none()

        assert config is not None
        assert config.detected_hardware_json is not None

    @pytest.mark.asyncio
    async def test_hardware_json_is_valid_json(
        self, client_with_startup: AsyncClient, session_factory
    ):
        """The persisted hardware JSON is valid and parseable."""
        async with session_factory() as session:
            result = await session.execute(select(LocalConfig).limit(1))
            config = result.scalar_one_or_none()

        assert config is not None
        assert config.detected_hardware_json is not None

        hw_data = json.loads(config.detected_hardware_json)
        assert isinstance(hw_data, dict)

    @pytest.mark.asyncio
    async def test_hardware_json_has_expected_keys(
        self, client_with_startup: AsyncClient, session_factory
    ):
        """The persisted hardware JSON contains all expected keys."""
        async with session_factory() as session:
            result = await session.execute(select(LocalConfig).limit(1))
            config = result.scalar_one_or_none()

        assert config is not None
        hw_data = json.loads(config.detected_hardware_json)

        expected_keys = {"cpu_model", "cpu_freq_ghz", "cpu_cores", "ram_total_gb"}
        assert expected_keys.issubset(hw_data.keys()), (
            f"Hardware JSON should contain {expected_keys}, got keys: {set(hw_data.keys())}"
        )

    @pytest.mark.asyncio
    async def test_hardware_json_values_match_detection(
        self, client_with_startup: AsyncClient, session_factory
    ):
        """The persisted hardware JSON values match the detected hardware."""
        async with session_factory() as session:
            result = await session.execute(select(LocalConfig).limit(1))
            config = result.scalar_one_or_none()

        assert config is not None
        hw_data = json.loads(config.detected_hardware_json)

        assert hw_data["cpu_model"] == "Intel Core i7-10750H"
        assert hw_data["cpu_freq_ghz"] == 2.6
        assert hw_data["cpu_cores"] == 6
        assert hw_data["ram_total_gb"] == 31.7
        assert hw_data["gpu_name"] == "NVIDIA GeForce RTX 3060"
        assert hw_data["gpu_vram_gb"] == 6.0
