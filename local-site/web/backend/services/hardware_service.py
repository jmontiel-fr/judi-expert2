"""Hardware detection and performance profile selection service.

This module provides dataclasses for hardware information and performance
profiles, along with the predefined PROFILES dictionary mapping hardware
capabilities to LLM parameters.
"""

import logging
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path

import psutil

logger = logging.getLogger(__name__)


@dataclass
class HardwareInfo:
    """Detected hardware information from the host machine.

    Attributes:
        cpu_model: CPU model name, e.g. "Intel Core i7-10750H".
        cpu_freq_ghz: CPU base frequency in GHz, e.g. 2.6.
        cpu_cores: Number of physical CPU cores, e.g. 6.
        ram_total_gb: Total available RAM in gigabytes, e.g. 31.7.
        gpu_name: GPU model name if detected, None otherwise.
        gpu_vram_gb: GPU VRAM in gigabytes if detected, None otherwise.
    """

    cpu_model: str
    cpu_freq_ghz: float
    cpu_cores: int
    ram_total_gb: float
    gpu_name: str | None
    gpu_vram_gb: float | None


@dataclass
class PerformanceProfile:
    """LLM performance profile tied to a hardware capability tier.

    Attributes:
        name: Profile identifier ("high", "medium", "low", "minimal").
        display_name: Human-readable name shown in the UI.
        ram_range: RAM range description for this tier.
        ctx_max: Maximum context window size in tokens.
        model: Ollama model identifier to use.
        rag_chunks: Number of RAG chunks to retrieve per query.
        tokens_per_sec: Estimated token generation speed (computed at runtime).
    """

    name: str
    display_name: str
    ram_range: str
    ctx_max: int
    model: str
    rag_chunks: int
    tokens_per_sec: float


PROFILES: dict[str, PerformanceProfile] = {
    "high": PerformanceProfile(
        name="high",
        display_name="Haute performance",
        ram_range="≥ 32 Go",
        ctx_max=8192,
        model="mistral:7b-instruct-v0.3-q4_0",
        rag_chunks=6,
        tokens_per_sec=0.0,
    ),
    "medium": PerformanceProfile(
        name="medium",
        display_name="Standard",
        ram_range="16–32 Go",
        ctx_max=6144,
        model="mistral:7b-instruct-v0.3-q4_0",
        rag_chunks=4,
        tokens_per_sec=0.0,
    ),
    "low": PerformanceProfile(
        name="low",
        display_name="Économique",
        ram_range="8–16 Go",
        ctx_max=4096,
        model="mistral:7b-instruct-v0.3-q4_0",
        rag_chunks=3,
        tokens_per_sec=0.0,
    ),
    "minimal": PerformanceProfile(
        name="minimal",
        display_name="Minimal",
        ram_range="< 8 Go",
        ctx_max=2048,
        model="mistral:7b-instruct-v0.3-q4_0",
        rag_chunks=2,
        tokens_per_sec=0.0,
    ),
}


class HardwareDetector:
    """Detects hardware capabilities of the host machine.

    Uses psutil for CPU cores and RAM, /proc/cpuinfo for CPU model and
    frequency, and nvidia-smi or /proc for GPU detection. Falls back to
    safe defaults when detection fails.
    """

    # Safe default values used when detection fails.
    _DEFAULT_CPU_MODEL = "Unknown CPU"
    _DEFAULT_CPU_FREQ_GHZ = 2.0
    _DEFAULT_CPU_CORES = 4
    _DEFAULT_RAM_TOTAL_GB = 8.0

    def detect(self) -> HardwareInfo:
        """Collect hardware info from the host machine.

        Uses safe defaults on failure for each attribute independently,
        ensuring partial failures don't prevent overall detection.

        Returns:
            HardwareInfo with detected or default values.
        """
        cpu_model = self._detect_cpu_model()
        cpu_freq_ghz = self._detect_cpu_freq_ghz()
        cpu_cores = self._detect_cpu_cores()
        ram_total_gb = self._detect_ram_total_gb()
        gpu_name, gpu_vram_gb = self._detect_gpu()

        return HardwareInfo(
            cpu_model=cpu_model,
            cpu_freq_ghz=cpu_freq_ghz,
            cpu_cores=cpu_cores,
            ram_total_gb=ram_total_gb,
            gpu_name=gpu_name,
            gpu_vram_gb=gpu_vram_gb,
        )

    def _detect_cpu_model(self) -> str:
        """Detect CPU model name from /proc/cpuinfo.

        Returns:
            CPU model string or default "Unknown CPU" on failure.
        """
        try:
            cpuinfo_path = Path("/proc/cpuinfo")
            if cpuinfo_path.exists():
                content = cpuinfo_path.read_text(encoding="utf-8")
                for line in content.splitlines():
                    if line.startswith("model name"):
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            return parts[1].strip()
            # Fallback: use psutil cpu_freq as indicator that we can't get model
            logger.warning(
                "CPU model not found in /proc/cpuinfo, using default."
            )
            return self._DEFAULT_CPU_MODEL
        except Exception as e:
            logger.warning("Failed to detect CPU model: %s", e)
            return self._DEFAULT_CPU_MODEL

    def _detect_cpu_freq_ghz(self) -> float:
        """Detect CPU base frequency in GHz from /proc/cpuinfo.

        Falls back to psutil.cpu_freq() if /proc/cpuinfo doesn't have
        the frequency information.

        Returns:
            CPU frequency in GHz or default 2.0 on failure.
        """
        try:
            # Try /proc/cpuinfo first
            cpuinfo_path = Path("/proc/cpuinfo")
            if cpuinfo_path.exists():
                content = cpuinfo_path.read_text(encoding="utf-8")
                for line in content.splitlines():
                    if line.startswith("cpu MHz"):
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            mhz = float(parts[1].strip())
                            return round(mhz / 1000.0, 2)

            # Fallback: psutil.cpu_freq()
            freq = psutil.cpu_freq()
            if freq and freq.max > 0:
                return round(freq.max / 1000.0, 2)
            if freq and freq.current > 0:
                return round(freq.current / 1000.0, 2)

            logger.warning(
                "CPU frequency not detected, using default %.1f GHz.",
                self._DEFAULT_CPU_FREQ_GHZ,
            )
            return self._DEFAULT_CPU_FREQ_GHZ
        except Exception as e:
            logger.warning("Failed to detect CPU frequency: %s", e)
            return self._DEFAULT_CPU_FREQ_GHZ

    def _detect_cpu_cores(self) -> int:
        """Detect number of physical CPU cores using psutil.

        Returns:
            Number of physical cores or default 4 on failure.
        """
        try:
            cores = psutil.cpu_count(logical=False)
            if cores and cores > 0:
                return cores
            logger.warning(
                "CPU core count returned None/0, using default %d.",
                self._DEFAULT_CPU_CORES,
            )
            return self._DEFAULT_CPU_CORES
        except Exception as e:
            logger.warning("Failed to detect CPU cores: %s", e)
            return self._DEFAULT_CPU_CORES

    def _detect_ram_total_gb(self) -> float:
        """Detect total RAM in gigabytes using psutil.

        Returns:
            Total RAM in GB or default 8.0 on failure.
        """
        try:
            mem = psutil.virtual_memory()
            ram_gb = round(mem.total / (1024**3), 1)
            if ram_gb > 0:
                return ram_gb
            logger.warning(
                "RAM detection returned 0, using default %.1f GB.",
                self._DEFAULT_RAM_TOTAL_GB,
            )
            return self._DEFAULT_RAM_TOTAL_GB
        except Exception as e:
            logger.warning("Failed to detect RAM: %s", e)
            return self._DEFAULT_RAM_TOTAL_GB

    def _detect_gpu(self) -> tuple[str | None, float | None]:
        """Detect GPU name and VRAM using /proc or nvidia-smi.

        Tries /proc/driver/nvidia/gpus/*/information first, then falls
        back to nvidia-smi CLI. Returns (None, None) if no GPU detected.

        Returns:
            Tuple of (gpu_name, gpu_vram_gb) or (None, None).
        """
        # Try /proc/driver/nvidia/gpus/*/information
        gpu_info = self._detect_gpu_from_proc()
        if gpu_info[0] is not None:
            return gpu_info

        # Fallback: nvidia-smi
        gpu_info = self._detect_gpu_from_nvidia_smi()
        if gpu_info[0] is not None:
            return gpu_info

        logger.info("No GPU detected. Running in CPU-only mode.")
        return None, None

    def _detect_gpu_from_proc(self) -> tuple[str | None, float | None]:
        """Attempt GPU detection via /proc/driver/nvidia/gpus/.

        Returns:
            Tuple of (gpu_name, gpu_vram_gb) or (None, None).
        """
        try:
            nvidia_gpu_path = Path("/proc/driver/nvidia/gpus")
            if not nvidia_gpu_path.exists():
                return None, None

            for gpu_dir in nvidia_gpu_path.iterdir():
                info_file = gpu_dir / "information"
                if info_file.exists():
                    content = info_file.read_text(encoding="utf-8")
                    gpu_name = None
                    for line in content.splitlines():
                        if line.startswith("Model:"):
                            gpu_name = line.split(":", 1)[1].strip()
                            break
                    if gpu_name:
                        # VRAM not always available in /proc, try nvidia-smi
                        vram = self._get_vram_from_nvidia_smi()
                        return gpu_name, vram
            return None, None
        except Exception as e:
            logger.warning("Failed to read GPU info from /proc: %s", e)
            return None, None

    def _detect_gpu_from_nvidia_smi(self) -> tuple[str | None, float | None]:
        """Attempt GPU detection via nvidia-smi command.

        Returns:
            Tuple of (gpu_name, gpu_vram_gb) or (None, None).
        """
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                line = result.stdout.strip().splitlines()[0]
                parts = line.split(",")
                if len(parts) >= 2:
                    gpu_name = parts[0].strip()
                    vram_mb = float(parts[1].strip())
                    vram_gb = round(vram_mb / 1024.0, 1)
                    return gpu_name, vram_gb
                elif len(parts) == 1:
                    return parts[0].strip(), None
            return None, None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None, None
        except Exception as e:
            logger.warning("Failed to run nvidia-smi: %s", e)
            return None, None

    def _get_vram_from_nvidia_smi(self) -> float | None:
        """Get GPU VRAM in GB from nvidia-smi.

        Returns:
            VRAM in GB or None if unavailable.
        """
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                vram_mb = float(result.stdout.strip().splitlines()[0])
                return round(vram_mb / 1024.0, 1)
            return None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        except Exception as e:
            logger.warning("Failed to get VRAM from nvidia-smi: %s", e)
            return None

# Minimum RAM requirements per profile (in GB)
_PROFILE_MIN_RAM: dict[str, float] = {
    "high": 32.0,
    "medium": 16.0,
    "low": 8.0,
    "minimal": 0.0,
}


class ProfileSelector:
    """Selects the appropriate performance profile based on hardware capabilities.

    Uses RAM thresholds to determine the best profile and computes
    estimated token generation speed from CPU characteristics.
    """

    def select(self, hw: HardwareInfo) -> PerformanceProfile:
        """Select a performance profile based on RAM thresholds.

        Determines the appropriate profile tier from detected RAM, computes
        the tokens_per_sec estimate, and returns a profile copy with the
        computed value filled in.

        Args:
            hw: Detected hardware information.

        Returns:
            A PerformanceProfile with tokens_per_sec computed from CPU specs.
        """
        if hw.ram_total_gb >= 32.0:
            profile = PROFILES["high"]
        elif hw.ram_total_gb >= 16.0:
            profile = PROFILES["medium"]
        elif hw.ram_total_gb >= 8.0:
            profile = PROFILES["low"]
        else:
            profile = PROFILES["minimal"]
            logger.warning(
                "RAM below 8 GB (%.1f GB detected). "
                "Selecting minimal profile — expect degraded performance.",
                hw.ram_total_gb,
            )

        tokens_per_sec = self.compute_tokens_per_sec(hw)
        return replace(profile, tokens_per_sec=tokens_per_sec)

    def compute_tokens_per_sec(self, hw: HardwareInfo) -> float:
        """Compute estimated token generation speed from CPU specs.

        Formula: 8.0 × (cores × freq_ghz) / 16

        Args:
            hw: Detected hardware information.

        Returns:
            Estimated tokens per second as a float.
        """
        return 8.0 * (hw.cpu_cores * hw.cpu_freq_ghz) / 16.0

    def get_active_profile(
        self, hw: HardwareInfo, override: str | None
    ) -> PerformanceProfile:
        """Return the active profile, respecting a manual override if set.

        If an override profile name is provided and valid, returns that
        profile (with tokens_per_sec computed from hw). Otherwise falls
        back to automatic selection via ``select()``.

        Args:
            hw: Detected hardware information.
            override: Profile name override from DB, or None for auto.

        Returns:
            The active PerformanceProfile with tokens_per_sec filled in.
        """
        if override and override in PROFILES:
            profile = PROFILES[override]
            tokens_per_sec = self.compute_tokens_per_sec(hw)
            return replace(profile, tokens_per_sec=tokens_per_sec)

        return self.select(hw)

    def check_ram_warning(
        self, hw: HardwareInfo, profile: PerformanceProfile
    ) -> bool:
        """Check if a profile is over-provisioned for the detected RAM.

        Returns True (warning) when the profile's minimum RAM requirement
        exceeds the detected RAM, indicating potential instability.

        Args:
            hw: Detected hardware information.
            profile: The performance profile to check against.

        Returns:
            True if detected RAM is below the profile's minimum requirement.
        """
        min_ram = _PROFILE_MIN_RAM.get(profile.name, 0.0)
        return hw.ram_total_gb < min_ram
