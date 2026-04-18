"""Test par propriété — Formatage de la taille des fichiers (frontend).

# Feature: workflow-dossier-refactor, Property 8: File size formatting

**Validates: Requirements 7.2**

Propriété 8 : Pour toute taille de fichier non-négative (0 à 10 Go),
la fonction ``format_file_size`` (miroir Python du ``formatFileSize``
TypeScript dans ``api.ts``) retourne une chaîne contenant une valeur
numérique suivie d'une unité valide parmi {o, Ko, Mo, Go}. La valeur
numérique est cohérente avec l'entrée (round-trip à tolérance de
rounding près).
"""

import math
import re

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Python mirror of the frontend formatFileSize (local-site/web/frontend/
# src/lib/api.ts).
#
# Logic:
#   units = ["o", "Ko", "Mo", "Go"]
#   Iterate through non-terminal units; if value < 1024, format with
#   Number(value.toFixed(1)) and return.  For the terminal unit (Go),
#   always format.
#   Number(x.toFixed(1)) in JS drops trailing ".0" → we replicate that
#   by converting via float(f"{value:.1f}") then formatting the number.
# ---------------------------------------------------------------------------

UNITS = ("o", "Ko", "Mo", "Go")
NON_TERMINAL_UNITS = {"o", "Ko", "Mo"}
MAX_SIZE = 10 * 1024 * 1024 * 1024  # 10 Go

OUTPUT_PATTERN = re.compile(r"^(\d+(?:\.\d+)?)\s+(o|Ko|Mo|Go)$")

# Multiplier to convert a displayed value back to bytes for each unit.
UNIT_MULTIPLIER = {
    "o": 1,
    "Ko": 1024,
    "Mo": 1024 ** 2,
    "Go": 1024 ** 3,
}


def format_file_size(size_bytes: int) -> str:
    """Python mirror of the TypeScript ``formatFileSize`` from api.ts."""
    value = float(size_bytes)
    for i in range(len(UNITS) - 1):
        if value < 1024:
            formatted = float(f"{value:.1f}")
            # JS Number(x.toFixed(1)): 1024.0 → 1024, 1.5 → 1.5
            if formatted == int(formatted):
                return f"{int(formatted)} {UNITS[i]}"
            return f"{formatted} {UNITS[i]}"
        value /= 1024

    # Terminal unit: Go
    formatted = float(f"{value:.1f}")
    if formatted == int(formatted):
        return f"{int(formatted)} {UNITS[-1]}"
    return f"{formatted} {UNITS[-1]}"


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(size_bytes=st.integers(min_value=0, max_value=MAX_SIZE))
def test_format_file_size_valid_output(size_bytes: int) -> None:
    """Output matches regex pattern with valid unit."""
    result = format_file_size(size_bytes)
    match = OUTPUT_PATTERN.match(result)

    assert match is not None, f"Format invalide : {result!r}"

    unit = match.group(2)
    assert unit in UNIT_MULTIPLIER, f"Unité inconnue : {unit!r}"


@settings(max_examples=100, deadline=None)
@given(size_bytes=st.integers(min_value=0, max_value=MAX_SIZE))
def test_format_file_size_non_negative_value(size_bytes: int) -> None:
    """The numeric value in the output is always >= 0."""
    result = format_file_size(size_bytes)
    match = OUTPUT_PATTERN.match(result)
    assert match is not None
    value = float(match.group(1))
    assert value >= 0, f"Valeur négative : {value}"


@settings(max_examples=100, deadline=None)
@given(size_bytes=st.integers(min_value=0, max_value=MAX_SIZE))
def test_format_file_size_value_below_1024_for_non_terminal(
    size_bytes: int,
) -> None:
    """For non-terminal units (o, Ko, Mo), the numeric value is < 1024."""
    result = format_file_size(size_bytes)
    match = OUTPUT_PATTERN.match(result)
    assert match is not None

    value = float(match.group(1))
    unit = match.group(2)

    if unit in NON_TERMINAL_UNITS:
        assert value < 1024, (
            f"Valeur {value} >= 1024 pour l'unité non terminale {unit!r}"
        )


@settings(max_examples=100, deadline=None)
@given(size_bytes=st.integers(min_value=0, max_value=MAX_SIZE))
def test_format_file_size_round_trip(size_bytes: int) -> None:
    """Converting the displayed value back to bytes yields a value within
    rounding tolerance of the original."""
    result = format_file_size(size_bytes)
    match = OUTPUT_PATTERN.match(result)
    assert match is not None

    value = float(match.group(1))
    unit = match.group(2)
    reconstructed = value * UNIT_MULTIPLIER[unit]

    # Tolerance: the display uses 1 decimal, so rounding error is at most
    # 0.05 * unit_multiplier.  We add 1 to handle the "o" unit edge
    # (integer display).
    tolerance = 0.05 * UNIT_MULTIPLIER[unit] + 1
    assert math.isclose(reconstructed, size_bytes, abs_tol=tolerance), (
        f"Round-trip échoué : {size_bytes} → {result!r} → {reconstructed} "
        f"(tolérance={tolerance})"
    )
