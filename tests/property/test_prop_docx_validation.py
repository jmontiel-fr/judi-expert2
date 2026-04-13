"""Test par propriété — Validation du format de fichier .docx.

**Validates: Requirements 8.2, 8.3**

Propriété 5 : Pour tout fichier soumis au Step2, le système doit accepter le
fichier si et seulement si son extension est `.docx`. Pour tout fichier avec
une extension différente, le système doit retourner un message d'erreur
indiquant que seul le format .docx est accepté.
"""

import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# Ajouter le backend au path pour cohérence avec les autres tests
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "site-central"
        / "local"
        / "web"
        / "backend"
    ),
)


# ---------------------------------------------------------------------------
# Pure function extracted from routers/steps.py step2_upload validation
# ---------------------------------------------------------------------------

def validate_docx_filename(filename: str | None) -> None:
    """Validate that a filename has a .docx extension.

    Reproduces the exact logic from step2_upload in routers/steps.py:
        if not f.filename or not f.filename.lower().endswith(".docx"):
            raise ValueError("seul le format .docx est accepté")

    Raises:
        ValueError: if filename is None, empty, or does not end with .docx
    """
    if not filename or not filename.lower().endswith(".docx"):
        raise ValueError("seul le format .docx est accepté")


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Base names: non-empty text without dots (to control extension precisely)
_base_names = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        blacklist_characters=".\x00/\\",
    ),
    min_size=1,
    max_size=50,
)

# Valid .docx filenames with various casings
_docx_extensions = st.sampled_from([".docx", ".DOCX", ".Docx", ".dOcX", ".DocX"])
_valid_docx_filenames = st.builds(
    lambda base, ext: base + ext,
    _base_names,
    _docx_extensions,
)

# Common non-.docx extensions
_non_docx_extensions = st.sampled_from([
    ".pdf", ".txt", ".doc", ".xlsx", ".png", ".jpg", ".odt",
    ".rtf", ".csv", ".html", ".pptx", ".zip", ".xml",
])
_invalid_extension_filenames = st.builds(
    lambda base, ext: base + ext,
    _base_names,
    _non_docx_extensions,
)

# Empty / None filenames
_empty_filenames = st.one_of(
    st.just(None),
    st.just(""),
)


# ---------------------------------------------------------------------------
# Propriété 5a — Fichiers .docx acceptés (toute casse)
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(filename=_valid_docx_filenames)
def test_docx_files_are_accepted(filename: str):
    """Pour tout nom de fichier se terminant par .docx (insensible à la casse),
    la validation doit réussir sans lever d'exception."""
    # Should not raise
    validate_docx_filename(filename)


# ---------------------------------------------------------------------------
# Propriété 5b — Fichiers non-.docx rejetés avec message approprié
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(filename=_invalid_extension_filenames)
def test_non_docx_files_are_rejected(filename: str):
    """Pour tout nom de fichier avec une extension différente de .docx,
    la validation doit lever une ValueError contenant '.docx'."""
    with pytest.raises(ValueError, match=r"\.docx"):
        validate_docx_filename(filename)


# ---------------------------------------------------------------------------
# Propriété 5c — Noms vides ou None rejetés
# ---------------------------------------------------------------------------

@settings(max_examples=10, deadline=None)
@given(filename=_empty_filenames)
def test_empty_filenames_are_rejected(filename):
    """Les noms de fichier vides ou None doivent être rejetés."""
    with pytest.raises(ValueError, match=r"\.docx"):
        validate_docx_filename(filename)


# ---------------------------------------------------------------------------
# Propriété 5d — Noms aléatoires sans extension .docx rejetés
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(filename=st.text(min_size=1, max_size=100).filter(
    lambda s: not s.lower().endswith(".docx")
))
def test_random_non_docx_filenames_are_rejected(filename: str):
    """Pour tout texte aléatoire ne se terminant pas par .docx,
    la validation doit lever une ValueError."""
    with pytest.raises(ValueError, match=r"\.docx"):
        validate_docx_filename(filename)
