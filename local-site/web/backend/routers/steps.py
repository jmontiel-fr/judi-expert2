"""Router des étapes du workflow d'expertise (Step1–Step5).

Valide : Exigences 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 7.1, 7.2, 7.3, 7.4,
         9.1, 9.2, 9.3, 9.4, 9.5, 9.6
"""

from __future__ import annotations

import logging
import os

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


class Step0ValidateResponse(BaseModel):
    message: str


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
    message: str
    filenames: list[str]


class Step3ValidateResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _step0_dir(dossier_id: int) -> str:
    """Retourne le chemin du répertoire step1 pour un dossier."""
    return os.path.join(DATA_DIR, "dossiers", str(dossier_id), "step1")


def _step1_dir(dossier_id: int) -> str:
    """Retourne le chemin du répertoire step2 pour un dossier."""
    return os.path.join(DATA_DIR, "dossiers", str(dossier_id), "step2")


def _step2_dir(dossier_id: int) -> str:
    """Retourne le chemin du répertoire step3 pour un dossier."""
    return os.path.join(DATA_DIR, "dossiers", str(dossier_id), "step3")


def _step3_dir(dossier_id: int) -> str:
    """Retourne le chemin du répertoire step4 pour un dossier."""
    return os.path.join(DATA_DIR, "dossiers", str(dossier_id), "step4")


def _step4_dir(dossier_id: int) -> str:
    """Retourne le chemin du répertoire step5 pour un dossier."""
    return os.path.join(DATA_DIR, "dossiers", str(dossier_id), "step5")


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

    # 0. Vérifier que l'étape n'est pas verrouillée (validée)
    await workflow_engine.require_step_not_validated(dossier_id, 1, db)

    # 0b. Marquer le step comme "en_cours"
    await workflow_engine.start_step(dossier_id, 1, db)
    await db.commit()

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
        await workflow_engine.fail_step(dossier_id, 1, db)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service LLM indisponible — essayez de redémarrer le conteneur judi-llm",
        )

    # 6b. Nettoyer le markdown (supprimer les blocs ``` ajoutés par le LLM)
    markdown = markdown.strip()
    if markdown.startswith("```markdown"):
        markdown = markdown[len("```markdown"):].strip()
    elif markdown.startswith("```md"):
        markdown = markdown[len("```md"):].strip()
    elif markdown.startswith("```"):
        markdown = markdown[3:].strip()
    if markdown.endswith("```"):
        markdown = markdown[:-3].strip()

    # 7. Sauvegarder le fichier Markdown (usage interne pour Step1)
    md_path = os.path.join(step_dir, "requisition.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    # 7b. Générer le .docx pour l'expert
    from docx import Document as DocxDocument
    docx_path = os.path.join(step_dir, "requisition.docx")
    doc = DocxDocument()
    for line in markdown.split("\n"):
        stripped = line.strip()
        if stripped.startswith("### "):
            doc.add_heading(stripped[4:], level=3)
        elif stripped.startswith("## "):
            doc.add_heading(stripped[3:], level=2)
        elif stripped.startswith("# "):
            doc.add_heading(stripped[2:], level=1)
        elif stripped.startswith("- "):
            doc.add_paragraph(stripped[2:], style="List Bullet")
        elif stripped:
            doc.add_paragraph(stripped)
    doc.save(docx_path)

    # 8. Créer les entrées StepFile en base
    step = await _get_step(dossier_id, 1, db)

    # Supprimer les anciens StepFile de step0 (ré-extraction)
    for old_file in list(step.files):
        await db.delete(old_file)
    await db.flush()

    pdf_size = len(pdf_content)
    md_size = len(markdown.encode("utf-8"))
    docx_size = os.path.getsize(docx_path)

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
    step_file_docx = StepFile(
        step_id=step.id,
        filename="requisition.docx",
        file_path=docx_path,
        file_type="docx",
        file_size=docx_size,
    )
    db.add(step_file_pdf)
    db.add(step_file_md)
    db.add(step_file_docx)

    # 9. Marquer step0 comme "fait"
    await workflow_engine.execute_step(dossier_id, 1, db)
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
    await workflow_engine.require_step_access(dossier_id, 1, db)

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
    await workflow_engine.require_step_not_validated(dossier_id, 1, db)

    md_path = os.path.join(_step0_dir(dossier_id), "requisition.md")
    if not os.path.isfile(md_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier Markdown non trouvé — lancez d'abord l'extraction",
        )

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(body.content)

    # Mettre à jour la taille du fichier dans StepFile
    step = await _get_step(dossier_id, 1, db)
    for sf in step.files:
        if sf.filename == "requisition.md":
            sf.file_size = len(body.content.encode("utf-8"))
            break

    await db.commit()

    return MarkdownUpdateResponse(message="Fichier Markdown mis à jour")


# ---- Step0 : POST /api/dossiers/{id}/step0/import-docx -------------------

@router.post(
    "/{dossier_id}/step0/import-docx",
    response_model=MarkdownUpdateResponse,
)
async def step0_import_docx(
    dossier_id: int,
    file: UploadFile,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Importe un .docx modifié par l'expert et met à jour le .md et le .docx."""
    from docx import Document as DocxDocument

    await workflow_engine.require_step_not_validated(dossier_id, 1, db)

    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seul le format .docx est accepté",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier est vide",
        )

    step_dir = _step0_dir(dossier_id)

    # Sauvegarder le .docx importé
    docx_path = os.path.join(step_dir, "requisition.docx")
    with open(docx_path, "wb") as f:
        f.write(content)

    # Extraire le texte du .docx pour mettre à jour le .md
    import io
    doc = DocxDocument(io.BytesIO(content))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    markdown = "\n\n".join(paragraphs)

    md_path = os.path.join(step_dir, "requisition.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    # Mettre à jour les tailles dans StepFile
    step = await _get_step(dossier_id, 1, db)
    for sf in step.files:
        if sf.filename == "requisition.md":
            sf.file_size = len(markdown.encode("utf-8"))
        elif sf.filename == "requisition.docx":
            sf.file_size = len(content)

    await db.commit()

    return MarkdownUpdateResponse(message="Document importé avec succès")


# ---- Step0 : POST /api/dossiers/{id}/step0/validate ---------------------

@router.post(
    "/{dossier_id}/step0/validate",
    response_model=Step0ValidateResponse,
)
async def step0_validate(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Valide l'étape 0 (extraction) — passage à "validé"."""

    await workflow_engine.validate_step(dossier_id, 1, db)
    await db.commit()

    return Step0ValidateResponse(message="Step0 validé avec succès")


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
    await workflow_engine.require_step_access(dossier_id, 2, db)

    # 1b. Marquer le step comme "en_cours"
    await workflow_engine.start_step(dossier_id, 2, db)
    await db.commit()

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
        await workflow_engine.fail_step(dossier_id, 2, db)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service LLM indisponible — essayez de redémarrer le conteneur judi-llm",
        )

    # 6b. Nettoyer le markdown
    qmec = qmec.strip()
    if qmec.startswith("```markdown"):
        qmec = qmec[len("```markdown"):].strip()
    elif qmec.startswith("```md"):
        qmec = qmec[len("```md"):].strip()
    elif qmec.startswith("```"):
        qmec = qmec[3:].strip()
    if qmec.endswith("```"):
        qmec = qmec[:-3].strip()

    # 7. Sauvegarder le QMEC en .md (interne) et .docx (pour l'expert)
    step1_path = _step1_dir(dossier_id)
    os.makedirs(step1_path, exist_ok=True)

    # .md interne
    qmec_md_path = os.path.join(step1_path, "qmec.md")
    with open(qmec_md_path, "w", encoding="utf-8") as f:
        f.write(qmec)

    # .docx pour l'expert
    from docx import Document as DocxDocument
    qmec_docx_path = os.path.join(step1_path, "qmec.docx")
    doc = DocxDocument()
    doc.add_heading("Plan d'entretien (QMEC)", level=1)
    for line in qmec.split("\n"):
        stripped = line.strip()
        if stripped.startswith("### "):
            doc.add_heading(stripped[4:], level=3)
        elif stripped.startswith("## "):
            doc.add_heading(stripped[3:], level=2)
        elif stripped.startswith("# "):
            doc.add_heading(stripped[2:], level=1)
        elif stripped.startswith("- "):
            doc.add_paragraph(stripped[2:], style="List Bullet")
        elif stripped:
            doc.add_paragraph(stripped)
    doc.save(qmec_docx_path)

    # 8. Créer les entrées StepFile en base
    step = await _get_step(dossier_id, 2, db)

    # Supprimer les anciens StepFile (ré-exécution)
    for old_file in list(step.files):
        await db.delete(old_file)
    await db.flush()

    step_file_md = StepFile(
        step_id=step.id,
        filename="qmec.md",
        file_path=qmec_md_path,
        file_type="qmec",
        file_size=len(qmec.encode("utf-8")),
    )
    step_file_docx = StepFile(
        step_id=step.id,
        filename="qmec.docx",
        file_path=qmec_docx_path,
        file_type="qmec_docx",
        file_size=os.path.getsize(qmec_docx_path),
    )
    db.add(step_file_md)
    db.add(step_file_docx)

    # 9. Marquer step1 comme "réalisé"
    await workflow_engine.execute_step(dossier_id, 2, db)
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
    await workflow_engine.require_step_access(dossier_id, 2, db)

    qmec_path = os.path.join(_step1_dir(dossier_id), "qmec.docx")
    if not os.path.isfile(qmec_path):
        # Fallback to .md for backward compatibility
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

    return FileResponse(
        path=qmec_path,
        filename="qmec.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
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

    await workflow_engine.validate_step(dossier_id, 2, db)
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
    file: UploadFile,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload du NEA (.docx) et génération du RE-Projet + RE-Projet-Auxiliaire.

    Valide : Exigences 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8
    """

    # 1. Vérifier l'accès au step2
    await workflow_engine.require_step_access(dossier_id, 4, db)

    # 1b. Marquer le step comme "en_cours"
    await workflow_engine.start_step(dossier_id, 4, db)
    await db.commit()

    # 2. Valider le format .docx
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seul le format .docx est accepté",
        )

    # 3. Lire le contenu du fichier NEA
    nea_content_bytes = await file.read()

    # 4. Créer le répertoire de destination
    step_dir = _step2_dir(dossier_id)
    os.makedirs(step_dir, exist_ok=True)

    # 5. Sauvegarder le NEA
    nea_path = os.path.join(step_dir, "nea.docx")
    with open(nea_path, "wb") as f:
        f.write(nea_content_bytes)

    # 6. Lire la réquisition Markdown de step0
    md_path = os.path.join(_step0_dir(dossier_id), "requisition.md")
    if not os.path.isfile(md_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier Markdown de la réquisition non trouvé — complétez d'abord le Step0",
        )
    with open(md_path, "r", encoding="utf-8") as f:
        requisition_md = f.read()

    # 7. Récupérer le domaine depuis LocalConfig
    result = await db.execute(select(LocalConfig).limit(1))
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration initiale non effectuée",
        )
    domaine = config.domaine

    # 8. Récupérer le Template Rapport depuis la base RAG
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

    # 9. Générer le RE-Projet via LLM
    nea_text = nea_content_bytes.decode("utf-8", errors="replace")

    llm = LLMService()
    try:
        re_projet_content = await llm.generer_re_projet(
            nea_text, requisition_md, template
        )
    except Exception as exc:
        logger.error("Erreur LLM lors de la génération du RE-Projet : %s", exc)
        await workflow_engine.fail_step(dossier_id, 4, db)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service LLM indisponible — essayez de redémarrer le conteneur judi-llm",
        )

    # 10. Générer le RE-Projet-Auxiliaire via LLM
    try:
        re_projet_aux_content = await llm.generer_re_projet_auxiliaire(
            nea_text, re_projet_content
        )
    except Exception as exc:
        logger.error("Erreur LLM lors de la génération du RE-Projet-Auxiliaire : %s", exc)
        await workflow_engine.fail_step(dossier_id, 4, db)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service LLM indisponible — essayez de redémarrer le conteneur judi-llm",
        )

    # 11. Sauvegarder le NEA en base (visible immédiatement par le polling)
    step = await _get_step(dossier_id, 4, db)

    # Supprimer les anciens StepFile (ré-exécution)
    for old_file in list(step.files):
        await db.delete(old_file)
    await db.flush()

    db.add(StepFile(
        step_id=step.id,
        filename="nea.docx",
        file_path=nea_path,
        file_type="nea",
        file_size=len(nea_content_bytes),
    ))
    await db.commit()

    # 12. Sauvegarder le RE-Projet
    re_projet_bytes = re_projet_content.encode("utf-8")
    re_projet_path = os.path.join(step_dir, "re_projet.docx")
    with open(re_projet_path, "wb") as f:
        f.write(re_projet_bytes)

    db.add(StepFile(
        step_id=step.id,
        filename="re_projet.docx",
        file_path=re_projet_path,
        file_type="re_projet",
        file_size=len(re_projet_bytes),
    ))
    await db.commit()

    # 13. Sauvegarder le RE-Projet-Auxiliaire
    re_projet_aux_bytes = re_projet_aux_content.encode("utf-8")
    re_projet_aux_path = os.path.join(step_dir, "re_projet_auxiliaire.docx")
    with open(re_projet_aux_path, "wb") as f:
        f.write(re_projet_aux_bytes)

    db.add(StepFile(
        step_id=step.id,
        filename="re_projet_auxiliaire.docx",
        file_path=re_projet_aux_path,
        file_type="re_projet_auxiliaire",
        file_size=len(re_projet_aux_bytes),
    ))

    # 14. Marquer step2 comme "fait"
    await workflow_engine.execute_step(dossier_id, 4, db)
    await db.commit()

    return Step2UploadResponse(
        message="NEA uploadé — RE-Projet et RE-Projet-Auxiliaire générés avec succès",
        filenames=["nea.docx", "re_projet.docx", "re_projet_auxiliaire.docx"],
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

    await workflow_engine.validate_step(dossier_id, 4, db)
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
    file: UploadFile = None,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload du ProjetFinal, génération de l'archive ZIP et du hash.

    Étape 1/3 : Génération du ZIP (Expert/ + IA/)
    Étape 2/3 : Génération du hash SHA-256
    Étape 3/3 : Stockage du hash (S3 en prod)
    """
    import hashlib
    import io
    import zipfile

    # 1. Vérifier l'accès au step3
    await workflow_engine.require_step_access(dossier_id, 5, db)

    # 1b. Marquer le step comme "en_cours"
    await workflow_engine.start_step(dossier_id, 5, db)
    await db.commit()

    step3_path = _step3_dir(dossier_id)
    os.makedirs(step3_path, exist_ok=True)

    # 2. Sauvegarder le ProjetFinal uploadé (optionnel)
    if file and file.filename:
        projet_final_bytes = await file.read()
        projet_final_path = os.path.join(step3_path, "projet_final.docx")
        with open(projet_final_path, "wb") as f:
            f.write(projet_final_bytes)

    # 3. Construire le ZIP avec tous les fichiers classés Expert/ et IA/
    dossier_root = _dossier_dir(dossier_id)
    zip_buffer = io.BytesIO()

    # Mapping des fichiers vers Expert/ ou IA/
    expert_files = {
        "step0/requisition.pdf": "Expert/requisition.pdf",
        "step0/requisition.docx": "Expert/requisition_modifiee.docx",
        "step2/nea.docx": "Expert/nea.docx",
        "step3/projet_final.docx": "Expert/projet_final.docx",
    }
    ia_files = {
        "step0/requisition.md": "IA/requisition_structuree.md",
        "step1/qmec.md": "IA/qmec.md",
        "step1/qmec.docx": "IA/qmec.docx",
        "step2/re_projet.docx": "IA/re_projet.docx",
        "step2/re_projet_auxiliaire.docx": "IA/re_projet_auxiliaire.docx",
    }

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for src_rel, arc_name in {**expert_files, **ia_files}.items():
            src_path = os.path.join(dossier_root, src_rel)
            if os.path.isfile(src_path):
                zf.write(src_path, arc_name)

    zip_bytes = zip_buffer.getvalue()
    zip_path = os.path.join(step3_path, "dossier_archive.zip")
    with open(zip_path, "wb") as f:
        f.write(zip_bytes)

    # 4. Générer le hash SHA-256 du ZIP
    sha256_hash = hashlib.sha256(zip_bytes).hexdigest()
    hash_path = os.path.join(step3_path, "hash_sha256.txt")
    with open(hash_path, "w") as f:
        f.write(f"SHA-256: {sha256_hash}\n")
        f.write(f"Fichier: dossier_archive.zip\n")
        f.write(f"Dossier: {dossier_id}\n")

    # 5. TODO (prod) : Stocker le hash sur S3 expert(xxx/dossierxxx/hash-dossier)
    logger.info("Hash SHA-256 dossier %s : %s", dossier_id, sha256_hash)

    # 6. Créer les entrées StepFile en base
    step = await _get_step(dossier_id, 5, db)

    # Supprimer les anciens StepFile
    for old_file in list(step.files):
        await db.delete(old_file)
    await db.flush()

    if file and file.filename:
        db.add(StepFile(
            step_id=step.id,
            filename="projet_final.docx",
            file_path=os.path.join(step3_path, "projet_final.docx"),
            file_type="projet_final",
            file_size=len(projet_final_bytes),
        ))

    db.add(StepFile(
        step_id=step.id,
        filename="dossier_archive.zip",
        file_path=zip_path,
        file_type="archive_zip",
        file_size=len(zip_bytes),
    ))
    db.add(StepFile(
        step_id=step.id,
        filename="hash_sha256.txt",
        file_path=hash_path,
        file_type="hash",
        file_size=os.path.getsize(hash_path),
    ))

    # 7. Marquer step3 comme "fait"
    await workflow_engine.execute_step(dossier_id, 5, db)
    await db.commit()

    return Step3ExecuteResponse(
        message=f"Archive générée — Hash SHA-256 : {sha256_hash}",
        filenames=["projet_final.docx", "dossier_archive.zip", "hash_sha256.txt"],
    )


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
    """Télécharge le REF-Projet généré pour step3.

    Valide : Exigence 4.4
    """

    # Vérifier l'accès à l'étape
    await workflow_engine.require_step_access(dossier_id, 5, db)

    if doc_type != "ref_projet":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Type de document invalide — utilisez 'ref_projet'",
        )

    file_path = os.path.join(_step3_dir(dossier_id), "ref_projet.docx")
    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier REF-Projet non trouvé — lancez d'abord l'exécution du Step3",
        )

    return FileResponse(
        path=file_path,
        filename="ref_projet.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
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
    """Valide le Step3 (verrouillage).

    Valide : Exigences 9.5, 9.6
    """

    await workflow_engine.validate_step(dossier_id, 5, db)
    await db.commit()

    return Step3ValidateResponse(message="Step3 validé avec succès")
