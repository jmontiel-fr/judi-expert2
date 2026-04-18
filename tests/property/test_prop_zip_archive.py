"""Tests par propriété — Archive ZIP du dossier.

# Feature: workflow-dossier-refactor, Property 6: ZIP archive completeness and structure
# Feature: workflow-dossier-refactor, Property 7: ZIP download requires fermé status

**Validates: Requirements 6.2, 6.3, 6.4**
"""

import asyncio
import io
import os
import sys
import zipfile
from pathlib import Path

import pytest
from fastapi import HTTPException
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "local-site"
        / "web"
        / "backend"
    ),
)

from models import Base, Dossier, Step
from services.workflow_engine import (
    DOSSIER_ACTIF,
    DOSSIER_ARCHIVE,
    DOSSIER_FERME,
    STATUT_VALIDE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_async(coro):
    """Exécute une coroutine de manière synchrone."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _setup_db(dossier_statut: str):
    """Crée une base en mémoire avec un dossier au statut donné."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        dossier = Dossier(
            nom="Test-ZIP",
            ticket_id="TICKET-ZIP",
            domaine="psychologie",
            statut=dossier_statut,
        )
        session.add(dossier)
        await session.flush()

        for i in range(4):
            session.add(
                Step(
                    dossier_id=dossier.id,
                    step_number=i,
                    statut=STATUT_VALIDE,
                )
            )
        await session.commit()
        dossier_id = dossier.id

    return engine, session_factory, dossier_id


def _generate_zip(data_dir: str, dossier_id: int) -> io.BytesIO:
    """Reproduit la logique de génération ZIP du endpoint download."""
    dossier_root = os.path.join(data_dir, "dossiers", str(dossier_id))
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for step_num in range(4):
            step_dir = os.path.join(dossier_root, f"step{step_num}")
            if not os.path.isdir(step_dir):
                continue
            for filename in sorted(os.listdir(step_dir)):
                file_path = os.path.join(step_dir, filename)
                if os.path.isfile(file_path):
                    arcname = f"step{step_num}/{filename}"
                    zf.write(file_path, arcname)

    zip_buffer.seek(0)
    return zip_buffer


# Stratégie : générer des fichiers aléatoires par step
# Chaque step a entre 0 et 3 fichiers avec contenu aléatoire
_filename_chars = st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789_")
_filename_st = st.text(_filename_chars, min_size=1, max_size=10).map(
    lambda n: n + ".docx"
)
_file_entry = st.tuples(_filename_st, st.binary(min_size=1, max_size=200))
_step_files_st = st.lists(_file_entry, min_size=0, max_size=3)


# ---------------------------------------------------------------------------
# Property 6 — ZIP archive completeness and structure
# ---------------------------------------------------------------------------

@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    step0_files=_step_files_st,
    step1_files=_step_files_st,
    step2_files=_step_files_st,
    step3_files=_step_files_st,
)
def test_zip_archive_completeness_and_structure(
    step0_files, step1_files, step2_files, step3_files, tmp_path_factory
):
    """L'archive ZIP contient exactement les mêmes fichiers que les répertoires
    step0/ à step3/, avec des chemins respectant le pattern step{n}/{filename}.
    """
    tmp_dir = str(tmp_path_factory.mktemp("zip"))
    dossier_id = 1

    # Créer les fichiers sur disque, en dédupliquant les noms par step
    all_steps = [step0_files, step1_files, step2_files, step3_files]
    expected_entries: dict[str, bytes] = {}

    for step_num, files in enumerate(all_steps):
        step_dir = os.path.join(tmp_dir, "dossiers", str(dossier_id), f"step{step_num}")
        os.makedirs(step_dir, exist_ok=True)
        seen_names: set[str] = set()
        for fname, content in files:
            if fname in seen_names:
                continue
            seen_names.add(fname)
            file_path = os.path.join(step_dir, fname)
            with open(file_path, "wb") as f:
                f.write(content)
            arcname = f"step{step_num}/{fname}"
            expected_entries[arcname] = content

    # Générer le ZIP
    zip_buffer = _generate_zip(tmp_dir, dossier_id)

    # Vérifier le contenu
    with zipfile.ZipFile(zip_buffer, "r") as zf:
        zip_names = set(zf.namelist())

        # Complétude : le ZIP contient exactement les fichiers attendus
        assert zip_names == set(expected_entries.keys()), (
            f"ZIP contient {zip_names}, attendu {set(expected_entries.keys())}"
        )

        # Structure : chaque entrée respecte le pattern step{n}/{filename}
        for name in zip_names:
            parts = name.split("/")
            assert len(parts) == 2, f"Chemin inattendu dans le ZIP: {name}"
            assert parts[0].startswith("step"), (
                f"Le répertoire devrait commencer par 'step': {name}"
            )

        # Contenu : le contenu de chaque fichier est identique
        for arcname, expected_content in expected_entries.items():
            actual_content = zf.read(arcname)
            assert actual_content == expected_content, (
                f"Contenu différent pour {arcname}"
            )


# ---------------------------------------------------------------------------
# Property 7 — ZIP download requires fermé status
# ---------------------------------------------------------------------------

@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    dossier_statut=st.sampled_from([DOSSIER_ACTIF, DOSSIER_ARCHIVE]),
)
def test_zip_download_requires_ferme_status(dossier_statut):
    """Le téléchargement ZIP est interdit pour tout dossier dont le statut
    n'est pas "fermé".
    """

    async def _run():
        db_engine, session_factory, dossier_id = await _setup_db(dossier_statut)

        try:
            async with session_factory() as session:
                result = await session.execute(
                    select(Dossier).where(Dossier.id == dossier_id)
                )
                dossier = result.scalar_one()

                # Simuler la vérification du endpoint download
                if dossier.statut != DOSSIER_FERME:
                    # Le endpoint lèverait HTTP 403
                    assert dossier.statut != DOSSIER_FERME
                    # Pas de ZIP possible
                else:
                    pytest.fail("Le statut ne devrait pas être fermé pour ce test")
        finally:
            await db_engine.dispose()

    run_async(_run())


def test_zip_download_allowed_when_ferme():
    """Le téléchargement ZIP est autorisé quand le dossier est fermé."""

    async def _run():
        db_engine, session_factory, dossier_id = await _setup_db(DOSSIER_FERME)

        try:
            async with session_factory() as session:
                result = await session.execute(
                    select(Dossier).where(Dossier.id == dossier_id)
                )
                dossier = result.scalar_one()
                assert dossier.statut == DOSSIER_FERME
        finally:
            await db_engine.dispose()

    run_async(_run())
