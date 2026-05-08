"""Router de version — vérification, mise à jour forcée, statut LLM.

Expose les endpoints de gestion des versions de l'Application Locale :
- GET /api/version : version courante + vérification de mise à jour
- POST /api/version/update : déclenchement de la mise à jour forcée
- GET /api/llm/update-status : état de la mise à jour du modèle LLM

Valide : Exigences 1.2, 3.1, 3.2, 3.3, 3.4, 3.5, 5.3, 7.1, 9.1, 9.3
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.version import (
    LlmUpdateStatusResponse,
    LocalVersionResponse,
    UpdateStatusResponse,
)
from services.llm_update_service import LlmUpdateService
from services.site_central_client import (
    SiteCentralClient,
    SiteCentralError,
    is_within_business_hours,
)
from services.update_service import UpdateError, UpdateService
from services.version_reader import compare_versions, read_version_file

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Chemin vers le fichier VERSION de l'Application Locale
# En conteneur Docker, le fichier est copié à /app/VERSION via le Dockerfile.
# En développement local, il est 3 niveaux au-dessus (local-site/VERSION).
VERSION_FILE: Path = Path(
    os.environ.get("VERSION_FILE", "/app/VERSION")
)

# ---------------------------------------------------------------------------
# Pydantic schemas (request bodies)
# ---------------------------------------------------------------------------


class UpdateRequest(BaseModel):
    """Requête de déclenchement de mise à jour forcée."""

    download_url: str = Field(..., min_length=1, description="URL de téléchargement des images Docker")
    version: str = Field(..., min_length=1, description="Version cible (semver)")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()


# ---- GET /version ----------------------------------------------------------


@router.get("/version", response_model=LocalVersionResponse)
async def get_version():
    """Retourne la version locale et vérifie la disponibilité d'une mise à jour.

    1. Lit le fichier VERSION local.
    2. Si dans les heures ouvrables, interroge le Site Central.
    3. Si le Site Central retourne une version plus récente avec mandatory=true,
       indique qu'une mise à jour est disponible.
    4. Si hors heures ouvrables ou Site Central injoignable, retourne
       update_available=false.
    """
    # 1. Lire la version locale
    try:
        version_info = read_version_file(VERSION_FILE)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Impossible de lire le fichier VERSION : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fichier VERSION invalide ou manquant : {exc}",
        )

    local_version = version_info.version
    local_date = version_info.date

    # 2. Vérifier si on est dans les heures ouvrables
    if not is_within_business_hours():
        logger.debug("Hors heures ouvrables — pas de vérification Site Central")
        return LocalVersionResponse(
            current_version=local_version,
            current_date=local_date,
            update_available=False,
        )

    # 3. Interroger le Site Central (isolation des données : seul current_version est envoyé)
    try:
        client = SiteCentralClient()
        response = await client.get(
            "/api/version",
            params={"current_version": local_version},
        )
    except SiteCentralError as exc:
        logger.warning(
            "Site Central indisponible lors de la vérification de version : %s",
            exc.message,
        )
        return LocalVersionResponse(
            current_version=local_version,
            current_date=local_date,
            update_available=False,
        )

    # 4. Analyser la réponse du Site Central
    if response.status_code != 200:
        logger.warning(
            "Site Central a retourné HTTP %d lors de la vérification de version",
            response.status_code,
        )
        return LocalVersionResponse(
            current_version=local_version,
            current_date=local_date,
            update_available=False,
        )

    try:
        data = response.json()
    except Exception as exc:
        logger.warning("Réponse JSON invalide du Site Central : %s", exc)
        return LocalVersionResponse(
            current_version=local_version,
            current_date=local_date,
            update_available=False,
        )

    latest_version: Optional[str] = data.get("latest_version")
    download_url: Optional[str] = data.get("download_url")
    mandatory: Optional[bool] = data.get("mandatory")
    release_notes: Optional[str] = data.get("release_notes")

    # 5. Comparer les versions
    update_available = False
    if latest_version:
        try:
            if compare_versions(local_version, latest_version) < 0 and mandatory:
                update_available = True
        except ValueError as exc:
            logger.warning(
                "Comparaison de version impossible : %s", exc
            )

    return LocalVersionResponse(
        current_version=local_version,
        current_date=local_date,
        update_available=update_available,
        latest_version=latest_version,
        download_url=download_url if update_available else None,
        mandatory=mandatory,
        release_notes=release_notes if update_available else None,
    )


# ---- POST /version/update --------------------------------------------------


@router.post("/version/update", response_model=UpdateStatusResponse)
async def trigger_update(
    request: UpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Déclenche une mise à jour forcée de l'Application Locale.

    Télécharge les images Docker, arrête les conteneurs, charge les
    nouvelles images, redémarre et met à jour LocalConfig.
    """
    service = UpdateService(
        db_session=db,
        download_url=request.download_url,
        new_version=request.version,
    )

    try:
        await service.execute_update()
    except UpdateError as exc:
        logger.error("Mise à jour échouée : %s (étape: %s)", exc.message, exc.step)
        return UpdateStatusResponse(
            status="error",
            progress=0,
            step=exc.step,
            error_message=exc.message,
        )

    update_status = service.get_status()
    return UpdateStatusResponse(
        status=update_status["status"],
        progress=update_status["progress"],
        step=update_status["step"],
        error_message=update_status["error_message"],
    )


# ---- GET /llm/update-status ------------------------------------------------


@router.get("/llm/update-status", response_model=LlmUpdateStatusResponse)
async def get_llm_update_status():
    """Retourne l'état de la mise à jour du modèle LLM.

    Lit le fichier d'état JSON écrit par ollama-entrypoint.sh et retourne
    le statut courant (idle, downloading, ready, error) avec la progression.
    """
    service = LlmUpdateService()
    result = await service.get_update_status()

    return LlmUpdateStatusResponse(
        status=result["status"],
        progress=result["progress"],
        current_model=result["current_model"],
        error_message=result["error_message"],
    )
