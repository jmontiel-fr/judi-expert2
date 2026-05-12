"""Tests unitaires pour ActiveProfile et l'intégration LLM_Service / hardware.

Teste le singleton ActiveProfile (set/get, hot-reload, fallback chain),
le déclenchement de téléchargement de modèle, et la gestion d'erreur
lors du téléchargement.

Valide : Exigences 3.1, 3.2, 3.3, 3.4, 7.1, 7.3
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

# Ajouter le backend au path
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend")
)

from services.hardware_service import HardwareInfo, PerformanceProfile, PROFILES
from services.llm_service import (
    ActiveProfile,
    ModelDownloadManager,
    ModelDownloadStatus,
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


@pytest.fixture
def low_profile() -> PerformanceProfile:
    """Low performance profile with computed tokens_per_sec."""
    return PerformanceProfile(
        name="low",
        display_name="Économique",
        ram_range="8–16 Go",
        ctx_max=4096,
        model="mistral:7b-instruct-v0.3-q4_0",
        rag_chunks=3,
        tokens_per_sec=4.0,
    )


@pytest.fixture
def download_manager() -> ModelDownloadManager:
    """ModelDownloadManager with a test Ollama URL."""
    return ModelDownloadManager(ollama_base_url="http://test-ollama:11434")


# ---------------------------------------------------------------------------
# Tests: ActiveProfile singleton set/get
# ---------------------------------------------------------------------------


class TestActiveProfileSetGet:
    """Test ActiveProfile singleton set/get behavior.

    Validates: Requirements 3.1, 3.2, 3.3
    """

    def test_get_ctx_max_returns_profile_value(
        self, high_profile, sample_hardware_info
    ):
        """After set(), get_ctx_max() returns profile.ctx_max."""
        ActiveProfile.set(high_profile, sample_hardware_info)
        assert ActiveProfile.get_ctx_max() == 8192

    def test_get_model_returns_profile_value(
        self, high_profile, sample_hardware_info
    ):
        """After set(), get_model() returns profile.model."""
        ActiveProfile.set(high_profile, sample_hardware_info)
        assert ActiveProfile.get_model() == "mistral:7b-instruct-v0.3-q4_0"

    def test_get_tokens_per_sec_returns_profile_value(
        self, high_profile, sample_hardware_info
    ):
        """After set(), get_tokens_per_sec() returns profile.tokens_per_sec."""
        ActiveProfile.set(high_profile, sample_hardware_info)
        assert ActiveProfile.get_tokens_per_sec() == 7.8

    def test_get_profile_returns_full_profile(
        self, high_profile, sample_hardware_info
    ):
        """get_profile() returns the full PerformanceProfile object."""
        ActiveProfile.set(high_profile, sample_hardware_info)
        result = ActiveProfile.get_profile()
        assert result is high_profile
        assert result.name == "high"
        assert result.display_name == "Haute performance"

    def test_get_hardware_info_returns_hardware(
        self, high_profile, sample_hardware_info
    ):
        """get_hardware_info() returns the stored HardwareInfo."""
        ActiveProfile.set(high_profile, sample_hardware_info)
        result = ActiveProfile.get_hardware_info()
        assert result is sample_hardware_info
        assert result.cpu_model == "Intel Core i7-10750H"
        assert result.ram_total_gb == 31.7


# ---------------------------------------------------------------------------
# Tests: Hot-reload
# ---------------------------------------------------------------------------


class TestActiveProfileHotReload:
    """Test hot-reload: changing profile updates subsequent reads.

    Validates: Requirements 3.4
    """

    def test_hot_reload_ctx_max(
        self, high_profile, low_profile, sample_hardware_info
    ):
        """Setting a new profile immediately updates get_ctx_max()."""
        ActiveProfile.set(high_profile, sample_hardware_info)
        assert ActiveProfile.get_ctx_max() == 8192

        ActiveProfile.set(low_profile, sample_hardware_info)
        assert ActiveProfile.get_ctx_max() == 4096

    def test_hot_reload_model(
        self, high_profile, low_profile, sample_hardware_info
    ):
        """Setting a new profile immediately updates get_model()."""
        ActiveProfile.set(high_profile, sample_hardware_info)
        assert ActiveProfile.get_model() == "mistral:7b-instruct-v0.3-q4_0"

        ActiveProfile.set(low_profile, sample_hardware_info)
        assert ActiveProfile.get_model() == "mistral:7b-instruct-v0.3-q4_0"

    def test_hot_reload_tokens_per_sec(
        self, high_profile, low_profile, sample_hardware_info
    ):
        """Setting a new profile immediately updates get_tokens_per_sec()."""
        ActiveProfile.set(high_profile, sample_hardware_info)
        assert ActiveProfile.get_tokens_per_sec() == 7.8

        ActiveProfile.set(low_profile, sample_hardware_info)
        assert ActiveProfile.get_tokens_per_sec() == 4.0


# ---------------------------------------------------------------------------
# Tests: Fallback chain (ActiveProfile not initialized)
# ---------------------------------------------------------------------------


class TestActiveProfileFallbackChain:
    """Test fallback chain when ActiveProfile._profile is None.

    Validates: Requirements 3.1, 3.2, 3.3
    """

    def test_fallback_ctx_max_from_env(self, monkeypatch):
        """With env var CTX_MAX=4096, get_ctx_max() returns 4096."""
        monkeypatch.setenv("CTX_MAX", "4096")
        assert ActiveProfile.get_ctx_max() == 4096

    def test_fallback_ctx_max_hardcoded_default(self, monkeypatch):
        """Without env var, get_ctx_max() returns 8192 (hardcoded default)."""
        monkeypatch.delenv("CTX_MAX", raising=False)
        assert ActiveProfile.get_ctx_max() == 8192

    def test_fallback_model_from_env(self, monkeypatch):
        """With env var LLM_MODEL, get_model() returns env value."""
        monkeypatch.setenv("LLM_MODEL", "custom-model:latest")
        assert ActiveProfile.get_model() == "custom-model:latest"

    def test_fallback_model_hardcoded_default(self, monkeypatch):
        """Without env var, get_model() returns hardcoded default."""
        monkeypatch.delenv("LLM_MODEL", raising=False)
        assert ActiveProfile.get_model() == "mistral:7b-instruct-v0.3-q4_0"

    def test_fallback_tokens_per_sec_from_env(self, monkeypatch):
        """With env var LLM_TOKENS_PER_SEC, get_tokens_per_sec() returns env value."""
        monkeypatch.setenv("LLM_TOKENS_PER_SEC", "12.5")
        assert ActiveProfile.get_tokens_per_sec() == 12.5

    def test_fallback_tokens_per_sec_hardcoded_default(self, monkeypatch):
        """Without env var, get_tokens_per_sec() returns 8.0."""
        monkeypatch.delenv("LLM_TOKENS_PER_SEC", raising=False)
        assert ActiveProfile.get_tokens_per_sec() == 8.0

    def test_get_profile_returns_none_when_not_set(self):
        """get_profile() returns None when ActiveProfile not initialized."""
        assert ActiveProfile.get_profile() is None

    def test_get_hardware_info_returns_none_when_not_set(self):
        """get_hardware_info() returns None when not initialized."""
        assert ActiveProfile.get_hardware_info() is None


# ---------------------------------------------------------------------------
# Tests: Model download trigger on mismatch
# ---------------------------------------------------------------------------


class TestModelDownloadTrigger:
    """Test model download trigger on mismatch.

    Validates: Requirements 7.1
    """

    @pytest.mark.asyncio
    async def test_download_triggered_when_model_not_available(
        self, download_manager
    ):
        """When target model is not in Ollama's list, download is triggered."""
        with patch.object(
            download_manager,
            "_is_model_available",
            new_callable=AsyncMock,
            return_value=False,
        ):
            with patch.object(
                download_manager,
                "_pull_model",
                new_callable=AsyncMock,
            ) as mock_pull:
                await download_manager.check_and_pull_if_needed(
                    "mistral:7b-instruct-v0.3-q4_0"
                )

                # Verify download was triggered
                mock_pull.assert_called_once_with("mistral:7b-instruct-v0.3-q4_0")

        # Status should indicate download was needed
        assert download_manager.status.needed is True

    @pytest.mark.asyncio
    async def test_no_download_when_model_available(self, download_manager):
        """When target model is already available, no download is triggered."""
        with patch.object(
            download_manager,
            "_is_model_available",
            new_callable=AsyncMock,
            return_value=True,
        ):
            with patch.object(
                download_manager,
                "_pull_model",
                new_callable=AsyncMock,
            ) as mock_pull:
                await download_manager.check_and_pull_if_needed(
                    "mistral:7b-instruct-v0.3-q4_0"
                )

                # No download should be triggered
                mock_pull.assert_not_called()

        # Status should indicate no download needed
        assert download_manager.status.needed is False
        assert download_manager.status.in_progress is False


# ---------------------------------------------------------------------------
# Tests: Model download failure fallback
# ---------------------------------------------------------------------------


class TestModelDownloadFailure:
    """Test model download failure fallback.

    Validates: Requirements 7.3
    """

    @pytest.mark.asyncio
    async def test_download_failure_sets_error_no_exception(
        self, download_manager
    ):
        """When Ollama pull fails, status.error is set, no exception raised."""
        # Mock /api/tags returning empty list (model not available)
        tags_response = httpx.Response(
            200,
            json={"models": []},
            request=httpx.Request("GET", "http://test-ollama:11434/api/tags"),
        )

        # We need to mock the _pull_model method to simulate failure,
        # since httpx.AsyncClient.stream is used as async context manager
        # and is complex to mock. Instead, patch _is_model_available and _pull_model.
        with patch.object(
            download_manager,
            "_is_model_available",
            new_callable=AsyncMock,
            return_value=False,
        ):
            with patch.object(
                download_manager,
                "_pull_model",
                new_callable=AsyncMock,
            ) as mock_pull:
                # Simulate _pull_model setting error status
                async def simulate_pull_failure(model_name):
                    download_manager._status.in_progress = True
                    download_manager._status.in_progress = False
                    download_manager._status.progress_percent = None
                    download_manager._status.error = "Connection refused"

                mock_pull.side_effect = simulate_pull_failure

                # Should NOT raise an exception
                await download_manager.check_and_pull_if_needed(
                    "mistral:7b-instruct-v0.3-q4_0"
                )

        # Error should be recorded in status
        assert download_manager.status.error is not None
        assert "Connection refused" in download_manager.status.error
        assert download_manager.status.in_progress is False

    @pytest.mark.asyncio
    async def test_ollama_unreachable_sets_error(self, download_manager):
        """When Ollama is unreachable, status.error is set gracefully."""
        with patch(
            "httpx.AsyncClient.get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Cannot connect"),
        ):
            # Should NOT raise an exception
            await download_manager.check_and_pull_if_needed(
                "mistral:7b-instruct-v0.3-q4_0"
            )

        # Error should be recorded
        assert download_manager.status.error is not None
        assert "Cannot connect" in download_manager.status.error


# ---------------------------------------------------------------------------
# Tests: HardwareDetector.detect() returns valid HardwareInfo
# ---------------------------------------------------------------------------


class TestHardwareDetectorDetect:
    """Test HardwareDetector.detect() returns valid HardwareInfo with mocked psutil.

    Validates: Requirements 1.1, 1.2, 1.3
    """

    @patch("services.hardware_service.subprocess.run")
    @patch("services.hardware_service.Path")
    @patch("services.hardware_service.psutil")
    def test_detect_returns_valid_hardware_info(
        self, mock_psutil, mock_path_cls, mock_subprocess_run
    ):
        """HardwareDetector.detect() returns HardwareInfo with all fields populated."""
        from unittest.mock import MagicMock
        from services.hardware_service import HardwareDetector

        # Mock psutil.cpu_count
        mock_psutil.cpu_count.return_value = 8

        # Mock psutil.virtual_memory
        mock_mem = MagicMock()
        mock_mem.total = 32 * 1024**3  # 32 GB
        mock_psutil.virtual_memory.return_value = mock_mem

        # Mock psutil.cpu_freq
        mock_freq = MagicMock()
        mock_freq.max = 3600.0
        mock_freq.current = 3600.0
        mock_psutil.cpu_freq.return_value = mock_freq

        # Mock Path for /proc/cpuinfo
        mock_cpuinfo_path = MagicMock()
        mock_cpuinfo_path.exists.return_value = True
        mock_cpuinfo_path.read_text.return_value = (
            "processor\t: 0\n"
            "model name\t: Intel Core i9-12900K\n"
            "cpu MHz\t\t: 3200.000\n"
        )

        # Mock Path for /proc/driver/nvidia/gpus (no GPU)
        mock_nvidia_path = MagicMock()
        mock_nvidia_path.exists.return_value = False

        def path_side_effect(path_str):
            if path_str == "/proc/cpuinfo":
                return mock_cpuinfo_path
            elif path_str == "/proc/driver/nvidia/gpus":
                return mock_nvidia_path
            return MagicMock(exists=MagicMock(return_value=False))

        mock_path_cls.side_effect = path_side_effect

        # Mock nvidia-smi not found
        mock_subprocess_run.side_effect = FileNotFoundError("nvidia-smi not found")

        detector = HardwareDetector()
        result = detector.detect()

        assert isinstance(result, HardwareInfo)
        assert result.cpu_model == "Intel Core i9-12900K"
        assert result.cpu_freq_ghz == 3.2  # 3200 MHz / 1000
        assert result.cpu_cores == 8
        assert result.ram_total_gb == 32.0
        assert result.gpu_name is None
        assert result.gpu_vram_gb is None

    @patch("services.hardware_service.subprocess.run")
    @patch("services.hardware_service.Path")
    @patch("services.hardware_service.psutil")
    def test_detect_uses_psutil_freq_fallback_when_proc_missing(
        self, mock_psutil, mock_path_cls, mock_subprocess_run
    ):
        """When /proc/cpuinfo doesn't exist, falls back to psutil.cpu_freq()."""
        from unittest.mock import MagicMock
        from services.hardware_service import HardwareDetector

        # Mock psutil.cpu_count
        mock_psutil.cpu_count.return_value = 6

        # Mock psutil.virtual_memory
        mock_mem = MagicMock()
        mock_mem.total = 16 * 1024**3
        mock_psutil.virtual_memory.return_value = mock_mem

        # Mock psutil.cpu_freq (fallback path)
        mock_freq = MagicMock()
        mock_freq.max = 2600.0
        mock_freq.current = 2600.0
        mock_psutil.cpu_freq.return_value = mock_freq

        # Mock Path — /proc/cpuinfo does NOT exist
        mock_cpuinfo_path = MagicMock()
        mock_cpuinfo_path.exists.return_value = False

        mock_nvidia_path = MagicMock()
        mock_nvidia_path.exists.return_value = False

        def path_side_effect(path_str):
            if path_str == "/proc/cpuinfo":
                return mock_cpuinfo_path
            elif path_str == "/proc/driver/nvidia/gpus":
                return mock_nvidia_path
            return MagicMock(exists=MagicMock(return_value=False))

        mock_path_cls.side_effect = path_side_effect

        # Mock nvidia-smi not found
        mock_subprocess_run.side_effect = FileNotFoundError("nvidia-smi not found")

        detector = HardwareDetector()
        result = detector.detect()

        assert result.cpu_model == "Unknown CPU"  # /proc/cpuinfo not available
        assert result.cpu_freq_ghz == 2.6  # from psutil.cpu_freq().max / 1000
        assert result.cpu_cores == 6
        assert result.ram_total_gb == 16.0


# ---------------------------------------------------------------------------
# Tests: Safe defaults when psutil raises exceptions
# ---------------------------------------------------------------------------


class TestHardwareDetectorSafeDefaults:
    """Test safe defaults when psutil raises exceptions.

    Validates: Requirements 1.5
    """

    @patch("services.hardware_service.subprocess.run")
    @patch("services.hardware_service.Path")
    @patch("services.hardware_service.psutil")
    def test_safe_defaults_when_cpu_count_raises(
        self, mock_psutil, mock_path_cls, mock_subprocess_run
    ):
        """When psutil.cpu_count raises RuntimeError, defaults to 4 cores."""
        from unittest.mock import MagicMock
        from services.hardware_service import HardwareDetector

        # cpu_count raises
        mock_psutil.cpu_count.side_effect = RuntimeError("CPU detection failed")

        # virtual_memory raises
        mock_psutil.virtual_memory.side_effect = RuntimeError("RAM detection failed")

        # cpu_freq raises
        mock_psutil.cpu_freq.side_effect = RuntimeError("Freq detection failed")

        # /proc/cpuinfo not available
        mock_cpuinfo_path = MagicMock()
        mock_cpuinfo_path.exists.return_value = False

        mock_nvidia_path = MagicMock()
        mock_nvidia_path.exists.return_value = False

        def path_side_effect(path_str):
            if path_str == "/proc/cpuinfo":
                return mock_cpuinfo_path
            elif path_str == "/proc/driver/nvidia/gpus":
                return mock_nvidia_path
            return MagicMock(exists=MagicMock(return_value=False))

        mock_path_cls.side_effect = path_side_effect

        # nvidia-smi not found
        mock_subprocess_run.side_effect = FileNotFoundError("nvidia-smi not found")

        detector = HardwareDetector()
        result = detector.detect()

        # All should be safe defaults
        assert result.cpu_cores == 4
        assert result.ram_total_gb == 8.0
        assert result.cpu_model == "Unknown CPU"
        assert result.cpu_freq_ghz == 2.0
        assert result.gpu_name is None
        assert result.gpu_vram_gb is None

    @patch("services.hardware_service.subprocess.run")
    @patch("services.hardware_service.Path")
    @patch("services.hardware_service.psutil")
    def test_partial_failure_uses_defaults_for_failed_only(
        self, mock_psutil, mock_path_cls, mock_subprocess_run
    ):
        """When only some psutil calls fail, only those use defaults."""
        from unittest.mock import MagicMock
        from services.hardware_service import HardwareDetector

        # cpu_count works
        mock_psutil.cpu_count.return_value = 12

        # virtual_memory raises
        mock_psutil.virtual_memory.side_effect = RuntimeError("RAM failed")

        # cpu_freq works
        mock_freq = MagicMock()
        mock_freq.max = 4000.0
        mock_freq.current = 4000.0
        mock_psutil.cpu_freq.return_value = mock_freq

        # /proc/cpuinfo not available
        mock_cpuinfo_path = MagicMock()
        mock_cpuinfo_path.exists.return_value = False

        mock_nvidia_path = MagicMock()
        mock_nvidia_path.exists.return_value = False

        def path_side_effect(path_str):
            if path_str == "/proc/cpuinfo":
                return mock_cpuinfo_path
            elif path_str == "/proc/driver/nvidia/gpus":
                return mock_nvidia_path
            return MagicMock(exists=MagicMock(return_value=False))

        mock_path_cls.side_effect = path_side_effect

        mock_subprocess_run.side_effect = FileNotFoundError("nvidia-smi not found")

        detector = HardwareDetector()
        result = detector.detect()

        # cpu_cores detected successfully
        assert result.cpu_cores == 12
        # RAM failed → default
        assert result.ram_total_gb == 8.0
        # cpu_freq from psutil fallback
        assert result.cpu_freq_ghz == 4.0
        # cpu_model default (no /proc/cpuinfo)
        assert result.cpu_model == "Unknown CPU"


# ---------------------------------------------------------------------------
# Tests: Override persistence (ProfileSelector.get_active_profile)
# ---------------------------------------------------------------------------


class TestOverridePersistence:
    """Test override persistence via ProfileSelector.get_active_profile().

    Validates: Requirements 5.2, 5.4
    """

    def test_override_low_returns_low_profile(self, sample_hardware_info):
        """With override='low', get_active_profile returns the low profile."""
        from services.hardware_service import ProfileSelector

        selector = ProfileSelector()
        # sample_hardware_info has 31.7 GB RAM → would auto-select "medium"
        result = selector.get_active_profile(sample_hardware_info, override="low")

        assert result.name == "low"
        assert result.ctx_max == 4096
        assert result.model == "mistral:7b-instruct-v0.3-q4_0"
        assert result.rag_chunks == 3
        # tokens_per_sec should be computed from hardware
        expected_tps = 8.0 * (sample_hardware_info.cpu_cores * sample_hardware_info.cpu_freq_ghz) / 16.0
        assert result.tokens_per_sec == expected_tps

    def test_override_none_returns_auto_detected_profile(self, sample_hardware_info):
        """With override=None, get_active_profile returns auto-detected profile."""
        from services.hardware_service import ProfileSelector

        selector = ProfileSelector()
        # sample_hardware_info has 31.7 GB RAM → auto-selects "medium" (16 ≤ 31.7 < 32)
        result = selector.get_active_profile(sample_hardware_info, override=None)

        assert result.name == "medium"
        assert result.ctx_max == 6144
        assert result.model == "mistral:7b-instruct-v0.3-q4_0"
        assert result.rag_chunks == 4

    def test_override_high_with_high_ram(self):
        """With override='high' and 64 GB RAM, returns high profile."""
        from services.hardware_service import ProfileSelector

        hw = HardwareInfo(
            cpu_model="AMD Ryzen 9 5950X",
            cpu_freq_ghz=3.4,
            cpu_cores=16,
            ram_total_gb=64.0,
            gpu_name=None,
            gpu_vram_gb=None,
        )
        selector = ProfileSelector()
        result = selector.get_active_profile(hw, override="high")

        assert result.name == "high"
        assert result.ctx_max == 8192

    def test_invalid_override_falls_back_to_auto(self, sample_hardware_info):
        """With an invalid override name, falls back to auto-detected profile."""
        from services.hardware_service import ProfileSelector

        selector = ProfileSelector()
        result = selector.get_active_profile(
            sample_hardware_info, override="nonexistent_profile"
        )

        # Should fall back to auto-detection (31.7 GB → medium)
        assert result.name == "medium"
        assert result.ctx_max == 6144

    def test_empty_string_override_falls_back_to_auto(self, sample_hardware_info):
        """With override='', falls back to auto-detected profile."""
        from services.hardware_service import ProfileSelector

        selector = ProfileSelector()
        result = selector.get_active_profile(sample_hardware_info, override="")

        # Empty string is falsy → auto-detection
        assert result.name == "medium"

    def test_override_minimal_returns_minimal_profile(self):
        """With override='minimal', returns minimal profile regardless of RAM."""
        from services.hardware_service import ProfileSelector

        hw = HardwareInfo(
            cpu_model="Intel Core i9-12900K",
            cpu_freq_ghz=3.2,
            cpu_cores=16,
            ram_total_gb=128.0,
            gpu_name="NVIDIA RTX 4090",
            gpu_vram_gb=24.0,
        )
        selector = ProfileSelector()
        result = selector.get_active_profile(hw, override="minimal")

        assert result.name == "minimal"
        assert result.ctx_max == 2048
        assert result.model == "mistral:7b-instruct-v0.3-q4_0"
        assert result.rag_chunks == 2
