"""Property-based tests — Hardware Performance Tuning.

Feature: hardware-performance-tuning

Property-based tests validating correctness properties of the hardware
performance profile selection and related computations.
"""

import sys
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

# Add backend to path for imports
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "local-site"
        / "web"
        / "backend"
    ),
)

from services.hardware_service import (
    PROFILES,
    HardwareInfo,
    PerformanceProfile,
    ProfileSelector,
)
from services.llm_service import compute_step_duration


# ---------------------------------------------------------------------------
# Feature: hardware-performance-tuning, Property 1: Profile selection matches RAM thresholds
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(ram=st.floats(min_value=0.5, max_value=256.0))
def test_profile_selection_matches_ram_thresholds(ram: float) -> None:
    """For any positive RAM value (in GB), the ProfileSelector SHALL return
    the correct profile with matching ctx_max, model, and rag_chunks.

    - "high" when RAM >= 32
    - "medium" when 16 <= RAM < 32
    - "low" when 8 <= RAM < 16
    - "minimal" when RAM < 8

    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
    """
    hw = HardwareInfo(
        cpu_model="Test CPU",
        cpu_freq_ghz=2.5,
        cpu_cores=8,
        ram_total_gb=ram,
        gpu_name=None,
        gpu_vram_gb=None,
    )
    selector = ProfileSelector()
    profile = selector.select(hw)

    if ram >= 32.0:
        assert profile.name == "high"
        assert profile.ctx_max == 8192
        assert profile.model == "mistral:7b-instruct-v0.3-q4_0"
        assert profile.rag_chunks == 6
    elif ram >= 16.0:
        assert profile.name == "medium"
        assert profile.ctx_max == 6144
        assert profile.model == "mistral:7b-instruct-v0.3-q4_0"
        assert profile.rag_chunks == 4
    elif ram >= 8.0:
        assert profile.name == "low"
        assert profile.ctx_max == 4096
        assert profile.model == "mistral:7b-instruct-v0.3-q4_0"
        assert profile.rag_chunks == 3
    else:
        assert profile.name == "minimal"
        assert profile.ctx_max == 2048
        assert profile.model == "mistral:7b-instruct-v0.3-q4_0"
        assert profile.rag_chunks == 2


# ---------------------------------------------------------------------------
# Feature: hardware-performance-tuning, Property 2: Tokens per second formula
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    cores=st.integers(min_value=1, max_value=64),
    freq=st.floats(min_value=0.5, max_value=6.0),
)
def test_tokens_per_sec_formula(cores: int, freq: float) -> None:
    """For any valid CPU configuration (cores > 0, frequency > 0), the
    computed tokens_per_sec SHALL equal 8.0 × (cores × frequency_ghz) / 16.

    **Validates: Requirements 2.6**
    """
    hw = HardwareInfo(
        cpu_model="Test CPU",
        cpu_freq_ghz=freq,
        cpu_cores=cores,
        ram_total_gb=16.0,
        gpu_name=None,
        gpu_vram_gb=None,
    )
    selector = ProfileSelector()
    result = selector.compute_tokens_per_sec(hw)
    expected = 8.0 * (cores * freq) / 16.0
    assert abs(result - expected) < 1e-9


# ---------------------------------------------------------------------------
# Feature: hardware-performance-tuning, Property 3: RAM warning consistency
# ---------------------------------------------------------------------------


# Minimum RAM requirements per profile (in GB)
_MIN_RAM: dict[str, float] = {
    "high": 32.0,
    "medium": 16.0,
    "low": 8.0,
    "minimal": 0.0,
}


@settings(max_examples=100)
@given(
    ram=st.floats(min_value=1.0, max_value=128.0),
    profile_name=st.sampled_from(list(PROFILES.keys())),
)
def test_ram_warning_consistency(ram: float, profile_name: str) -> None:
    """For any combination of detected RAM and selected profile, if the
    profile's minimum RAM requirement exceeds the detected RAM, the system
    SHALL flag the selection as potentially unstable (warning = True).
    If the detected RAM meets or exceeds the requirement, no warning SHALL
    be raised.

    **Validates: Requirements 5.5**
    """
    hw = HardwareInfo(
        cpu_model="Test CPU",
        cpu_freq_ghz=2.5,
        cpu_cores=8,
        ram_total_gb=ram,
        gpu_name=None,
        gpu_vram_gb=None,
    )
    profile = PROFILES[profile_name]
    selector = ProfileSelector()
    warning = selector.check_ram_warning(hw, profile)

    if ram < _MIN_RAM[profile_name]:
        assert warning is True, (
            f"Expected warning=True for profile '{profile_name}' "
            f"(min RAM={_MIN_RAM[profile_name]} GB) with detected RAM={ram} GB"
        )
    else:
        assert warning is False, (
            f"Expected warning=False for profile '{profile_name}' "
            f"(min RAM={_MIN_RAM[profile_name]} GB) with detected RAM={ram} GB"
        )


# Feature: hardware-performance-tuning, Property 4: Step duration estimate formula
"""Test par propriété — Formule d'estimation de durée par step.

**Validates: Requirements 6.2**

Propriété 4 : Pour toute valeur positive de estimated_input_tokens,
output_ratio (> 0), et tokens_per_sec (> 0), la durée estimée d'un step
en secondes DOIT être égale à :
    (estimated_input_tokens × output_ratio) / tokens_per_sec
"""


@settings(max_examples=100)
@given(
    tokens=st.integers(min_value=100, max_value=50000),
    ratio=st.floats(min_value=0.1, max_value=3.0),
    tps=st.floats(min_value=1.0, max_value=50.0),
)
def test_step_duration_formula(tokens: int, ratio: float, tps: float) -> None:
    """Pour tout triplet (tokens, ratio, tps) valide, la durée suit la formule."""
    expected = (tokens * ratio) / tps
    result = compute_step_duration(tokens, ratio, tps)
    assert abs(result - expected) < 1e-9
