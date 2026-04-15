"""Router des étapes du workflow d'expertise (Step0–Step3).

Valide : Exigences 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 7.1, 7.2, 7.3, 7.4,
         9.1, 9.2, 9.3, 9.4, 9.5, 9.6
"""

from __future__ import annotations

import logging
import os
import zipfile

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fastapi.responses import FileResponse

from database import get_db
from models.local_config import LocalConfig
from models.step import Step
from models.step_file import StepFile
from routers.auth import get_current_user
from services.llm_service import LLMService
from services.rag_service import RAGService
from services.workflow_engine import workflow_engine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OCR_HOST: str = os.environ.get("OCR_HOST", "http://judi-ocr:8001")
DATA_DIR: str = os.environ.get("DATA_DIR", "data")

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class MarkdownResponse(BaseModel):
    markdown: str


class MarkdownUpdateRequest(BaseModel):
    content: str


class MarkdownUpdateResponse(BaseModel):
    message: str


class ExtractResponse(BaseModel):
    markdown: str
    pdf_path: str
    md_path: str


class QmecResponse(BaseModel):
    qmec: str


class Step1ValidateResponse(BaseModel):
    message: str


class Step2UploadResponse(BaseModel):
    message: str
    filenames: list[str]


class Step2ValidateResponse(BaseModel):
    message: str


class Step3ExecuteResponse(BaseModel):
    ref: str
    raux: str


class Step3ValidateResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _step0_dir(dossier_id: int) -> str:
    """Retourne le chemin du répertoire step0 pour un dossier."""
    return os.path.join(DATA_DIR, "dossiers", str(dossier_id), "step0")


def _step1_dir(dossier_id: int) -> str:
    """Retourne le chemin du répertoire step1 pour un dossier."""
    return os.path.join(DATA_DIR, "dossiers", str(dossier_id), "step1")


def _step2_dir(dossier_id: int) -> str:
    """Retourne le chemin du répertoire step2 pour un dossier."""
    return os.path.join(DATA_DIR, "dossiers", str(dossier_id), "step2")


def _step3_dir(dossier_id: int) -> str:
    """Retourne le chemin du répertoire step3 pour un dossier."""
    return os.path.join(DATA_DIR, "dossiers", str(dossier_id), "step3")


def _dossier_dir(dossier_id: int) -> str:
    """Retourne le chemin du répertoire racine d'un dossier."""
    return os.path.join(DATA_DIR, "dossiers", str(dossier_id))


async def _get_step(
    dossier_id: int, step_number: int, db: AsyncSession
) -> Step:
    """Charge l'étape demandée avec ses fichiers ou lève 404."""
    result = await db.execute(
        select(Step)
        .options(selectinload(Step.files))
        .where(Step.dossier_id == dossier_id, Step.step_number == step_number)
    )
    step = result.scalar_one_or_none()
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Étape {step_number} non trouvée pour le dossier {dossier_id}",
        )
    return step


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()


# ---- Step0 : POST /api/dossiers/{id}/step0/extract -----------------------

@router.post(
    "/{dossier_id}/step0/extract",
    response_model=ExtractResponse,
    status_code=status.HTTP_201_CREATED,
)
async def step0_extract(
    dossier_id: int,
    file: UploadFile,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload un PDF-scan, lance l'OCR puis structure en Markdown via LLM."""

    # 1. Vérifier que le fichier est un PDF
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seuls les fichiers PDF sont acceptés",
        )

    # 2. Créer le répertoire de destination
    step_dir = _step0_dir(dossier_id)
    os.makedirs(step_dir, exist_ok=True)

    # 3. Lire le contenu du fichier uploadé
    pdf_content = await file.read()
    if not pdf_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier PDF est vide",
        )

    # 4. Sauvegarder le PDF original
    pdf_path = os.path.join(step_dir, "requisition.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_content)

    # 5. Appeler le service OCR
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OCR_HOST}/api/ocr/extract",
                files={"file": ("requisition.pdf", pdf_content, "application/pdf")},
            )
            resp.raise_for_status()
            ocr_data = resp.json()
            texte_brut = ocr_data.get("text", "")
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service OCR indisponible — vérifiez que le conteneur judi-ocr est démarré",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service OCR indisponible — délai de connexion dépassé",
        )
    except httpx.HTTPStatusError as exc:
        logger.error("Erreur OCR HTTP %s", exc.response.status_code)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erreur du service OCR lors de l'extraction",
        )

    if not texte_brut.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le PDF ne contient pas de texte exploitable",
        )

    # 6. Appeler le LLM pour structurer en Markdown
    llm = LLMService()
    try:
        markdown = await llm.structurer_markdown(texte_brut)
    except Exception as exc:
        logger.error("Erreur LLM lors de la structuration Markdown : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service LLM indisponible — essayez de redémarrer le conteneur judi-llm",
        )

    # 7. Sauvegarder le fichier Markdown
    md_path = os.path.join(step_dir, "requisition.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    # 8. Créer les entrées StepFile en base
    step = await _get_step(dossier_id, 0, db)

    pdf_size = len(pdf_content)
    md_size = len(markdown.encode("utf-8"))

    step_file_pdf = StepFile(
        step_id=step.id,
        filename="requisition.pdf",
        file_path=pdf_path,
        file_type="pdf_scan",
        file_size=pdf_size,
    )
    step_file_md = StepFile(
        step_id=step.id,
        filename="requisition.md",
        file_path=md_path,
        file_type="markdown",
        file_size=md_size,
    )
    db.add(step_file_pdf)
    db.add(step_file_md)

    # 9. Marquer step0 comme "réalisé" via le WorkflowEngine
    await workflow_engine.execute_step(dossier_id, 0, db)
    await db.commit()

    return ExtractResponse(
        markdown=markdown,
        pdf_path=pdf_path,
        md_path=md_path,
    )


# ---- Step0 : GET /api/dossiers/{id}/step0/markdown -----------------------

@router.get(
    "/{dossier_id}/step0/markdown",
    response_model=MarkdownResponse,
)
async def step0_get_markdown(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retourne le contenu du fichier Markdown généré pour step0."""

    # Vérifier l'accès à l'étape
    await workflow_engine.require_step_access(dossier_id, 0, db)

    md_path = os.path.join(_step0_dir(dossier_id), "requisition.md")
    if not os.path.isfile(md_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier Markdown non trouvé — lancez d'abord l'extraction",
        )

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    return MarkdownResponse(markdown=content)


# ---- Step0 : PUT /api/dossiers/{id}/step0/markdown -----------------------

@router.put(
    "/{dossier_id}/step0/markdown",
    response_model=MarkdownUpdateResponse,
)
async def step0_update_markdown(
    dossier_id: int,
    body: MarkdownUpdateRequest,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Met à jour le fichier Markdown (édition manuelle par l'expert)."""

    # Vérifier que l'étape n'est pas validée (immuable)
    await workflow_engine.require_step_not_validated(dossier_id, 0, db)

    md_path = os.path.join(_step0_dir(dossier_id), "requisition.md")
    if not os.path.isfile(md_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier Markdown non trouvé — lancez d'abord l'extraction",
        )

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(body.content)

    # Mettre à jour la taille du fichier dans StepFile
    step = await _get_step(dossier_id, 0, db)
    for sf in step.files:
        if sf.filename == "requisition.md":
            sf.file_size = len(body.content.encode("utf-8"))
            break

    await db.commit()

    return MarkdownUpdateResponse(message="Fichier Markdown mis à jour")


# ---- Step1 : POST /api/dossiers/{id}/step1/execute -----------------------

@router.post(
    "/{dossier_id}/step1/execute",
    response_model=QmecResponse,
    status_code=status.HTTP_201_CREATED,
)
async def step1_execute(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Génère le QMEC (plan d'entretien) à partir de QT + TPE + contexte RAG.

    Valide : Exigences 7.1, 7.2
    """

    # 1. Vérifier l'accès au step1
    await workflow_engine.require_step_access(dossier_id, 1, db)

    # 2. Lire le fichier Markdown de step0 pour obtenir les QT
    md_path = os.path.join(_step0_dir(dossier_id), "requisition.md")
    if not os.path.isfile(md_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier Markdown de la réquisition non trouvé — complétez d'abord le Step0",
        )

    with open(md_path, "r", encoding="utf-8") as f:
        qt = f.read()

    # 3. Récupérer le domaine depuis LocalConfig
    result = await db.execute(select(LocalConfig).limit(1))
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration initiale non effectuée",
        )
    domaine = config.domaine

    # 4. Récupérer le TPE depuis la base RAG (collection config_{domaine})
    rag = RAGService()
    try:
        tpe_docs = await rag.search(
            query="trame plan entretien TPE",
            collection=f"config_{domaine}",
            limit=5,
        )
    except Exception as exc:
        logger.error("Erreur RAG lors de la recherche du TPE : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service RAG indisponible — vérifiez que le conteneur judi-rag est démarré",
        )

    tpe = "\n\n".join(doc.content for doc in tpe_docs) if tpe_docs else ""

    # 5. Récupérer le contexte domaine depuis la base RAG (collection corpus_{domaine})
    try:
        contexte_docs = await rag.search(
            query=qt[:500],
            collection=f"corpus_{domaine}",
            limit=5,
        )
    except Exception as exc:
        logger.error("Erreur RAG lors de la recherche du contexte domaine : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service RAG indisponible — vérifiez que le conteneur judi-rag est démarré",
        )

    contexte_rag = "\n\n".join(doc.content for doc in contexte_docs) if contexte_docs else ""

    # 6. Appeler le LLM pour générer le QMEC
    llm = LLMService()
    try:
        qmec = await llm.generer_qmec(qt, tpe, contexte_rag)
    except Exception as exc:
        logger.error("Erreur LLM lors de la génération du QMEC : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service LLM indisponible — essayez de redémarrer le conteneur judi-llm",
        )

    # 7. Sauvegarder le QMEC
    step1_path = _step1_dir(dossier_id)
    os.makedirs(step1_path, exist_ok=True)
    qmec_path = os.path.join(step1_path, "qmec.md")
    with open(qmec_path, "w", encoding="utf-8") as f:
        f.write(qmec)

    # 8. Créer l'entrée StepFile en base
    step = await _get_step(dossier_id, 1, db)
    step_file = StepFile(
        step_id=step.id,
        filename="qmec.md",
        file_path=qmec_path,
        file_type="qmec",
        file_size=len(qmec.encode("utf-8")),
    )
    db.add(step_file)

    # 9. Marquer step1 comme "réalisé"
    await workflow_engine.execute_step(dossier_id, 1, db)
    await db.commit()

    return QmecResponse(qmec=qmec)


# ---- Step1 : GET /api/dossiers/{id}/step1/download -----------------------

@router.get(
    "/{dossier_id}/step1/download",
)
async def step1_download(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Télécharge le fichier QMEC généré pour step1.

    Valide : Exigence 7.3
    """

    # Vérifier l'accès à l'étape
    await workflow_engine.require_step_access(dossier_id, 1, db)

    qmec_path = os.path.join(_step1_dir(dossier_id), "qmec.md")
    if not os.path.isfile(qmec_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier QMEC non trouvé — lancez d'abord l'exécution du Step1",
        )

    return FileResponse(
        path=qmec_path,
        filename="qmec.md",
        media_type="text/markdown",
    )


# ---- Step1 : POST /api/dossiers/{id}/step1/validate ---------------------

@router.post(
    "/{dossier_id}/step1/validate",
    response_model=Step1ValidateResponse,
)
async def step1_validate(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Valide le Step1 (verrouillage) et autorise l'accès au Step2.

    Valide : Exigence 7.4
    """

    await workflow_engine.validate_step(dossier_id, 1, db)
    await db.commit()

    return Step1ValidateResponse(message="Step1 validé avec succès")


# ---- Step2 : POST /api/dossiers/{id}/step2/upload ------------------------

@router.post(
    "/{dossier_id}/step2/upload",
    response_model=Step2UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def step2_upload(
    dossier_id: int,
    ne: UploadFile,
    reb: UploadFile,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload des fichiers NE.docx et REB.docx pour le Step2.

    Valide : Exigences 8.1, 8.2, 8.3
    """

    # 1. Vérifier l'accès au step2
    await workflow_engine.require_step_access(dossier_id, 2, db)

    # 2. Valider le format .docx pour les deux fichiers
    for f in (ne, reb):
        if not f.filename or not f.filename.lower().endswith(".docx"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="seul le format .docx est accepté",
            )

    # 3. Lire le contenu des fichiers
    ne_content = await ne.read()
    reb_content = await reb.read()

    # 4. Créer le répertoire de destination
    step_dir = _step2_dir(dossier_id)
    os.makedirs(step_dir, exist_ok=True)

    # 5. Sauvegarder les fichiers
    ne_path = os.path.join(step_dir, "ne.docx")
    reb_path = os.path.join(step_dir, "reb.docx")

    with open(ne_path, "wb") as f:
        f.write(ne_content)
    with open(reb_path, "wb") as f:
        f.write(reb_content)

    # 6. Créer les entrées StepFile en base
    step = await _get_step(dossier_id, 2, db)

    db.add(StepFile(
        step_id=step.id,
        filename="ne.docx",
        file_path=ne_path,
        file_type="ne",
        file_size=len(ne_content),
    ))
    db.add(StepFile(
        step_id=step.id,
        filename="reb.docx",
        file_path=reb_path,
        file_type="reb",
        file_size=len(reb_content),
    ))

    # 7. Marquer step2 comme "réalisé"
    await workflow_engine.execute_step(dossier_id, 2, db)
    await db.commit()

    return Step2UploadResponse(
        message="Fichiers NE et REB uploadés avec succès",
        filenames=["ne.docx", "reb.docx"],
    )


# ---- Step2 : POST /api/dossiers/{id}/step2/validate ---------------------

@router.post(
    "/{dossier_id}/step2/validate",
    response_model=Step2ValidateResponse,
)
async def step2_validate(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Valide le Step2 (verrouillage) et autorise l'accès au Step3.

    Valide : Exigence 8.4
    """

    await workflow_engine.validate_step(dossier_id, 2, db)
    await db.commit()

    return Step2ValidateResponse(message="Step2 validé avec succès")


# ---- Step3 : POST /api/dossiers/{id}/step3/execute -----------------------

@router.post(
    "/{dossier_id}/step3/execute",
    response_model=Step3ExecuteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def step3_execute(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Génère le REF et le RAUX à partir de REB + QT + NE + Template + Corpus.

    Valide : Exigences 9.1, 9.2, 9.3, 9.4
    """

    # 1. Vérifier l'accès au step3
    await workflow_engine.require_step_access(dossier_id, 3, db)

    # 2. Lire le fichier Markdown de step0 pour obtenir les QT
    md_path = os.path.join(_step0_dir(dossier_id), "requisition.md")
    if not os.path.isfile(md_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier Markdown de la réquisition non trouvé — complétez d'abord le Step0",
        )
    with open(md_path, "r", encoding="utf-8") as f:
        qt = f.read()

    # 3. Lire les fichiers NE et REB de step2
    ne_path = os.path.join(_step2_dir(dossier_id), "ne.docx")
    reb_path = os.path.join(_step2_dir(dossier_id), "reb.docx")

    if not os.path.isfile(ne_path) or not os.path.isfile(reb_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichiers NE et REB non trouvés — complétez d'abord le Step2",
        )

    with open(ne_path, "rb") as f:
        ne = f.read().decode("utf-8", errors="replace")
    with open(reb_path, "rb") as f:
        reb = f.read().decode("utf-8", errors="replace")

    # 4. Récupérer le domaine depuis LocalConfig
    result = await db.execute(select(LocalConfig).limit(1))
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration initiale non effectuée",
        )
    domaine = config.domaine

    # 5. Récupérer le Template Rapport depuis la base RAG
    rag = RAGService()
    try:
        template_docs = await rag.search(
            query="template rapport",
            collection=f"config_{domaine}",
            limit=5,
        )
    except Exception as exc:
        logger.error("Erreur RAG lors de la recherche du template : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service RAG indisponible — vérifiez que le conteneur judi-rag est démarré",
        )

    template = "\n\n".join(doc.content for doc in template_docs) if template_docs else ""

    # 6. Récupérer le contexte corpus depuis la base RAG
    try:
        corpus_docs = await rag.search(
            query=qt[:500],
            collection=f"corpus_{domaine}",
            limit=5,
        )
    except Exception as exc:
        logger.error("Erreur RAG lors de la recherche du corpus : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service RAG indisponible — vérifiez que le conteneur judi-rag est démarré",
        )

    corpus = "\n\n".join(doc.content for doc in corpus_docs) if corpus_docs else ""

    # 7. Générer le REF via LLM
    llm = LLMService()
    try:
        ref = await llm.generer_ref(reb, qt, ne, template)
    except Exception as exc:
        logger.error("Erreur LLM lors de la génération du REF : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service LLM indisponible — essayez de redémarrer le conteneur judi-llm",
        )

    # 8. Générer le RAUX Partie 1 (contestations)
    try:
        raux_p1 = await llm.generer_raux_p1(ref, corpus)
    except Exception as exc:
        logger.error("Erreur LLM lors de la génération du RAUX P1 : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service LLM indisponible — essayez de redémarrer le conteneur judi-llm",
        )

    # 9. Générer le RAUX Partie 2 (révision)
    try:
        raux_p2 = await llm.generer_raux_p2(ref, raux_p1)
    except Exception as exc:
        logger.error("Erreur LLM lors de la génération du RAUX P2 : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service LLM indisponible — essayez de redémarrer le conteneur judi-llm",
        )

    # 10. Combiner RAUX P1 + P2
    raux = (
        "# RAUX — Rapport Auxiliaire\n\n"
        "## Partie 1 — Analyse des contestations\n\n"
        f"{raux_p1}\n\n"
        "## Partie 2 — Version révisée du REF\n\n"
        f"{raux_p2}"
    )

    # 11. Sauvegarder les fichiers
    step3_path = _step3_dir(dossier_id)
    os.makedirs(step3_path, exist_ok=True)

    ref_path = os.path.join(step3_path, "ref.md")
    raux_path = os.path.join(step3_path, "raux.md")

    with open(ref_path, "w", encoding="utf-8") as f:
        f.write(ref)
    with open(raux_path, "w", encoding="utf-8") as f:
        f.write(raux)

    # 12. Créer les entrées StepFile en base
    step = await _get_step(dossier_id, 3, db)

    db.add(StepFile(
        step_id=step.id,
        filename="ref.md",
        file_path=ref_path,
        file_type="ref",
        file_size=len(ref.encode("utf-8")),
    ))
    db.add(StepFile(
        step_id=step.id,
        filename="raux.md",
        file_path=raux_path,
        file_type="raux",
        file_size=len(raux.encode("utf-8")),
    ))

    # 13. Marquer step3 comme "réalisé"
    await workflow_engine.execute_step(dossier_id, 3, db)
    await db.commit()

    return Step3ExecuteResponse(ref=ref, raux=raux)


# ---- Step3 : GET /api/dossiers/{id}/step3/download/{doc_type} ------------

@router.get(
    "/{dossier_id}/step3/download/{doc_type}",
)
async def step3_download(
    dossier_id: int,
    doc_type: str,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Télécharge le REF ou le RAUX généré pour step3.

    Valide : Exigence 9.4
    """

    # Vérifier l'accès à l'étape
    await workflow_engine.require_step_access(dossier_id, 3, db)

    if doc_type not in ("ref", "raux"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Type de document invalide — utilisez 'ref' ou 'raux'",
        )

    file_path = os.path.join(_step3_dir(dossier_id), f"{doc_type}.md")
    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fichier {doc_type.upper()} non trouvé — lancez d'abord l'exécution du Step3",
        )

    return FileResponse(
        path=file_path,
        filename=f"{doc_type}.md",
        media_type="text/markdown",
    )


# ---- Step3 : POST /api/dossiers/{id}/step3/validate ---------------------

@router.post(
    "/{dossier_id}/step3/validate",
    response_model=Step3ValidateResponse,
)
async def step3_validate(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Valide le Step3, archive le dossier complet en ZIP.

    Valide : Exigences 9.5, 9.6
    """

    # 1. Valider step3 (cela archive aussi le dossier via WorkflowEngine)
    await workflow_engine.validate_step(dossier_id, 3, db)

    # 2. Créer l'archive ZIP du dossier complet
    dossier_path = _dossier_dir(dossier_id)
    archive_path = os.path.join(dossier_path, "archive.zip")

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(dossier_path):
            for filename in files:
                if filename == "archive.zip":
                    continue
                abs_path = os.path.join(root, filename)
                arc_name = os.path.relpath(abs_path, dossier_path)
                zf.write(abs_path, arc_name)

    # 3. Créer l'entrée StepFile pour l'archive
    step = await _get_step(dossier_id, 3, db)
    archive_size = os.path.getsize(archive_path)

    db.add(StepFile(
        step_id=step.id,
        filename="archive.zip",
        file_path=archive_path,
        file_type="archive",
        file_size=archive_size,
    ))

    await db.commit()

    return Step3ValidateResponse(message="Step3 validé — dossier archivé avec succès")
