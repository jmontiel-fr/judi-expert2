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


async def _get_dossier_name(dossier_id: int, db: AsyncSession) -> str:
    """Récupère le nom du dossier par son ID."""
    from models.dossier import Dossier as DossierModel
    result = await db.execute(select(DossierModel).where(DossierModel.id == dossier_id))
    dossier = result.scalar_one_or_none()
    if dossier is None:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")
    return dossier.nom


def _step_in(dossier_name: str, step_number: int) -> str:
    """Retourne le chemin du sous-dossier d'entrée d'un step."""
    from services.file_paths import step_in_dir
    return step_in_dir(dossier_name, step_number)


def _step_out(dossier_name: str, step_number: int) -> str:
    """Retourne le chemin du sous-dossier de sortie d'un step."""
    from services.file_paths import step_out_dir
    return step_out_dir(dossier_name, step_number)


def _dossier_dir(dossier_name: str) -> str:
    """Retourne le chemin du répertoire racine d'un dossier."""
    from services.file_paths import dossier_root
    return dossier_root(dossier_name)


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


# ---- Step1 : POST /api/dossiers/{id}/step1/upload -------------------------


class UploadResponse(BaseModel):
    message: str
    filename: str
    file_size: int


@router.post(
    "/{dossier_id}/step1/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def step1_upload(
    dossier_id: int,
    file: UploadFile,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload l'ordonnance PDF dans step1/in/ sans lancer de traitement."""

    # Vérifier que l'étape n'est pas verrouillée
    await workflow_engine.require_step_not_validated(dossier_id, 1, db)

    # Vérifier que le fichier est un PDF
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seuls les fichiers PDF sont acceptés",
        )

    # Lire le contenu
    pdf_content = await file.read()
    if not pdf_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier PDF est vide",
        )

    # Résoudre le nom du dossier et sauvegarder
    dossier_name = await _get_dossier_name(dossier_id, db)
    in_dir = _step_in(dossier_name, 1)
    os.makedirs(in_dir, exist_ok=True)

    pdf_path = os.path.join(in_dir, "ordonnance.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_content)

    # Créer le StepFile en base
    step = await _get_step(dossier_id, 1, db)

    # Supprimer l'ancien fichier ordonnance s'il existe (ré-upload)
    for old_file in list(step.files):
        if old_file.filename == "ordonnance.pdf":
            await db.delete(old_file)
    await db.flush()

    step_file = StepFile(
        step_id=step.id,
        filename="ordonnance.pdf",
        file_path=pdf_path,
        file_type="pdf_scan",
        file_size=len(pdf_content),
    )
    db.add(step_file)
    await db.commit()

    return UploadResponse(
        message="Ordonnance importée avec succès",
        filename="ordonnance.pdf",
        file_size=len(pdf_content),
    )


# ---- Step1 : POST /api/dossiers/{id}/step1/execute -----------------------

@router.post(
    "/{dossier_id}/step1/execute",
    response_model=ExtractResponse,
    status_code=status.HTTP_201_CREATED,
)
async def step1_execute(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lance l'OCR + structuration LLM sur les fichiers déjà uploadés dans step1/in/.

    Produit : ordonnance.md, questions.md, place_holders.csv dans step1/out/.
    """

    # 0. Vérifier que l'étape n'est pas verrouillée
    await workflow_engine.require_step_not_validated(dossier_id, 1, db)

    # 0b. Vérifier que le step n'est pas déjà en cours (éviter re-lancement sur refresh)
    step = await _get_step(dossier_id, 1, db)
    if step.statut == "en_cours":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Le traitement est déjà en cours",
        )

    # 0c. Vérifier qu'il y a au moins un fichier uploadé
    dossier_name = await _get_dossier_name(dossier_id, db)
    in_dir = _step_in(dossier_name, 1)
    out_dir = _step_out(dossier_name, 1)

    pdf_path = os.path.join(in_dir, "ordonnance.pdf")
    if not os.path.isfile(pdf_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucune ordonnance uploadée — importez d'abord le PDF",
        )

    # 1. Marquer le step comme "en_cours"
    await workflow_engine.start_step(dossier_id, 1, db)
    await db.commit()

    # 2. Lire le PDF
    with open(pdf_path, "rb") as f:
        pdf_content = f.read()

    # 3. Appeler le service OCR
    logger.info("[Step1] Dossier %d — Phase 1/3 : OCR en cours…", dossier_id)
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OCR_HOST}/api/ocr/extract",
                files={"file": ("ordonnance.pdf", pdf_content, "application/pdf")},
            )
            resp.raise_for_status()
            ocr_data = resp.json()
            texte_brut = ocr_data.get("text", "")
    except httpx.ConnectError:
        await workflow_engine.fail_step(dossier_id, 1, db)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service OCR indisponible — vérifiez que le conteneur judi-ocr est démarré",
        )
    except httpx.TimeoutException:
        await workflow_engine.fail_step(dossier_id, 1, db)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service OCR indisponible — délai de connexion dépassé",
        )
    except httpx.HTTPStatusError as exc:
        logger.error("Erreur OCR HTTP %s", exc.response.status_code)
        await workflow_engine.fail_step(dossier_id, 1, db)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erreur du service OCR lors de l'extraction",
        )

    if not texte_brut.strip():
        await workflow_engine.fail_step(dossier_id, 1, db)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le PDF ne contient pas de texte exploitable",
        )

    # 3b. Vérifier si l'opération a été annulée entre OCR et LLM
    step_check = await _get_step(dossier_id, 1, db)
    if step_check.statut != "en_cours":
        logger.info("Step 1 annulé après OCR — abandon du traitement")
        return ExtractResponse(markdown="", pdf_path=pdf_path, md_path="")

    # 4. Appeler le LLM pour structurer en Markdown
    logger.info("[Step1] Dossier %d — Phase 2/3 : Structuration ordonnance (LLM)…", dossier_id)
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

    # 4b. Vérifier si l'opération a été annulée pendant le LLM
    await db.refresh(step_check)
    if step_check.statut != "en_cours":
        logger.info("Step 1 annulé après LLM — abandon du traitement")
        return ExtractResponse(markdown="", pdf_path=pdf_path, md_path="")

    # 4b. Nettoyer le markdown (supprimer les blocs ``` ajoutés par le LLM)
    markdown = markdown.strip()
    if markdown.startswith("```markdown"):
        markdown = markdown[len("```markdown"):].strip()
    elif markdown.startswith("```md"):
        markdown = markdown[len("```md"):].strip()
    elif markdown.startswith("```"):
        markdown = markdown[3:].strip()
    if markdown.endswith("```"):
        markdown = markdown[:-3].strip()

    # 5. Sauvegarder les fichiers de sortie
    os.makedirs(out_dir, exist_ok=True)

    md_path = os.path.join(out_dir, "ordonnance.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    # 5b. Vérifier annulation avant extraction des questions
    step_check = await _get_step(dossier_id, 1, db)
    if step_check.statut != "en_cours":
        logger.info("Step 1 annulé avant extraction questions — abandon")
        return ExtractResponse(markdown=markdown, pdf_path=pdf_path, md_path=md_path)

    # 6. Extraire les questions du tribunal
    logger.info("[Step1] Dossier %d — Phase 3a/3 : Extraction des questions (LLM)…", dossier_id)
    try:
        questions_md = await llm.extraire_questions(markdown)
    except Exception as exc:
        logger.warning("Extraction questions échouée : %s — on continue sans", exc)
        questions_md = ""

    # Nettoyer le markdown des questions
    if questions_md:
        questions_md = questions_md.strip()
        if questions_md.startswith("```"):
            questions_md = questions_md.split("\n", 1)[-1] if "\n" in questions_md else ""
        if questions_md.endswith("```"):
            questions_md = questions_md[:-3].strip()

    questions_path = ""
    if questions_md.strip():
        questions_path = os.path.join(out_dir, "questions.md")
        with open(questions_path, "w", encoding="utf-8") as f:
            f.write(questions_md)

    # 6b. Vérifier annulation avant extraction des placeholders
    await db.refresh(step_check)
    if step_check.statut != "en_cours":
        logger.info("Step 1 annulé avant extraction placeholders — abandon")
        return ExtractResponse(markdown=markdown, pdf_path=pdf_path, md_path=md_path)

    # 7. Extraire les placeholders
    logger.info("[Step1] Dossier %d — Phase 3b/3 : Extraction des placeholders (LLM)…", dossier_id)
    try:
        placeholders_csv = await llm.extraire_placeholders(markdown)
    except Exception as exc:
        logger.warning("Extraction placeholders échouée : %s — on continue sans", exc)
        placeholders_csv = ""

    # Nettoyer le CSV
    if placeholders_csv:
        placeholders_csv = placeholders_csv.strip()
        if placeholders_csv.startswith("```"):
            placeholders_csv = placeholders_csv.split("\n", 1)[-1] if "\n" in placeholders_csv else ""
        if placeholders_csv.endswith("```"):
            placeholders_csv = placeholders_csv[:-3].strip()

    placeholders_path = ""
    if placeholders_csv.strip():
        placeholders_path = os.path.join(out_dir, "place_holders.csv")
        with open(placeholders_path, "w", encoding="utf-8") as f:
            f.write(placeholders_csv)

    # 8. Créer les entrées StepFile de sortie en base
    step = await _get_step(dossier_id, 1, db)

    # Supprimer les anciens fichiers de sortie (ré-exécution)
    for old_file in list(step.files):
        if old_file.file_type in ("markdown", "questions", "placeholders"):
            await db.delete(old_file)
    await db.flush()

    md_size = len(markdown.encode("utf-8"))
    step_file_md = StepFile(
        step_id=step.id,
        filename="ordonnance.md",
        file_path=md_path,
        file_type="markdown",
        file_size=md_size,
    )
    db.add(step_file_md)

    if questions_path:
        db.add(StepFile(
            step_id=step.id,
            filename="questions.md",
            file_path=questions_path,
            file_type="questions",
            file_size=len(questions_md.encode("utf-8")),
        ))

    if placeholders_path:
        db.add(StepFile(
            step_id=step.id,
            filename="place_holders.csv",
            file_path=placeholders_path,
            file_type="placeholders",
            file_size=len(placeholders_csv.encode("utf-8")),
        ))

    # 9. Marquer step1 comme "fait"
    logger.info("[Step1] Dossier %d — Terminé. Fichiers générés : ordonnance.md%s%s",
                dossier_id,
                ", questions.md" if questions_path else "",
                ", place_holders.csv" if placeholders_path else "")
    await workflow_engine.execute_step(dossier_id, 1, db)
    await db.commit()

    return ExtractResponse(
        markdown=markdown,
        pdf_path=pdf_path,
        md_path=md_path,
    )


# ---- Step1 : POST /api/dossiers/{id}/step1/extract (legacy — redirige) ---

@router.post(
    "/{dossier_id}/step1/extract",
    response_model=ExtractResponse,
    status_code=status.HTTP_201_CREATED,
    deprecated=True,
)
async def step0_extract(
    dossier_id: int,
    file: UploadFile,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """[LEGACY] Upload + extraction en un seul appel. Utiliser /upload puis /execute."""
    # Upload d'abord
    await step1_upload.__wrapped__(dossier_id, file, _user, db) if hasattr(step1_upload, '__wrapped__') else None

    # Sauvegarder le fichier manuellement (fallback si __wrapped__ n'existe pas)
    dossier_name = await _get_dossier_name(dossier_id, db)
    in_dir = _step_in(dossier_name, 1)
    os.makedirs(in_dir, exist_ok=True)

    pdf_content = await file.read()
    if not pdf_content:
        # Le fichier a déjà été lu par step1_upload, relire depuis le disque
        pdf_path = os.path.join(in_dir, "ordonnance.pdf")
        if os.path.isfile(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_content = f.read()

    if not pdf_content:
        raise HTTPException(status_code=400, detail="Fichier vide")

    # Puis exécuter
    return await step1_execute(dossier_id, _user, db)


# ---- Step1 : GET /api/dossiers/{id}/step1/markdown -----------------------

@router.get(
    "/{dossier_id}/step1/markdown",
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

    dossier_name = await _get_dossier_name(dossier_id, db)
    md_path = os.path.join(_step_out(dossier_name, 1), "requisition.md")
    if not os.path.isfile(md_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier Markdown non trouvé — lancez d'abord l'extraction",
        )

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    return MarkdownResponse(markdown=content)


# ---- Step1 : PUT /api/dossiers/{id}/step1/markdown -----------------------

@router.put(
    "/{dossier_id}/step1/markdown",
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

    dossier_name = await _get_dossier_name(dossier_id, db)
    md_path = os.path.join(_step_out(dossier_name, 1), "requisition.md")
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


# ---- Step1 : POST /api/dossiers/{id}/step1/import-docx -------------------

@router.post(
    "/{dossier_id}/step1/import-docx",
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

    dossier_name = await _get_dossier_name(dossier_id, db)
    in_dir = _step_in(dossier_name, 1)
    out_dir = _step_out(dossier_name, 1)

    # Sauvegarder le .docx importé (input — uploadé par l'expert)
    docx_path = os.path.join(in_dir, "requisition.docx")
    with open(docx_path, "wb") as f:
        f.write(content)

    # Extraire le texte du .docx pour mettre à jour le .md (output)
    import io
    doc = DocxDocument(io.BytesIO(content))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    markdown = "\n\n".join(paragraphs)

    md_path = os.path.join(out_dir, "requisition.md")
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


# ---- Step1 : POST /api/dossiers/{id}/step1/complementary -----------------

# Types de pièces complémentaires
VALID_DOC_TYPES = ("rapport", "plainte", "autre")
# Formats acceptés et ceux qui passent à l'OCR
VALID_DOC_FORMATS = ("pdf", "scan", "image", "csv", "xlsx")
OCR_FORMATS = ("pdf", "scan")


class ComplementaryResponse(BaseModel):
    message: str
    filename: str
    ocr_applied: bool
    output_file: str | None = None


@router.post(
    "/{dossier_id}/step1/complementary",
    response_model=ComplementaryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def step1_upload_complementary(
    dossier_id: int,
    file: UploadFile,
    label: str = "",
    doc_type: str = "autre",
    doc_format: str = "pdf",
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload une pièce complémentaire au dossier (Step 1).

    - type : rapport, plainte, autre
    - format : pdf, scan, image, csv, xlsx
    - Seuls les formats pdf et scan passent à l'OCR → produisent un .md
    - Les formats csv et xlsx sont stockés tels quels
    """
    # Validation
    if doc_type not in VALID_DOC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Type invalide. Valeurs acceptées : {', '.join(VALID_DOC_TYPES)}",
        )
    if doc_format not in VALID_DOC_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Format invalide. Valeurs acceptées : {', '.join(VALID_DOC_FORMATS)}",
        )

    # Vérifier que l'étape n'est pas verrouillée
    await workflow_engine.require_step_not_validated(dossier_id, 1, db)

    # Lire le fichier
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier est vide",
        )

    # Créer le répertoire
    dossier_name = await _get_dossier_name(dossier_id, db)
    in_dir = _step_in(dossier_name, 1)
    out_dir = _step_out(dossier_name, 1)
    os.makedirs(in_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    # Sauvegarder le fichier original (input — uploadé par l'expert)
    safe_filename = file.filename or f"piece_{doc_type}.{doc_format}"
    file_path = os.path.join(in_dir, safe_filename)
    with open(file_path, "wb") as f:
        f.write(content)

    # OCR si format pdf ou scan
    ocr_applied = False
    output_file = None

    if doc_format in OCR_FORMATS:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{OCR_HOST}/api/ocr/extract",
                    files={"file": (safe_filename, content, "application/pdf")},
                )
                resp.raise_for_status()
                ocr_data = resp.json()
                texte_brut = ocr_data.get("text", "")

            if texte_brut.strip():
                # Sauvegarder le résultat OCR en .md (output — généré par OCR)
                md_filename = os.path.splitext(safe_filename)[0] + ".md"
                md_path = os.path.join(out_dir, md_filename)
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(texte_brut)
                ocr_applied = True
                output_file = md_filename

                # Créer le StepFile pour le .md
                step = await _get_step(dossier_id, 1, db)
                md_step_file = StepFile(
                    step_id=step.id,
                    filename=md_filename,
                    file_path=md_path,
                    file_type="complementary_ocr",
                    file_size=len(texte_brut.encode("utf-8")),
                    doc_type=doc_type,
                    doc_format=doc_format,
                )
                db.add(md_step_file)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
            logger.warning("OCR indisponible pour pièce complémentaire : %s", e)

    # Créer le StepFile pour le fichier original
    step = await _get_step(dossier_id, 1, db)
    step_file = StepFile(
        step_id=step.id,
        filename=safe_filename,
        file_path=file_path,
        file_type="complementary",
        file_size=len(content),
        doc_type=doc_type,
        doc_format=doc_format,
    )
    db.add(step_file)
    await db.commit()

    return ComplementaryResponse(
        message=f"Pièce complémentaire '{label or safe_filename}' ajoutée.",
        filename=safe_filename,
        ocr_applied=ocr_applied,
        output_file=output_file,
    )


# ---- Step1 : POST /api/dossiers/{id}/step1/validate ---------------------

@router.post(
    "/{dossier_id}/step1/validate",
    response_model=Step0ValidateResponse,
)
async def step1_validate(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Valide l'étape 1 (extraction) — passage à "validé"."""

    await workflow_engine.validate_step(dossier_id, 1, db)
    await db.commit()

    return Step0ValidateResponse(message="Step 1 validé avec succès")


# ---- Step2 : POST /api/dossiers/{id}/step2/execute -----------------------

@router.post(
    "/{dossier_id}/step2/execute",
    response_model=QmecResponse,
    status_code=status.HTTP_201_CREATED,
)
async def step2_execute(
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

    # Résoudre le nom du dossier pour les chemins
    dossier_name = await _get_dossier_name(dossier_id, db)

    # 2. Lire le fichier Markdown de step0 pour obtenir les QT
    md_path = os.path.join(_step_out(dossier_name, 1), "requisition.md")
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

    # 7. Sauvegarder le PE en .md (interne) et .docx (pour l'expert)
    step2_out = _step_out(dossier_name, 2)
    os.makedirs(step2_out, exist_ok=True)

    # .md interne
    pe_md_path = os.path.join(step2_out, "pe.md")
    with open(pe_md_path, "w", encoding="utf-8") as f:
        f.write(qmec)

    # .docx pour l'expert
    from docx import Document as DocxDocument
    pe_docx_path = os.path.join(step2_out, "pe.docx")
    doc = DocxDocument()
    doc.add_heading("Plan d'Entretien (PE)", level=1)
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
    doc.save(pe_docx_path)

    # 8. Créer les entrées StepFile en base
    step = await _get_step(dossier_id, 2, db)

    # Supprimer les anciens StepFile (ré-exécution)
    for old_file in list(step.files):
        await db.delete(old_file)
    await db.flush()

    step_file_md = StepFile(
        step_id=step.id,
        filename="pe.md",
        file_path=pe_md_path,
        file_type="plan_entretien",
        file_size=len(qmec.encode("utf-8")),
    )
    step_file_docx = StepFile(
        step_id=step.id,
        filename="pe.docx",
        file_path=pe_docx_path,
        file_type="plan_entretien_docx",
        file_size=os.path.getsize(pe_docx_path),
    )
    db.add(step_file_md)
    db.add(step_file_docx)

    # 9. Marquer step1 comme "réalisé"
    await workflow_engine.execute_step(dossier_id, 2, db)
    await db.commit()

    return QmecResponse(qmec=qmec)


# ---- Step2 : GET /api/dossiers/{id}/step2/download -----------------------

@router.get(
    "/{dossier_id}/step2/download",
)
async def step2_download(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Télécharge le fichier QMEC généré pour step1.

    Valide : Exigence 7.3
    """

    # Vérifier l'accès à l'étape
    await workflow_engine.require_step_access(dossier_id, 2, db)

    dossier_name = await _get_dossier_name(dossier_id, db)
    step2_out = _step_out(dossier_name, 2)

    pe_path = os.path.join(step2_out, "pe.docx")
    if not os.path.isfile(pe_path):
        # Fallback to .md
        pe_path = os.path.join(step2_out, "pe.md")
        if not os.path.isfile(pe_path):
            # Legacy fallback
            pe_path = os.path.join(step2_out, "qmec.docx")
            if not os.path.isfile(pe_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Plan d'Entretien non trouvé — lancez d'abord l'exécution du Step 2",
                )
        return FileResponse(
            path=pe_path,
            filename="pe.md",
            media_type="text/markdown",
        )

    return FileResponse(
        path=pe_path,
        filename="pe.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# ---- Step2 : POST /api/dossiers/{id}/step2/validate ---------------------

@router.post(
    "/{dossier_id}/step2/validate",
    response_model=Step1ValidateResponse,
)
async def step2_validate(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Valide le Step 2 (verrouillage) et autorise l'accès au Step 3.

    Valide : Exigence 7.4
    """

    await workflow_engine.validate_step(dossier_id, 2, db)
    await db.commit()

    return Step1ValidateResponse(message="Step 2 validé avec succès")


# ---- Step4 : POST /api/dossiers/{id}/step4/execute ------------------------

@router.post(
    "/{dossier_id}/step4/execute",
    response_model=Step2UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def step4_execute(
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

    # Résoudre le nom du dossier pour les chemins
    dossier_name = await _get_dossier_name(dossier_id, db)

    # 4. Créer le répertoire de destination
    in_dir = _step_in(dossier_name, 3)
    out_dir = _step_out(dossier_name, 3)
    os.makedirs(in_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    # 5. Sauvegarder le NEA (input — uploadé par l'expert)
    nea_path = os.path.join(in_dir, "nea.docx")
    with open(nea_path, "wb") as f:
        f.write(nea_content_bytes)

    # 6. Lire la réquisition Markdown de step0 (output du step1)
    md_path = os.path.join(_step_out(dossier_name, 1), "requisition.md")
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

    # 12. Sauvegarder le RE-Projet (output — généré par LLM)
    re_projet_bytes = re_projet_content.encode("utf-8")
    re_projet_path = os.path.join(out_dir, "re_projet.docx")
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

    # 13. Sauvegarder le RE-Projet-Auxiliaire (output — généré par LLM)
    re_projet_aux_bytes = re_projet_aux_content.encode("utf-8")
    re_projet_aux_path = os.path.join(out_dir, "re_projet_auxiliaire.docx")
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


# ---- Step4 : POST /api/dossiers/{id}/step4/validate ---------------------

@router.post(
    "/{dossier_id}/step4/validate",
    response_model=Step2ValidateResponse,
)
async def step4_validate(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Valide le Step 4 (verrouillage) et autorise l'accès au Step 5.

    Valide : Exigence 8.4
    """

    await workflow_engine.validate_step(dossier_id, 4, db)
    await db.commit()

    return Step2ValidateResponse(message="Step 4 validé avec succès")


# ---- Step5 : POST /api/dossiers/{id}/step5/execute -----------------------

@router.post(
    "/{dossier_id}/step5/execute",
    response_model=Step3ExecuteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def step5_execute(
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

    # Résoudre le nom du dossier pour les chemins
    dossier_name = await _get_dossier_name(dossier_id, db)

    in_dir = _step_in(dossier_name, 5)
    out_dir = _step_out(dossier_name, 5)
    os.makedirs(in_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    # 2. Sauvegarder le ProjetFinal uploadé (optionnel — input)
    if file and file.filename:
        projet_final_bytes = await file.read()
        projet_final_path = os.path.join(in_dir, "projet_final.docx")
        with open(projet_final_path, "wb") as f:
            f.write(projet_final_bytes)

    # 3. Construire le ZIP avec tous les fichiers classés Expert/ et IA/
    dossier_root = _dossier_dir(dossier_name)
    zip_buffer = io.BytesIO()

    # Mapping des fichiers vers Expert/ ou IA/
    expert_files = {
        "step1/in/requisition.pdf": "Expert/requisition.pdf",
        "step1/in/requisition.docx": "Expert/requisition_modifiee.docx",
        "step3/in/nea.docx": "Expert/nea.docx",
        "step5/in/projet_final.docx": "Expert/projet_final.docx",
    }
    ia_files = {
        "step1/out/requisition.md": "IA/requisition_structuree.md",
        "step2/out/pe.md": "IA/qmec.md",
        "step2/out/pe.docx": "IA/qmec.docx",
        "step3/out/re_projet.docx": "IA/re_projet.docx",
        "step3/out/re_projet_auxiliaire.docx": "IA/re_projet_auxiliaire.docx",
    }

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for src_rel, arc_name in {**expert_files, **ia_files}.items():
            src_path = os.path.join(dossier_root, src_rel)
            if os.path.isfile(src_path):
                zf.write(src_path, arc_name)

    zip_bytes = zip_buffer.getvalue()
    zip_path = os.path.join(out_dir, "dossier_archive.zip")
    with open(zip_path, "wb") as f:
        f.write(zip_bytes)

    # 4. Générer le hash SHA-256 du ZIP
    sha256_hash = hashlib.sha256(zip_bytes).hexdigest()
    hash_path = os.path.join(out_dir, "hash_sha256.txt")
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
            file_path=os.path.join(in_dir, "projet_final.docx"),
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


# ---- Step5 : GET /api/dossiers/{id}/step5/download/{doc_type} ------------

@router.get(
    "/{dossier_id}/step5/download/{doc_type}",
)
async def step5_download(
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

    dossier_name = await _get_dossier_name(dossier_id, db)
    file_path = os.path.join(_step_out(dossier_name, 5), "ref_projet.docx")
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


# ---- Step5 : POST /api/dossiers/{id}/step5/validate ---------------------

@router.post(
    "/{dossier_id}/step5/validate",
    response_model=Step3ValidateResponse,
)
async def step5_validate(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Valide le Step 5 (verrouillage).

    Valide : Exigences 9.5, 9.6
    """

    await workflow_engine.validate_step(dossier_id, 5, db)
    await db.commit()

    return Step3ValidateResponse(message="Step 5 validé avec succès")
