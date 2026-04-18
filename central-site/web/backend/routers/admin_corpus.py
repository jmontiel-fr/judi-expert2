"""Router d'administration du corpus — Site Central.

Endpoints protégés pour l'upload de fichiers PDF et l'ajout d'URLs
dans le corpus d'un domaine.
"""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from models.expert import Expert
from routers.admin import get_admin_expert
from schemas.corpus import AddUrlRequest, ContenuItemResponse, UrlItemResponse
from services.corpus_content_service import CorpusContentService
from services.domaines_service import load_domaines

logger = logging.getLogger(__name__)

router = APIRouter()

# Résolution du chemin de base du corpus
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_CORPUS_BASE_PATH_ENV = os.environ.get("CORPUS_BASE_PATH")
if _CORPUS_BASE_PATH_ENV:
    _CORPUS_BASE_PATH = Path(_CORPUS_BASE_PATH_ENV)
else:
    try:
        _PROJECT_ROOT = _BACKEND_DIR.parents[2]
        _CORPUS_BASE_PATH = _PROJECT_ROOT / "corpus"
    except IndexError:
        _CORPUS_BASE_PATH = Path("/data/corpus")


def _get_corpus_service() -> CorpusContentService:
    """Retourne une instance du service de contenu corpus."""
    return CorpusContentService(corpus_base_path=_CORPUS_BASE_PATH)


def _validate_domaine(domaine: str) -> None:
    """Valide que le domaine existe dans domaines.yaml.

    Args:
        domaine: Nom du domaine à valider.

    Raises:
        HTTPException: 404 si le domaine n'existe pas, 500 si config introuvable.
    """
    try:
        domaines_config = load_domaines()
    except (FileNotFoundError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration des domaines introuvable",
        )

    noms_domaines = [d.get("nom") for d in domaines_config]
    if domaine not in noms_domaines:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domaine introuvable",
        )


@router.post(
    "/{domaine}/documents",
    response_model=ContenuItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    domaine: str,
    file: UploadFile,
    _admin: Expert = Depends(get_admin_expert),
) -> ContenuItemResponse:
    """Upload un fichier PDF dans le corpus d'un domaine.

    Valide que le fichier est un PDF, vérifie l'absence de doublon,
    puis enregistre le fichier et met à jour contenu.yaml.

    Args:
        domaine: Nom du domaine cible.
        file: Fichier PDF uploadé.
        _admin: Expert administrateur (injecté par dépendance).

    Returns:
        Métadonnées de l'entrée ajoutée dans contenu.yaml.

    Raises:
        HTTPException: 404 domaine inexistant, 400 non-PDF, 409 doublon.
    """
    _validate_domaine(domaine)

    # Vérifier que le fichier est un PDF
    is_pdf = (
        file.content_type == "application/pdf"
        or (file.filename or "").lower().endswith(".pdf")
    )
    if not is_pdf:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seuls les fichiers PDF sont acceptés",
        )

    filename = file.filename or "document.pdf"
    content = await file.read()

    service = _get_corpus_service()
    try:
        entry = service.save_pdf(domaine, filename, content)
    except FileExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un document portant ce nom existe déjà",
        )

    return ContenuItemResponse(**entry)


@router.post(
    "/{domaine}/urls",
    response_model=UrlItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_url(
    domaine: str,
    request: AddUrlRequest,
    _admin: Expert = Depends(get_admin_expert),
) -> UrlItemResponse:
    """Ajoute une URL dans le corpus d'un domaine.

    Args:
        domaine: Nom du domaine cible.
        request: Données de l'URL à ajouter.
        _admin: Expert administrateur (injecté par dépendance).

    Returns:
        Métadonnées de l'entrée ajoutée dans urls.yaml.

    Raises:
        HTTPException: 404 si le domaine n'existe pas.
    """
    _validate_domaine(domaine)

    service = _get_corpus_service()
    entry = service.add_url(domaine, request.model_dump())

    return UrlItemResponse(**entry)
