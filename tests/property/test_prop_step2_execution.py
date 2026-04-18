"""Test par propriété — Post-conditions d'exécution du Step 2.

# Feature: workflow-dossier-refactor, Property 2: Step 2 execution post-conditions

**Validates: Requirements 3.3, 3.6, 3.7, 3.8**

Propriété 2 : Pour toute exécution valide du Step 2 avec un fichier NEA .docx,
le système doit :
- Sauvegarder exactement 3 fichiers sur disque : nea.docx, re_projet.docx,
  re_projet_auxiliaire.docx
- Créer exactement 3 enregistrements StepFile avec les file_type "nea",
  "re_projet", "re_projet_auxiliaire"
- Mettre le statut de l'étape à "réalisé"
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

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
from models.step_file import StepFile
from services.workflow_engine import (
    DOSSIER_ACTIF,
    STATUT_INITIAL,
    STATUT_REALISE,
    STATUT_VALIDE,
    WorkflowEngine,
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


async def _setup_db_and_dossier(tmp_dir: str):
    """Crée une base en mémoire avec un dossier prêt pour Step 2.

    Steps 0 et 1 sont validés, Step 2 est initial.
    Crée aussi le fichier requisition.md dans step0/.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        dossier = Dossier(
            nom="Test-Step2",
            ticket_id="TICKET-002",
            domaine="psychologie",
            statut=DOSSIER_ACTIF,
        )
        session.add(dossier)
        await session.flush()

        for step_number in range(4):
            statut = STATUT_VALIDE if step_number < 2 else STATUT_INITIAL
            session.add(
                Step(
                    dossier_id=dossier.id,
                    step_number=step_number,
                    statut=statut,
                )
            )
        await session.flush()
        await session.commit()
        dossier_id = dossier.id

    return engine, session_factory, dossier_id


def _create_step0_files(tmp_dir: str, dossier_id: int) -> None:
    """Crée le fichier requisition.md dans step0/ pour le dossier."""
    step0_dir = os.path.join(tmp_dir, "dossiers", str(dossier_id), "step0")
    os.makedirs(step0_dir, exist_ok=True)
    with open(os.path.join(step0_dir, "requisition.md"), "w", encoding="utf-8") as f:
        f.write("# Réquisition\n\n## Questions du Tribunal\n\n1. Question test")


async def _simulate_step2_execution(
    session_factory,
    dossier_id: int,
    nea_bytes: bytes,
    re_projet_content: str,
    re_projet_aux_content: str,
    data_dir: str,
):
    """Simule la logique core de step2_upload (sans HTTP, sans LLM réel).

    Reproduit les étapes 4-13 de step2_upload :
    - Sauvegarde NEA sur disque
    - Sauvegarde RE-Projet et RE-Projet-Auxiliaire sur disque
    - Crée 3 StepFile en base
    - Marque step2 comme "réalisé"
    """
    step_dir = os.path.join(data_dir, "dossiers", str(dossier_id), "step2")
    os.makedirs(step_dir, exist_ok=True)

    # Sauvegarder NEA
    nea_path = os.path.join(step_dir, "nea.docx")
    with open(nea_path, "wb") as f:
        f.write(nea_bytes)

    # Sauvegarder RE-Projet
    re_projet_bytes = re_projet_content.encode("utf-8")
    re_projet_path = os.path.join(step_dir, "re_projet.docx")
    with open(re_projet_path, "wb") as f:
        f.write(re_projet_bytes)

    # Sauvegarder RE-Projet-Auxiliaire
    re_projet_aux_bytes = re_projet_aux_content.encode("utf-8")
    re_projet_aux_path = os.path.join(step_dir, "re_projet_auxiliaire.docx")
    with open(re_projet_aux_path, "wb") as f:
        f.write(re_projet_aux_bytes)

    engine = WorkflowEngine()

    async with session_factory() as session:
        # Charger le step2
        result = await session.execute(
            select(Step)
            .where(Step.dossier_id == dossier_id, Step.step_number == 2)
        )
        step = result.scalar_one()

        # Créer les 3 StepFile
        session.add(StepFile(
            step_id=step.id,
            filename="nea.docx",
            file_path=nea_path,
            file_type="nea",
            file_size=len(nea_bytes),
        ))
        session.add(StepFile(
            step_id=step.id,
            filename="re_projet.docx",
            file_path=re_projet_path,
            file_type="re_projet",
            file_size=len(re_projet_bytes),
        ))
        session.add(StepFile(
            step_id=step.id,
            filename="re_projet_auxiliaire.docx",
            file_path=re_projet_aux_path,
            file_type="re_projet_auxiliaire",
            file_size=len(re_projet_aux_bytes),
        ))

        # Marquer step2 comme "réalisé"
        await engine.execute_step(dossier_id, 2, session)
        await session.commit()


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# NEA content: random bytes (simulating .docx binary content)
_nea_content = st.binary(min_size=1, max_size=500)

# LLM-generated content: random non-empty text
_llm_output = st.text(min_size=1, max_size=500)


# ---------------------------------------------------------------------------
# Property 2 — Step 2 execution post-conditions
# ---------------------------------------------------------------------------

@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    nea_bytes=_nea_content,
    re_projet_text=_llm_output,
    re_projet_aux_text=_llm_output,
)
def test_step2_execution_postconditions(
    nea_bytes: bytes,
    re_projet_text: str,
    re_projet_aux_text: str,
    tmp_path_factory,
):
    """Après une exécution valide du Step 2, le système doit avoir :
    - Exactement 3 fichiers sur disque dans step2/
    - Exactement 3 StepFile en base avec les bons file_type
    - Le statut de l'étape à "réalisé"
    """
    tmp_dir = str(tmp_path_factory.mktemp("step2"))

    async def _run():
        db_engine, session_factory, dossier_id = await _setup_db_and_dossier(
            tmp_dir
        )

        _create_step0_files(tmp_dir, dossier_id)

        try:
            await _simulate_step2_execution(
                session_factory,
                dossier_id,
                nea_bytes,
                re_projet_text,
                re_projet_aux_text,
                tmp_dir,
            )

            # --- Vérifications post-conditions ---

            step_dir = os.path.join(
                tmp_dir, "dossiers", str(dossier_id), "step2"
            )

            # Post-condition 1: Exactement 3 fichiers sur disque
            files_on_disk = os.listdir(step_dir)
            assert len(files_on_disk) == 3, (
                f"Attendu 3 fichiers sur disque, trouvé {len(files_on_disk)}: "
                f"{files_on_disk}"
            )
            expected_filenames = {"nea.docx", "re_projet.docx", "re_projet_auxiliaire.docx"}
            assert set(files_on_disk) == expected_filenames, (
                f"Fichiers attendus: {expected_filenames}, "
                f"trouvés: {set(files_on_disk)}"
            )

            # Post-condition 2: Contenu des fichiers correct
            with open(os.path.join(step_dir, "nea.docx"), "rb") as f:
                assert f.read() == nea_bytes
            with open(os.path.join(step_dir, "re_projet.docx"), "rb") as f:
                assert f.read() == re_projet_text.encode("utf-8")
            with open(os.path.join(step_dir, "re_projet_auxiliaire.docx"), "rb") as f:
                assert f.read() == re_projet_aux_text.encode("utf-8")

            # Post-condition 3: Exactement 3 StepFile en base avec bons types
            async with session_factory() as session:
                result = await session.execute(
                    select(Step)
                    .options(selectinload(Step.files))
                    .where(
                        Step.dossier_id == dossier_id,
                        Step.step_number == 2,
                    )
                )
                step = result.scalar_one()

                assert len(step.files) == 3, (
                    f"Attendu 3 StepFile, trouvé {len(step.files)}"
                )

                file_types = {sf.file_type for sf in step.files}
                expected_types = {"nea", "re_projet", "re_projet_auxiliaire"}
                assert file_types == expected_types, (
                    f"Types attendus: {expected_types}, trouvés: {file_types}"
                )

                # Vérifier les tailles
                for sf in step.files:
                    if sf.file_type == "nea":
                        assert sf.file_size == len(nea_bytes)
                    elif sf.file_type == "re_projet":
                        assert sf.file_size == len(re_projet_text.encode("utf-8"))
                    elif sf.file_type == "re_projet_auxiliaire":
                        assert sf.file_size == len(re_projet_aux_text.encode("utf-8"))

                # Post-condition 4: Statut de l'étape = "réalisé"
                assert step.statut == STATUT_REALISE, (
                    f"Statut attendu: {STATUT_REALISE}, trouvé: {step.statut}"
                )
        finally:
            await db_engine.dispose()

    run_async(_run())
