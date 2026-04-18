"""Test par propriété — Résolution du chemin de fichier actif.

# Feature: step-files-management, Property 5: Active file path resolution

**Validates: Requirements 5.1, 5.2, 5.3**

Propriété 5 : Pour tout StepFile, ``resolve_file_path`` retourne
``step_file.file_path``. Quand ``is_modified`` est False, ce chemin
pointe vers le fichier original. Quand ``is_modified`` est True, ce
chemin pointe vers le fichier modifié. Dans les deux cas, le fichier
au chemin retourné existe sur le disque.
"""

import sys
import tempfile
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

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

from services.workflow_engine import WorkflowEngine

VALID_EXTENSIONS = [".md", ".pdf", ".docx", ".zip"]

# Stratégies
valid_stems = st.from_regex(r"[a-z][a-z0-9_]{0,19}", fullmatch=True)
valid_extensions = st.sampled_from(VALID_EXTENSIONS)
valid_filenames = st.tuples(valid_stems, valid_extensions).map(
    lambda t: f"{t[0]}{t[1]}"
)
valid_content = st.binary(min_size=1, max_size=512)


def _make_mock_db(step_file_mock):
    """Crée un mock AsyncSession qui retourne le StepFile donné."""
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = step_file_mock

    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)
    return db


@settings(max_examples=100, deadline=None)
@given(
    filename=valid_filenames,
    content=valid_content,
    is_modified=st.booleans(),
)
@pytest.mark.asyncio
async def test_resolve_file_path_returns_file_path_and_file_exists(
    filename: str,
    content: bytes,
    is_modified: bool,
) -> None:
    """resolve_file_path retourne file_path et le fichier existe sur le disque."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        stem = Path(filename).stem
        ext = Path(filename).suffix

        if is_modified:
            # Fichier modifié : le fichier actif est sous le nom original
            active_path = tmp_path / filename
            original_backup = tmp_path / f"{stem}_original{ext}"
            active_path.write_bytes(content)
            original_backup.write_bytes(b"original content")
            original_file_path = str(original_backup)
        else:
            # Fichier original : le fichier actif est sous le nom original
            active_path = tmp_path / filename
            active_path.write_bytes(content)
            original_file_path = None

        # Mock du StepFile retourné par la requête DB
        step_file_mock = MagicMock()
        step_file_mock.file_path = str(active_path)
        step_file_mock.is_modified = is_modified
        step_file_mock.original_file_path = original_file_path

        db = _make_mock_db(step_file_mock)
        engine = WorkflowEngine()

        resolved = await engine.resolve_file_path(
            dossier_id=1,
            step_number=0,
            filename=filename,
            db=db,
        )

        # Le chemin retourné correspond à file_path
        assert resolved == str(active_path)

        # Le fichier existe sur le disque
        assert Path(resolved).exists()
        assert Path(resolved).read_bytes() == content


@pytest.mark.asyncio
async def test_resolve_file_path_raises_404_when_not_found() -> None:
    """resolve_file_path lève 404 quand le fichier n'est pas trouvé."""
    from fastapi import HTTPException

    db = _make_mock_db(None)
    engine = WorkflowEngine()

    with pytest.raises(HTTPException) as exc_info:
        await engine.resolve_file_path(
            dossier_id=1,
            step_number=0,
            filename="inexistant.md",
            db=db,
        )

    assert exc_info.value.status_code == 404
    assert "Fichier non trouvé" in exc_info.value.detail
