"""Router de gestion des dossiers d'expertise.

Valide : Exigences 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7
"""

from __future__ import annotations

import io
import logging
import os
import zipfile
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models.dossier import Dossier
from models.local_config import LocalConfig
from models.step import Step
from models.step_file import StepFile
from routers.auth import get_current_user
from services.file_service import FileService
from services.site_central_client import SiteCentralClient, SiteCentralError
from services.workflow_engine import (
    DOSSIER_ACTIF,
    DOSSIER_FERME,
    STATUT_VALIDE,
    workflow_engine,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR: str = os.environ.get("DATA_DIR", "data")

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class DossierListItem(BaseModel):
    id: int
    nom: str
    ticket_id: str
    domaine: str
    statut: str
    created_at: datetime


class DossierListResponse(BaseModel):
    dossiers: list[DossierListItem]


class DossierCreateRequest(BaseModel):
    nom: str = Field(..., min_length=1, description="Nom du dossier")
    ticket_id: str = Field(..., min_length=1, description="Code du ticket")


class StepItem(BaseModel):
    step_number: int
    statut: str
    executed_at: datetime | None = None
    validated_at: datetime | None = None
    files: list["StepFileItem"] = []


class DossierDetailResponse(BaseModel):
    id: int
    nom: str
    ticket_id: str
    domaine: str
    statut: str
    created_at: datetime
    updated_at: datetime
    steps: list[StepItem]


class StepFileItem(BaseModel):
    id: int
    filename: str
    file_path: str
    file_type: str
    file_size: int
    created_at: datetime
    is_modified: bool
    original_file_path: str | None
    updated_at: datetime | None


class StepDetailResponse(BaseModel):
    id: int
    step_number: int
    statut: str
    executed_at: datetime | None = None
    validated_at: datetime | None = None
    files: list[StepFileItem]


class DossierCloseResponse(BaseModel):
    message: str


class DossierArchiveResponse(BaseModel):
    message: str


class DossierResetAllResponse(BaseModel):
    message: str


class StepResetResponse(BaseModel):
    message: str


class FileDownloadInfo(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int


class FileReplaceResponse(BaseModel):
    message: str
    new_size: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

file_service = FileService()


async def _get_local_config(db: AsyncSession) -> LocalConfig:
    """Récupère la configuration locale ou lève 404."""
    result = await db.execute(select(LocalConfig).limit(1))
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration initiale non effectuée",
        )
    return config


async def _verify_ticket(ticket_token: str) -> dict:
    """Vérifie un token ticket auprès du Site Central.

    Envoie le token signé au Site Central qui valide la signature,
    l'expiration et le statut en base de données.

    Returns a dict with keys: valid (bool), message (str), ticket_code (str|None).
    """
    client = SiteCentralClient()
    try:
        resp = await client.post(
            "/api/tickets/verify",
            json={"ticket_token": ticket_token},
        )
    except SiteCentralError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.message,
        )

    if resp.status_code == 200:
        data = resp.json()
        if data.get("success"):
            return {
                "valid": True,
                "message": "Ticket valide",
                "ticket_code": data.get("ticket_code", ""),
            }
        error = data.get("error", "Ticket invalide ou déjà utilisé")
        return {"valid": False, "message": error, "ticket_code": data.get("ticket_code")}

    try:
        body = resp.json()
        detail = body.get("detail", "Ticket invalide ou déjà utilisé")
    except Exception:
        detail = "Ticket invalide ou déjà utilisé"
    return {"valid": False, "message": detail, "ticket_code": None}


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()


# ---- 1. GET /  (list dossiers) --------------------------------------------

@router.get("", response_model=DossierListResponse)
async def list_dossiers(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Liste tous les dossiers triés par date de création décroissante."""
    result = await db.execute(
        select(Dossier).order_by(Dossier.created_at.desc(), Dossier.id.desc())
    )
    dossiers = result.scalars().all()
    return DossierListResponse(
        dossiers=[
            DossierListItem(
                id=d.id,
                nom=d.nom,
                ticket_id=d.ticket_id,
                domaine=d.domaine,
                statut=d.statut,
                created_at=d.created_at,
            )
            for d in dossiers
        ]
    )


# ---- 2. POST /  (create dossier) ------------------------------------------

@router.post("", response_model=DossierDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_dossier(
    body: DossierCreateRequest,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crée un nouveau dossier après vérification du token ticket."""
    # Verify ticket token with Site Central
    ticket_result = await _verify_ticket(body.ticket_id)
    if not ticket_result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ticket_result["message"],
        )

    ticket_code = ticket_result["ticket_code"] or body.ticket_id[:20]

    # Check ticket uniqueness locally
    existing = await db.execute(
        select(Dossier).where(Dossier.ticket_id == ticket_code)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce ticket a déjà été utilisé pour créer un dossier",
        )

    # Get domaine from local config
    config = await _get_local_config(db)

    # Create dossier
    dossier = Dossier(
        nom=body.nom,
        ticket_id=ticket_code,
        domaine=config.domaine,
        statut="actif",
    )
    db.add(dossier)
    await db.flush()  # get dossier.id

    # Create 5 steps (1, 2, 3, 4, 5) all with statut="initial"
    steps: list[Step] = []
    for step_number in range(1, 6):
        step = Step(
            dossier_id=dossier.id,
            step_number=step_number,
            statut="initial",
        )
        db.add(step)
        steps.append(step)

    await db.commit()
    await db.refresh(dossier)
    for s in steps:
        await db.refresh(s)

    return DossierDetailResponse(
        id=dossier.id,
        nom=dossier.nom,
        ticket_id=dossier.ticket_id,
        domaine=dossier.domaine,
        statut=dossier.statut,
        created_at=dossier.created_at,
        updated_at=dossier.updated_at,
        steps=[
            StepItem(
                step_number=s.step_number,
                statut=s.statut,
                executed_at=s.executed_at,
                validated_at=s.validated_at,
            )
            for s in sorted(steps, key=lambda s: s.step_number)
        ],
    )


# ---- 3. GET /{id}  (dossier detail) ---------------------------------------

@router.get("/{dossier_id}", response_model=DossierDetailResponse)
async def get_dossier(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retourne le détail d'un dossier avec ses étapes."""
    result = await db.execute(
        select(Dossier)
        .options(selectinload(Dossier.steps).selectinload(Step.files))
        .where(Dossier.id == dossier_id)
    )
    dossier = result.scalar_one_or_none()
    if dossier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé",
        )

    return DossierDetailResponse(
        id=dossier.id,
        nom=dossier.nom,
        ticket_id=dossier.ticket_id,
        domaine=dossier.domaine,
        statut=dossier.statut,
        created_at=dossier.created_at,
        updated_at=dossier.updated_at,
        steps=[
            StepItem(
                step_number=s.step_number,
                statut=s.statut,
                executed_at=s.executed_at,
                validated_at=s.validated_at,
                files=[
                    StepFileItem(
                        id=f.id,
                        filename=f.filename,
                        file_path=f.file_path,
                        file_type=f.file_type,
                        file_size=f.file_size,
                        created_at=f.created_at,
                        is_modified=f.is_modified,
                        original_file_path=f.original_file_path,
                        updated_at=f.updated_at,
                    )
                    for f in s.files
                ],
            )
            for s in sorted(dossier.steps, key=lambda s: s.step_number)
        ],
    )


# ---- 4. GET /{id}/steps/{step}  (step detail) -----------------------------

@router.get("/{dossier_id}/steps/{step_number}", response_model=StepDetailResponse)
async def get_step_detail(
    dossier_id: int,
    step_number: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retourne le détail d'une étape spécifique avec ses fichiers."""
    if step_number not in (1, 2, 3, 4, 5):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le numéro d'étape doit être entre 1 et 5",
        )

    # Verify dossier exists
    dossier_result = await db.execute(
        select(Dossier).where(Dossier.id == dossier_id)
    )
    if dossier_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé",
        )

    result = await db.execute(
        select(Step)
        .options(selectinload(Step.files))
        .where(Step.dossier_id == dossier_id, Step.step_number == step_number)
    )
    step = result.scalar_one_or_none()
    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Étape non trouvée",
        )

    return StepDetailResponse(
        id=step.id,
        step_number=step.step_number,
        statut=step.statut,
        executed_at=step.executed_at,
        validated_at=step.validated_at,
        files=[
            StepFileItem(
                id=f.id,
                filename=f.filename,
                file_path=f.file_path,
                file_type=f.file_type,
                file_size=f.file_size,
                created_at=f.created_at,
                is_modified=f.is_modified,
                original_file_path=f.original_file_path,
                updated_at=f.updated_at,
            )
            for f in step.files
        ],
    )


# ---- 5. POST /{id}/close  (fermer le dossier) -----------------------------

@router.post("/{dossier_id}/close", response_model=DossierCloseResponse)
async def close_dossier(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ferme le dossier si toutes les étapes sont validées.

    Valide : Exigences 5.2, 5.3, 5.4, 5.5
    """
    await workflow_engine.close_dossier(dossier_id, db)
    await db.commit()

    return DossierCloseResponse(message="Dossier fermé avec succès")


# ---- 5b. POST /{id}/steps/{step}/reset  (reset step) ----------------------

@router.post(
    "/{dossier_id}/steps/{step_number}/reset",
    response_model=StepResetResponse,
)
async def reset_step(
    dossier_id: int,
    step_number: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remet une étape à "initial" et supprime ses fichiers.

    Supprime les fichiers sur disque et en base, puis remet le statut
    de l'étape (et des suivantes non-validées) à "initial".
    """
    import shutil

    # Déléguer la logique métier au WorkflowEngine
    await workflow_engine.reset_step(dossier_id, step_number, db)

    # Supprimer les fichiers sur disque
    step_dir = os.path.join(DATA_DIR, "dossiers", str(dossier_id), f"step{step_number}")
    if os.path.isdir(step_dir):
        shutil.rmtree(step_dir)

    await db.commit()

    return StepResetResponse(message=f"Étape {step_number} réinitialisée")


# ---- 5b2. POST /{id}/steps/{step}/cancel  (annuler step en cours) ---------

@router.post(
    "/{dossier_id}/steps/{step_number}/cancel",
    response_model=StepResetResponse,
)
async def cancel_step(
    dossier_id: int,
    step_number: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Annule un step en cours de traitement et le remet à initial."""
    result = await db.execute(
        select(Step)
        .where(Step.dossier_id == dossier_id, Step.step_number == step_number)
    )
    step = result.scalar_one_or_none()
    if step is None:
        raise HTTPException(status_code=404, detail="Étape non trouvée")
    if step.statut != "en_cours":
        raise HTTPException(status_code=400, detail="L'étape n'est pas en cours")
    step.statut = "initial"
    step.executed_at = None
    await db.commit()
    return StepResetResponse(message=f"Étape {step_number} annulée")


# ---- 5c. POST /{id}/reset-all  (reset complet) ----------------------------

@router.post(
    "/{dossier_id}/reset-all",
    response_model=DossierResetAllResponse,
)
async def reset_all_steps(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Réinitialise toutes les étapes du dossier et supprime tous les fichiers."""
    import shutil

    # Vérifier que le dossier est actif
    result = await db.execute(
        select(Dossier)
        .options(selectinload(Dossier.steps).selectinload(Step.files))
        .where(Dossier.id == dossier_id)
    )
    dossier = result.scalar_one_or_none()
    if dossier is None:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")
    if dossier.statut != DOSSIER_ACTIF:
        raise HTTPException(status_code=403, detail="Le dossier n'est pas actif")

    # Remettre toutes les étapes à "initial" et supprimer les StepFile
    for step in dossier.steps:
        step.statut = "initial"
        step.executed_at = None
        step.validated_at = None
        for sf in list(step.files):
            await db.delete(sf)

    # Supprimer les fichiers sur disque pour chaque step
    for step_num in range(1, 6):
        step_dir = os.path.join(DATA_DIR, "dossiers", str(dossier_id), f"step{step_num}")
        if os.path.isdir(step_dir):
            shutil.rmtree(step_dir)

    await db.commit()

    return DossierResetAllResponse(message="Dossier réinitialisé — tous les fichiers supprimés")


# ---- 5d. POST /{id}/archive  (archiver) -----------------------------------

@router.post(
    "/{dossier_id}/archive",
    response_model=DossierArchiveResponse,
)
async def archive_dossier(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Archive un dossier fermé — le rend définitivement en lecture seule."""
    result = await db.execute(
        select(Dossier).where(Dossier.id == dossier_id)
    )
    dossier = result.scalar_one_or_none()
    if dossier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé",
        )
    if dossier.statut != DOSSIER_FERME:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Le dossier doit être fermé avant d'être archivé",
        )
    dossier.statut = "archive"
    await db.commit()

    return DossierArchiveResponse(message="Dossier archivé")


# ---- 6. GET /{id}/download  (télécharger archive ZIP) ---------------------

@router.get("/{dossier_id}/download")
async def download_dossier(
    dossier_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Génère et télécharge l'archive ZIP d'un dossier fermé.

    Valide : Exigences 6.1, 6.2, 6.3, 6.4, 6.5
    """
    # Vérifier que le dossier existe
    result = await db.execute(
        select(Dossier).where(Dossier.id == dossier_id)
    )
    dossier = result.scalar_one_or_none()
    if dossier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé",
        )

    # Vérifier que le dossier est fermé
    if dossier.statut not in (DOSSIER_FERME, "archive"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Le dossier doit être fermé ou archivé pour télécharger l'archive",
        )

    # Générer l'archive ZIP en mémoire
    dossier_root = os.path.join(DATA_DIR, "dossiers", str(dossier_id))
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for step_num in range(1, 6):
            step_dir = os.path.join(dossier_root, f"step{step_num}")
            if not os.path.isdir(step_dir):
                continue
            for filename in sorted(os.listdir(step_dir)):
                file_path = os.path.join(step_dir, filename)
                if os.path.isfile(file_path):
                    arcname = f"step{step_num}/{filename}"
                    zf.write(file_path, arcname)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="dossier_{dossier_id}_archive.zip"',
        },
    )


# ---------------------------------------------------------------------------
# Helpers — fichiers individuels
# ---------------------------------------------------------------------------


async def _get_step_file_with_context(
    dossier_id: int, file_id: int, db: AsyncSession
) -> tuple[StepFile, Step, Dossier]:
    """Charge un StepFile avec son Step et son Dossier, ou lève 404."""
    result = await db.execute(
        select(StepFile)
        .join(Step, StepFile.step_id == Step.id)
        .join(Dossier, Step.dossier_id == Dossier.id)
        .where(StepFile.id == file_id, Dossier.id == dossier_id)
        .options(
            selectinload(StepFile.step).selectinload(Step.dossier),
        )
    )
    step_file = result.scalar_one_or_none()
    if step_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier non trouvé",
        )
    return step_file, step_file.step, step_file.step.dossier


# ---- 7. GET /{id}/files/{file_id}/download  (fichier individuel) ----------

@router.get("/{dossier_id}/files/{file_id}/download", response_class=FileResponse)
async def download_file(
    dossier_id: int,
    file_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Télécharge un fichier individuel (Content-Disposition: attachment).

    Valide : Exigence 8.1
    """
    step_file, _step, _dossier = await _get_step_file_with_context(
        dossier_id, file_id, db
    )

    if not os.path.isfile(step_file.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier non trouvé",
        )

    content_type = file_service.get_content_type(step_file.filename)
    return FileResponse(
        path=step_file.file_path,
        media_type=content_type,
        filename=step_file.filename,
        headers={
            "Content-Disposition": f'attachment; filename="{step_file.filename}"',
        },
    )


# ---- 8. GET /{id}/files/{file_id}/preview  (prévisualisation) -------------

@router.get("/{dossier_id}/files/{file_id}/preview", response_class=FileResponse)
async def preview_file(
    dossier_id: int,
    file_id: int,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Affiche un fichier inline — Markdown/PDF inline, .docx → download.

    Valide : Exigence 8.3
    """
    step_file, _step, _dossier = await _get_step_file_with_context(
        dossier_id, file_id, db
    )

    if not os.path.isfile(step_file.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier non trouvé",
        )

    content_type = file_service.get_content_type(step_file.filename)
    ext = os.path.splitext(step_file.filename)[1].lower()

    # .docx ne peut pas être affiché inline → forcer le téléchargement
    if ext == ".docx":
        disposition = f'attachment; filename="{step_file.filename}"'
    else:
        disposition = "inline"

    return FileResponse(
        path=step_file.file_path,
        media_type=content_type,
        headers={"Content-Disposition": disposition},
    )


# ---- 9. PUT /{id}/files/{file_id}/replace  (remplacement) ----------------

@router.put(
    "/{dossier_id}/files/{file_id}/replace",
    response_model=FileReplaceResponse,
)
async def replace_file(
    dossier_id: int,
    file_id: int,
    file: UploadFile,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileReplaceResponse:
    """Remplace un fichier existant par une version modifiée par l'expert.

    Valide : Exigences 9.2, 9.3, 9.4, 9.5, 9.6
    """
    step_file, step, dossier = await _get_step_file_with_context(
        dossier_id, file_id, db
    )

    # Vérifier que le dossier n'est pas fermé
    if dossier.statut == DOSSIER_FERME:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Le dossier est fermé, aucune modification n'est possible",
        )

    # Vérifier que l'étape n'est pas validée
    if step.statut == STATUT_VALIDE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Étape verrouillée, modification impossible",
        )

    # Lire et valider le contenu
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier uploadé est vide",
        )

    # Remplacer sur le disque
    step_dir = os.path.join(
        DATA_DIR, "dossiers", str(dossier_id), f"step{step.step_number}"
    )
    try:
        file_service.replace_file(step_file, content, step_dir)
    except OSError:
        logger.exception("Erreur lors de l'écriture du fichier sur le disque")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'écriture du fichier sur le disque",
        )

    await db.commit()

    return FileReplaceResponse(
        message="Fichier remplacé avec succès",
        new_size=step_file.file_size,
    )
