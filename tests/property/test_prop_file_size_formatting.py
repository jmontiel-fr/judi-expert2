"""Test par propriété — Formatage de la taille des fichiers.

# Feature: step-files-management, Property 1: File size formatting produces valid human-readable output

**Validates: Requirements 1.2**

Propriété 1 : Pour toute taille de fichier non-négative (0 à 10 Go),
``format_file_size`` retourne une chaîne contenant une valeur numérique
suivie d'une unité valide parmi {o, Ko, Mo, Go}. La valeur numérique
est strictement inférieure à 1024 pour les unités non terminales.
"""

import re
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# Ajouter le backend au path pour les imports
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "local-site"
        / "web"
        / "backend"
    ),
)

from services.file_service import FileService

VALID_UNITS = {"o", "Ko", "Mo", "Go"}
NON_TERMINAL_UNITS = {"o", "Ko", "Mo"}
MAX_SIZE = 10 * 1024 * 1024 * 1024  # 10 Go

# Regex : nombre (entier ou décimal) suivi d'un espace et d'une unité
OUTPUT_PATTERN = re.compile(r"^(\d+(?:\.\d+)?)\s+(o|Ko|Mo|Go)$")

service = FileService()


@settings(max_examples=100, deadline=None)
@given(size_bytes=st.integers(min_value=0, max_value=MAX_SIZE))
def test_format_file_size_valid_output(size_bytes: int) -> None:
    """Le résultat contient une valeur numérique et une unité valide."""
    result = service.format_file_size(size_bytes)
    match = OUTPUT_PATTERN.match(result)

    assert match is not None, f"Format invalide : {result!r}"

    value = float(match.group(1))
    unit = match.group(2)

    assert unit in VALID_UNITS, f"Unité inconnue : {unit!r}"

    # Pour les unités non terminales, la valeur doit être < 1024
    if unit in NON_TERMINAL_UNITS:
        assert value < 1024, (
            f"Valeur {value} >= 1024 pour l'unité non terminale {unit!r}"
        )

    # La valeur doit être >= 0
    assert value >= 0, f"Valeur négative : {value}"


@settings(max_examples=100, deadline=None)
@given(size_bytes=st.integers(min_value=0, max_value=MAX_SIZE))
def test_format_file_size_non_negative_value(size_bytes: int) -> None:
    """La valeur numérique dans le résultat est toujours >= 0."""
    result = service.format_file_size(size_bytes)
    match = OUTPUT_PATTERN.match(result)
    assert match is not None
    assert float(match.group(1)) >= 0


def test_format_file_size_zero() -> None:
    """0 octets donne '0 o'."""
    assert service.format_file_size(0) == "0 o"


def test_format_file_size_boundary_1024() -> None:
    """1024 octets donne '1 Ko'."""
    assert service.format_file_size(1024) == "1 Ko"


def test_format_file_size_boundary_1_mo() -> None:
    """1 048 576 octets donne '1 Mo'."""
    assert service.format_file_size(1024 * 1024) == "1 Mo"


def test_format_file_size_boundary_1_go() -> None:
    """1 073 741 824 octets donne '1 Go'."""
    assert service.format_file_size(1024 * 1024 * 1024) == "1 Go"
