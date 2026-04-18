"""Test par propriété — Mapping Content-Type des fichiers.

# Feature: step-files-management, Property 2: Content-Type mapping is correct for known extensions

**Validates: Requirements 3.3**

Propriété 2 : Pour tout nom de fichier avec une extension connue parmi
{.md, .pdf, .docx, .zip}, ``get_content_type`` retourne le type MIME
correspondant. Pour toute extension inconnue, il retourne
``application/octet-stream``.
"""

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

KNOWN_EXTENSIONS: dict[str, str] = {
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".docx": (
        "application/vnd.openxmlformats-officedocument"
        ".wordprocessingml.document"
    ),
    ".zip": "application/zip",
}

UNKNOWN_EXTENSIONS = [".txt", ".csv", ".jpg", ".png", ".html", ".xml", ".json", ".yaml"]

service = FileService()

# ---------------------------------------------------------------------------
# Stratégies Hypothesis
# ---------------------------------------------------------------------------

# Noms de fichiers valides (stem) : au moins 1 caractère alphanumérique
file_stems = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789_-"),
    min_size=1,
    max_size=50,
)

known_ext = st.sampled_from(list(KNOWN_EXTENSIONS.keys()))

unknown_ext = st.sampled_from(UNKNOWN_EXTENSIONS)


# ---------------------------------------------------------------------------
# Propriété 2 — Extensions connues → type MIME correct
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(stem=file_stems, ext=known_ext)
def test_known_extension_returns_correct_mime(stem: str, ext: str) -> None:
    """Pour une extension connue, le Content-Type correspond au mapping."""
    filename = f"{stem}{ext}"
    result = service.get_content_type(filename)
    expected = KNOWN_EXTENSIONS[ext]
    assert result == expected, (
        f"Pour {filename!r} : attendu {expected!r}, obtenu {result!r}"
    )


# ---------------------------------------------------------------------------
# Propriété 2 — Extensions inconnues → application/octet-stream
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(stem=file_stems, ext=unknown_ext)
def test_unknown_extension_returns_octet_stream(stem: str, ext: str) -> None:
    """Pour une extension inconnue, le Content-Type est octet-stream."""
    filename = f"{stem}{ext}"
    result = service.get_content_type(filename)
    assert result == "application/octet-stream", (
        f"Pour {filename!r} : attendu 'application/octet-stream', obtenu {result!r}"
    )


# ---------------------------------------------------------------------------
# Propriété 2 — Insensibilité à la casse de l'extension
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(stem=file_stems, ext=known_ext)
def test_case_insensitive_extension(stem: str, ext: str) -> None:
    """Le mapping fonctionne quelle que soit la casse de l'extension."""
    filename_upper = f"{stem}{ext.upper()}"
    result = service.get_content_type(filename_upper)
    expected = KNOWN_EXTENSIONS[ext]
    assert result == expected, (
        f"Pour {filename_upper!r} : attendu {expected!r}, obtenu {result!r}"
    )


# ---------------------------------------------------------------------------
# Tests déterministes — chaque extension connue
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "filename,expected",
    [
        ("rapport.md", "text/markdown"),
        ("document.pdf", "application/pdf"),
        (
            "rapport.docx",
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document",
        ),
        ("archive.zip", "application/zip"),
        ("data.csv", "application/octet-stream"),
        ("image.png", "application/octet-stream"),
    ],
)
def test_specific_filenames(filename: str, expected: str) -> None:
    """Vérification déterministe pour chaque extension."""
    assert service.get_content_type(filename) == expected
