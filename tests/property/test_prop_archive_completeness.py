"""Test par propriété — Complétude et immutabilité de l'archive.

**Validates: Requirements 9.6, 34.1, 34.2**

Propriété 7 : Pour tout dossier finalisé (Step3 validé), l'archive ZIP générée
doit contenir exactement tous les fichiers du dossier (sauf archive.zip elle-même).
De plus, pour tout dossier archivé, toute tentative de modification ou suppression
des fichiers contenus doit échouer.

Teste la logique pure d'archivage extraite de routers/steps.py step3_validate
et l'immutabilité via le WorkflowEngine.
"""

import asyncio
import os
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Ajouter le backend au path pour les imports
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

from models import Base, Dossier, Step
from services.workflow_engine import (
    DOSSIER_ARCHIVE,
    STATUT_VALIDE,
    WorkflowEngine,
)


# ---------------------------------------------------------------------------
# Pure function extracted from routers/steps.py step3_validate
# ---------------------------------------------------------------------------

def create_archive(dossier_path: str) -> str:
    """Create a ZIP archive of all files in dossier_path (excluding archive.zip).

    Reproduces the exact logic from step3_validate in routers/steps.py:
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(dossier_path):
                for filename in files:
                    if filename == "archive.zip":
                        continue
                    abs_path = os.path.join(root, filename)
                    arc_name = os.path.relpath(abs_path, dossier_path)
                    zf.write(abs_path, arc_name)

    Returns the path to the created archive.
    """
    archive_path = os.path.join(dossier_path, "archive.zip")
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(dossier_path):
            for filename in files:
                if filename == "archive.zip":
                    continue
                abs_path = os.path.join(root, filename)
                arc_name = os.path.relpath(abs_path, dossier_path)
                zf.write(abs_path, arc_name)
    return archive_path


def collect_all_files(dossier_path: str) -> dict[str, bytes]:
    """Collect all files in dossier_path (excluding archive.zip) with their contents.

    Returns a dict mapping relative paths (using forward slashes) to file contents.
    """
    result = {}
    for root, _dirs, files in os.walk(dossier_path):
        for filename in files:
            if filename == "archive.zip":
                continue
            abs_path = os.path.join(root, filename)
            rel_path = os.path.relpath(abs_path, dossier_path).replace(os.sep, "/")
            with open(abs_path, "rb") as f:
                result[rel_path] = f.read()
    return result


# ---------------------------------------------------------------------------
# Helper : boucle d'événements pour exécuter les coroutines
# ---------------------------------------------------------------------------

def run_async(coro):
    """Exécute une coroutine de manière synchrone."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Safe filename characters (letters, digits, underscore, hyphen)
_safe_chars = st.characters(
    whitelist_categories=("L", "N"),
    whitelist_characters="_-",
)

# Filename base (non-empty, no path separators or special chars)
_filename_base = st.text(
    alphabet=_safe_chars,
    min_size=1,
    max_size=20,
)

# File extensions commonly found in a dossier
_extensions = st.sampled_from([".pdf", ".md", ".docx", ".txt", ".json"])

# A single filename (base + extension), excluding "archive.zip"
_filename = st.builds(
    lambda base, ext: base + ext,
    _filename_base,
    _extensions,
).filter(lambda name: name != "archive.zip")

# File content (binary)
_file_content = st.binary(min_size=0, max_size=500)

# Subdirectories matching the dossier structure (step0, step1, step2, step3)
_subdirs = st.sampled_from(["step0", "step1", "step2", "step3"])

# A single file entry: (subdir, filename, content)
_file_entry = st.tuples(_subdirs, _filename, _file_content)

# A set of file entries for a dossier (at least 1 file)
_file_entries = st.lists(
    _file_entry,
    min_size=1,
    max_size=15,
).map(
    # Deduplicate by (subdir, filename) — keep last occurrence
    lambda entries: list({(sd, fn): (sd, fn, content) for sd, fn, content in entries}.values())
)


# ---------------------------------------------------------------------------
# Propriété 7a — Complétude de l'archive : le ZIP contient tous les fichiers
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(file_entries=_file_entries)
def test_archive_contains_all_dossier_files(file_entries):
    """Pour tout ensemble de fichiers dans un dossier, l'archive ZIP créée
    doit contenir exactement tous les fichiers (sauf archive.zip elle-même)."""

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Create the dossier directory structure with files
        for subdir, filename, content in file_entries:
            dir_path = os.path.join(tmpdir, subdir)
            os.makedirs(dir_path, exist_ok=True)
            file_path = os.path.join(dir_path, filename)
            with open(file_path, "wb") as f:
                f.write(content)

        # 2. Collect expected files before archiving
        expected_files = collect_all_files(tmpdir)
        assert len(expected_files) > 0, "Should have at least one file"

        # 3. Create the archive
        archive_path = create_archive(tmpdir)
        assert os.path.isfile(archive_path), "Archive should exist"

        # 4. Verify the ZIP contains exactly all expected files
        with zipfile.ZipFile(archive_path, "r") as zf:
            archived_names = set(zf.namelist())
            expected_names = set(expected_files.keys())

            assert archived_names == expected_names, (
                f"Archive mismatch.\n"
                f"  Missing from archive: {expected_names - archived_names}\n"
                f"  Extra in archive: {archived_names - expected_names}"
            )


# ---------------------------------------------------------------------------
# Propriété 7b — Intégrité du contenu : les fichiers dans le ZIP sont identiques
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(file_entries=_file_entries)
def test_archive_file_contents_match_originals(file_entries):
    """Pour tout ensemble de fichiers, le contenu de chaque fichier dans
    l'archive ZIP doit être identique au fichier original."""

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Create the dossier directory structure
        for subdir, filename, content in file_entries:
            dir_path = os.path.join(tmpdir, subdir)
            os.makedirs(dir_path, exist_ok=True)
            with open(os.path.join(dir_path, filename), "wb") as f:
                f.write(content)

        # 2. Collect expected files
        expected_files = collect_all_files(tmpdir)

        # 3. Create the archive
        archive_path = create_archive(tmpdir)

        # 4. Verify each file's content matches
        with zipfile.ZipFile(archive_path, "r") as zf:
            for rel_path, expected_content in expected_files.items():
                actual_content = zf.read(rel_path)
                assert actual_content == expected_content, (
                    f"Content mismatch for {rel_path}: "
                    f"expected {len(expected_content)} bytes, "
                    f"got {len(actual_content)} bytes"
                )


# ---------------------------------------------------------------------------
# Propriété 7c — archive.zip est exclue de l'archive elle-même
# ---------------------------------------------------------------------------

@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(file_entries=_file_entries)
def test_archive_excludes_itself(file_entries):
    """L'archive ZIP ne doit jamais contenir 'archive.zip' comme entrée."""

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create files
        for subdir, filename, content in file_entries:
            dir_path = os.path.join(tmpdir, subdir)
            os.makedirs(dir_path, exist_ok=True)
            with open(os.path.join(dir_path, filename), "wb") as f:
                f.write(content)

        # Create the archive
        archive_path = create_archive(tmpdir)

        # Verify archive.zip is not in the ZIP
        with zipfile.ZipFile(archive_path, "r") as zf:
            for name in zf.namelist():
                assert name != "archive.zip", (
                    "archive.zip should not be included in the archive"
                )


# ---------------------------------------------------------------------------
# Propriété 7d — Immutabilité : après archivage, le WorkflowEngine rejette
#                toute opération execute/validate
# ---------------------------------------------------------------------------

@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    step_to_execute=st.integers(min_value=0, max_value=3),
    step_to_validate=st.integers(min_value=0, max_value=3),
)
def test_archived_dossier_rejects_modifications(step_to_execute, step_to_validate):
    """Pour tout dossier archivé, toute tentative d'execute_step ou
    validate_step doit échouer avec HTTP 403."""

    engine = WorkflowEngine()

    db_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _run():
        async with db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_factory() as session:
            # Create an archived dossier with all steps validated
            dossier = Dossier(
                nom="Archived-Dossier",
                ticket_id=f"TICKET-ARCH-{step_to_execute}-{step_to_validate}",
                domaine="psychologie",
                statut=DOSSIER_ARCHIVE,
            )
            session.add(dossier)
            await session.flush()

            for step_number in range(4):
                session.add(
                    Step(
                        dossier_id=dossier.id,
                        step_number=step_number,
                        statut=STATUT_VALIDE,
                    )
                )
            await session.flush()
            await session.commit()
            dossier_id = dossier.id

        # Test execute_step is rejected
        async with session_factory() as session:
            try:
                await engine.execute_step(dossier_id, step_to_execute, session)
                raise AssertionError(
                    f"execute_step({step_to_execute}) should have been rejected "
                    f"on archived dossier"
                )
            except HTTPException as exc:
                assert exc.status_code == 403, (
                    f"Expected 403, got {exc.status_code}"
                )

        # Test validate_step is rejected
        async with session_factory() as session:
            try:
                await engine.validate_step(dossier_id, step_to_validate, session)
                raise AssertionError(
                    f"validate_step({step_to_validate}) should have been rejected "
                    f"on archived dossier"
                )
            except HTTPException as exc:
                assert exc.status_code == 403, (
                    f"Expected 403, got {exc.status_code}"
                )

        await db_engine.dispose()

    run_async(_run())
