"""Router de gestion des corpus par domaine — Site Central."""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.corpus_version import CorpusVersion
from models.domaine import Domaine
from schemas.corpus import ContenuItemResponse, CorpusResponse, CorpusVersionResponse, UrlItemResponse
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


@router.get("", response_model=list[CorpusResponse])
async def list_corpus(db: AsyncSession = Depends(get_db)):
    """Liste tous les corpus par domaine.

    Lit le fichier domaines.yaml pour la liste des domaines,
    puis enrichit avec les versions de corpus depuis la base de données.
    """
    try:
        domaines_config = load_domaines()
    except FileNotFoundError:
        logger.warning("Fichier domaines.yaml introuvable")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration des domaines introuvable",
        )
    except ValueError as e:
        logger.error("Erreur de parsing domaines.yaml : %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur de configuration des domaines",
        )

    result = []
    for domaine_cfg in domaines_config:
        nom = domaine_cfg.get("nom", "")

        # Chercher les versions en DB via le modèle Domaine
        stmt = select(Domaine).where(Domaine.nom == nom)
        db_domaine = (await db.execute(stmt)).scalars().first()

        versions: list[CorpusVersionResponse] = []
        if db_domaine:
            stmt_versions = (
                select(CorpusVersion)
                .where(CorpusVersion.domaine_id == db_domaine.id)
                .order_by(CorpusVersion.published_at.desc())
            )
            db_versions = (await db.execute(stmt_versions)).scalars().all()
            versions = [
                CorpusVersionResponse.model_validate(v) for v in db_versions
            ]

        result.append(
            CorpusResponse(
                nom=nom,
                repertoire=domaine_cfg.get("repertoire", ""),
                actif=domaine_cfg.get("actif", False),
                versions=versions,
            )
        )

    return result


@router.get("/{domaine}/versions", response_model=list[CorpusVersionResponse])
async def list_versions(domaine: str, db: AsyncSession = Depends(get_db)):
    """Liste toutes les versions du module RAG d'un domaine.

    Retourne les CorpusVersion depuis la base de données pour le domaine donné.
    """
    # Vérifier que le domaine existe dans domaines.yaml
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
            detail=f"Domaine '{domaine}' introuvable",
        )

    # Chercher le domaine en DB
    stmt = select(Domaine).where(Domaine.nom == domaine)
    db_domaine = (await db.execute(stmt)).scalars().first()

    if not db_domaine:
        # Le domaine existe dans le YAML mais pas encore en DB → liste vide
        return []

    stmt_versions = (
        select(CorpusVersion)
        .where(CorpusVersion.domaine_id == db_domaine.id)
        .order_by(CorpusVersion.published_at.desc())
    )
    db_versions = (await db.execute(stmt_versions)).scalars().all()

    return [CorpusVersionResponse.model_validate(v) for v in db_versions]


@router.get("/{domaine}/contenu", response_model=list[ContenuItemResponse])
async def get_contenu(domaine: str) -> list[ContenuItemResponse]:
    """Liste le contenu du corpus d'un domaine.

    Lit le fichier contenu.yaml du domaine demandé et retourne la liste
    des ressources. Retourne une liste vide si le fichier n'existe pas.
    Cet endpoint ne nécessite pas d'authentification.

    Args:
        domaine: Nom du domaine (ex: 'psychologie').

    Returns:
        Liste des éléments de contenu du corpus.

    Raises:
        HTTPException: 404 si le domaine n'existe pas dans domaines.yaml.
    """
    _validate_domaine(domaine)

    service = _get_corpus_service()
    try:
        items = service.load_contenu(domaine)
    except ValueError as e:
        logger.error("Erreur de lecture du corpus contenu pour %s : %s", domaine, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur de lecture du corpus",
        )

    return [ContenuItemResponse(**item) for item in items]


@router.get("/{domaine}/urls", response_model=list[UrlItemResponse])
async def get_urls(domaine: str) -> list[UrlItemResponse]:
    """Liste les URLs de référence du corpus d'un domaine.

    Lit le fichier urls/urls.yaml du domaine demandé et retourne la liste
    des URLs. Retourne une liste vide si le fichier n'existe pas.
    Cet endpoint ne nécessite pas d'authentification.

    Args:
        domaine: Nom du domaine (ex: 'psychologie').

    Returns:
        Liste des URLs de référence du corpus.

    Raises:
        HTTPException: 404 si le domaine n'existe pas dans domaines.yaml.
    """
    _validate_domaine(domaine)

    service = _get_corpus_service()
    try:
        items = service.load_urls(domaine)
    except ValueError as e:
        logger.error("Erreur de lecture des URLs corpus pour %s : %s", domaine, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur de lecture du corpus",
        )

    return [UrlItemResponse(**item) for item in items]


@router.get("/{domaine}/fichier/{filename:path}")
async def download_corpus_file(domaine: str, filename: str) -> FileResponse:
    """Télécharge un fichier du corpus d'un domaine.

    Le filename correspond au champ 'nom' du contenu.yaml
    (ex: 'TPE_psychologie.tpl', 'documents/guide_methodologique.pdf').
    Les fichiers .tpl sont servis avec l'extension .md.
    """
    _validate_domaine(domaine)

    # Sécurité : empêcher la traversée de répertoire
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chemin de fichier invalide",
        )

    file_path = _CORPUS_BASE_PATH / domaine / filename

    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier non trouvé dans le corpus",
        )

    # Renommer .tpl en .md pour le téléchargement
    download_name = file_path.name
    ext = file_path.suffix.lower()
    if ext == ".tpl":
        download_name = file_path.stem + ".md"

    # Content-type adapté
    content_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".tpl": "text/markdown",
        ".md": "text/markdown",
    }
    media_type = content_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        filename=download_name,
        media_type=media_type,
    )
