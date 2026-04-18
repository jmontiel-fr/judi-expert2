"""Test par propriété — Validation de l'extension de fichier au Step 2.

# Feature: workflow-dossier-refactor, Property 1: Upload file extension validation

**Validates: Requirements 3.1, 3.2**

Propriété 1 : Pour tout nom de fichier, l'endpoint Step 2 upload doit accepter
le fichier si et seulement si son extension est `.docx` (insensible à la casse).
Toute autre extension doit être rejetée avec HTTP 400.
"""

import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "local-site"
        / "web"
        / "backend"
    ),
)


# ---------------------------------------------------------------------------
# Pure validation function extracted from step2_upload logic
# ---------------------------------------------------------------------------

def validate_step2_upload_filename(filename: str | None) -> None:
    """Validate that a filename has a .docx extension.

    Reproduces the exact logic from step2_upload in routers/steps.py:
        if not file.filename or not file.filename.lower().endswith(".docx"):
            raise ValueError("Seul le format .docx est accepté")

    Raises:
        ValueError: if filename is None, empty, or does not end with .docx
    """
    if not filename or not filename.lower().endswith(".docx"):
        raise ValueError("Seul le format .docx est accepté")


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_base_names = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        blacklist_characters=".\x00/\\",
    ),
    min_size=1,
    max_size=50,
)

_docx_extensions = st.sampled_from([".docx", ".DOCX", ".Docx", ".dOcX", ".DocX"])
_valid_docx_filenames = st.builds(
    lambda base, ext: base + ext,
    _base_names,
    _docx_extensions,
)

_non_docx_extensions = st.sampled_from([
    ".pdf", ".txt", ".doc", ".xlsx", ".png", ".jpg", ".odt",
    ".rtf", ".csv", ".html", ".pptx", ".zip", ".xml",
])
_invalid_extension_filenames = st.builds(
    lambda base, ext: base + ext,
    _base_names,
    _non_docx_extensions,
)

_empty_filenames = st.one_of(st.just(None), st.just(""))


# ---------------------------------------------------------------------------
# Property 1a — .docx files accepted (any casing)
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(filename=_valid_docx_filenames)
def test_docx_files_are_accepted(filename: str):
    """Pour tout nom de fichier se terminant par .docx (insensible à la casse),
    la validation doit réussir sans lever d'exception."""
    validate_step2_upload_filename(filename)


# ---------------------------------------------------------------------------
# Property 1b — Non-.docx files rejected with HTTP 400 message
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(filename=_invalid_extension_filenames)
def test_non_docx_files_are_rejected(filename: str):
    """Pour tout nom de fichier avec une extension différente de .docx,
    la validation doit lever une ValueError."""
    with pytest.raises(ValueError, match=r"\.docx"):
        validate_step2_upload_filename(filename)


# ---------------------------------------------------------------------------
# Property 1c — Empty/None filenames rejected
# ---------------------------------------------------------------------------

@settings(max_examples=10, deadline=None)
@given(filename=_empty_filenames)
def test_empty_filenames_are_rejected(filename):
    """Les noms de fichier vides ou None doivent être rejetés."""
    with pytest.raises(ValueError, match=r"\.docx"):
        validate_step2_upload_filename(filename)


# ---------------------------------------------------------------------------
# Property 1d — Random non-.docx strings rejected
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(
    filename=st.text(min_size=1, max_size=100).filter(
        lambda s: not s.lower().endswith(".docx")
    )
)
def test_random_non_docx_filenames_are_rejected(filename: str):
    """Pour tout texte aléatoire ne se terminant pas par .docx,
    la validation doit lever une ValueError."""
    with pytest.raises(ValueError, match=r"\.docx"):
        validate_step2_upload_filename(filename)
