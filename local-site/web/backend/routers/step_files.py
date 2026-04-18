"""Router générique pour les opérations sur les fichiers d'étape.

Endpoints :
- GET  /{file_id}/download — téléchargement (Content-Disposition: attachment)
- GET  /{file_id}/view     — affichage inline (Content-Disposition: inline)
- POST /{file_id}/replace  — remplacement par une version modifiée

Valide : Exigences 7.1, 7.2, 7.3, 7.4, 7.5, 3.2, 3.3, 3.4, 4.1–4.6, 2.5
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.step_file import StepFile
from routers.auth import get_current_user
from services.file_service import FileService
from services.workflow_engine import workflow_engine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR: str = os.environ.get("DATA_DIR", "data")

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class StepFileResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    is_modified: bool
    original_file_path: str | None
    created_at: datetime
    updated_at: datetime | None


class StepFileReplaceResponse(BaseModel):
    message: str
    file: StepFileResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

file_service = FileService()


def _step_dir(dossier_id: int, step_number: int) -> str:
    """Retourne le chemin du répertoire d'une étape sur le disque."""
    return os.path.join(DATA_DIR, "dossiers", str(dossier_id), f"step{step_number}")


async def _get_step_file(file_id: int, db: AsyncSession) -> StepFile:
    """Charge un StepFile par id ou lève 404."""
    result = await db.execute(select(StepFile).where(StepFile.id == file_id))
    step_file = result.scalar_one_or_none()
    if step_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier non trouvé",
        )
    return step_file


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()


# ---- GET /{dossier_id}/steps/{step_number}/files/{file_id}/download ------

@router.get(
    "/{dossier_id}/steps/{step_number}/files/{file_id}/download",
    response_class=FileResponse,
)
async def download_file(
    dossier_id: int,
    step_number: int,
    file_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> FileResponse:
    """Télécharge un fichier d'étape (Content-Disposition: attachment)."""
    step_file = await _get_step_file(file_id, db)

    if not os.path.isfile(step_file.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier introuvable sur le disque",
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


# ---- GET /{dossier_id}/steps/{step_number}/files/{file_id}/view ---------

@router.get(
    "/{dossier_id}/steps/{step_number}/files/{file_id}/view",
    response_class=FileResponse,
)
async def view_file(
    dossier_id: int,
    step_number: int,
    file_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> FileResponse:
    """Affiche un fichier d'étape inline (Content-Disposition: inline)."""
    step_file = await _get_step_file(file_id, db)

    if not os.path.isfile(step_file.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier introuvable sur le disque",
        )

    content_type = file_service.get_content_type(step_file.filename)
    return FileResponse(
        path=step_file.file_path,
        media_type=content_type,
        headers={
            "Content-Disposition": "inline",
        },
    )


# ---- POST /{dossier_id}/steps/{step_number}/files/{file_id}/replace -----

@router.post(
    "/{dossier_id}/steps/{step_number}/files/{file_id}/replace",
    response_model=StepFileReplaceResponse,
)
async def replace_file(
    dossier_id: int,
    step_number: int,
    file_id: int,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> StepFileReplaceResponse:
    """Remplace un fichier d'étape par une version modifiée par l'expert."""
    # 1. Vérifier que l'étape n'est pas verrouillée
    await workflow_engine.require_step_not_validated(dossier_id, step_number, db)

    # 2. Charger le StepFile
    step_file = await _get_step_file(file_id, db)

    # 3. Valider l'extension
    original_ext = os.path.splitext(step_file.filename)[1].lower()
    uploaded_ext = os.path.splitext(file.filename or "")[1].lower()
    if uploaded_ext != original_ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le fichier doit avoir la même extension que l'original ({original_ext})",
        )

    # 4. Lire le contenu et valider qu'il n'est pas vide
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier uploadé est vide",
        )

    # 5. Remplacer le fichier sur le disque et mettre à jour le StepFile
    step_dir = _step_dir(dossier_id, step_number)
    try:
        file_service.replace_file(step_file, content, step_dir)
    except OSError:
        logger.exception("Erreur lors de l'écriture du fichier sur le disque")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'écriture du fichier sur le disque",
        )

    # 6. Persister les modifications en base
    await db.commit()
    await db.refresh(step_file)

    return StepFileReplaceResponse(
        message="Fichier remplacé avec succès",
        file=StepFileResponse(
            id=step_file.id,
            filename=step_file.filename,
            file_type=step_file.file_type,
            file_size=step_file.file_size,
            is_modified=step_file.is_modified,
            original_file_path=step_file.original_file_path,
            created_at=step_file.created_at,
            updated_at=step_file.updated_at,
        ),
    )
