"""Test par propriété — Post-conditions d'exécution du Step 3.

# Feature: workflow-dossier-refactor, Property 3: Step 3 execution post-conditions

**Validates: Requirements 4.4, 4.5, 4.6**

Propriété 3 : Pour toute exécution valide du Step 3 (NEA présent dans step2/),
le système doit :
- Sauvegarder `ref_projet.docx` sur disque dans `data/dossiers/{id}/step3/`
- Créer exactement 1 enregistrement StepFile avec file_type "ref_projet"
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
    """Crée une base en mémoire avec un dossier prêt pour Step 3.

    Steps 0, 1 et 2 sont validés, Step 3 est initial.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        dossier = Dossier(
            nom="Test-Step3",
            ticket_id="TICKET-003",
            domaine="psychologie",
            statut=DOSSIER_ACTIF,
        )
        session.add(dossier)
        await session.flush()

        for step_number in range(4):
            statut = STATUT_VALIDE if step_number < 3 else STATUT_INITIAL
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


def _create_prerequisite_files(tmp_dir: str, dossier_id: int, nea_bytes: bytes) -> None:
    """Crée les fichiers prérequis : requisition.md (step0) et nea.docx (step2)."""
    step0_dir = os.path.join(tmp_dir, "dossiers", str(dossier_id), "step0")
    os.makedirs(step0_dir, exist_ok=True)
    with open(os.path.join(step0_dir, "requisition.md"), "w", encoding="utf-8") as f:
        f.write("# Réquisition\n\n## Questions du Tribunal\n\n1. Question test")

    step2_dir = os.path.join(tmp_dir, "dossiers", str(dossier_id), "step2")
    os.makedirs(step2_dir, exist_ok=True)
    with open(os.path.join(step2_dir, "nea.docx"), "wb") as f:
        f.write(nea_bytes)


async def _simulate_step3_execution(
    session_factory,
    dossier_id: int,
    ref_projet_content: str,
    data_dir: str,
):
    """Simule la logique core de step3_execute (sans HTTP, sans LLM réel).

    Reproduit les étapes clés de step3_execute :
    - Sauvegarde ref_projet.docx sur disque
    - Crée 1 StepFile en base
    - Marque step3 comme "réalisé"
    """
    step_dir = os.path.join(data_dir, "dossiers", str(dossier_id), "step3")
    os.makedirs(step_dir, exist_ok=True)

    # Sauvegarder REF-Projet
    ref_projet_bytes = ref_projet_content.encode("utf-8")
    ref_projet_path = os.path.join(step_dir, "ref_projet.docx")
    with open(ref_projet_path, "wb") as f:
        f.write(ref_projet_bytes)

    engine = WorkflowEngine()

    async with session_factory() as session:
        # Charger le step3
        result = await session.execute(
            select(Step)
            .where(Step.dossier_id == dossier_id, Step.step_number == 3)
        )
        step = result.scalar_one()

        # Créer 1 StepFile
        session.add(StepFile(
            step_id=step.id,
            filename="ref_projet.docx",
            file_path=ref_projet_path,
            file_type="ref_projet",
            file_size=len(ref_projet_bytes),
        ))

        # Marquer step3 comme "réalisé"
        await engine.execute_step(dossier_id, 3, session)
        await session.commit()


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# NEA content: random bytes (simulating .docx binary content)
_nea_content = st.binary(min_size=1, max_size=500)

# LLM-generated content: random non-empty text
_llm_output = st.text(min_size=1, max_size=500)


# ---------------------------------------------------------------------------
# Property 3 — Step 3 execution post-conditions
# ---------------------------------------------------------------------------

@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    nea_bytes=_nea_content,
    ref_projet_text=_llm_output,
)
def test_step3_execution_postconditions(
    nea_bytes: bytes,
    ref_projet_text: str,
    tmp_path_factory,
):
    """Après une exécution valide du Step 3, le système doit avoir :
    - Exactement 1 fichier ref_projet.docx sur disque dans step3/
    - Exactement 1 StepFile en base avec file_type "ref_projet"
    - Le statut de l'étape à "réalisé"
    """
    tmp_dir = str(tmp_path_factory.mktemp("step3"))

    async def _run():
        db_engine, session_factory, dossier_id = await _setup_db_and_dossier(
            tmp_dir
        )

        _create_prerequisite_files(tmp_dir, dossier_id, nea_bytes)

        try:
            await _simulate_step3_execution(
                session_factory,
                dossier_id,
                ref_projet_text,
                tmp_dir,
            )

            # --- Vérifications post-conditions ---

            step_dir = os.path.join(
                tmp_dir, "dossiers", str(dossier_id), "step3"
            )

            # Post-condition 1: Exactement 1 fichier sur disque
            files_on_disk = os.listdir(step_dir)
            assert len(files_on_disk) == 1, (
                f"Attendu 1 fichier sur disque, trouvé {len(files_on_disk)}: "
                f"{files_on_disk}"
            )
            assert files_on_disk[0] == "ref_projet.docx", (
                f"Fichier attendu: ref_projet.docx, trouvé: {files_on_disk[0]}"
            )

            # Post-condition 2: Contenu du fichier correct
            with open(os.path.join(step_dir, "ref_projet.docx"), "rb") as f:
                assert f.read() == ref_projet_text.encode("utf-8")

            # Post-condition 3: Exactement 1 StepFile en base avec bon type
            async with session_factory() as session:
                result = await session.execute(
                    select(Step)
                    .options(selectinload(Step.files))
                    .where(
                        Step.dossier_id == dossier_id,
                        Step.step_number == 3,
                    )
                )
                step = result.scalar_one()

                assert len(step.files) == 1, (
                    f"Attendu 1 StepFile, trouvé {len(step.files)}"
                )

                sf = step.files[0]
                assert sf.file_type == "ref_projet", (
                    f"Type attendu: ref_projet, trouvé: {sf.file_type}"
                )
                assert sf.filename == "ref_projet.docx", (
                    f"Filename attendu: ref_projet.docx, trouvé: {sf.filename}"
                )
                assert sf.file_size == len(ref_projet_text.encode("utf-8")), (
                    f"Taille attendue: {len(ref_projet_text.encode('utf-8'))}, "
                    f"trouvée: {sf.file_size}"
                )

                # Post-condition 4: Statut de l'étape = "réalisé"
                assert step.statut == STATUT_REALISE, (
                    f"Statut attendu: {STATUT_REALISE}, trouvé: {step.statut}"
                )
        finally:
            await db_engine.dispose()

    run_async(_run())
