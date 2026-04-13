"""Router de configuration — domaine, RAG, TPE, Template, documents.

Valide : Exigences 3.1–3.7, 4.1, 4.2, 33.2
"""

from __future__ import annotations

import logging
import os
import shutil
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.local_config import LocalConfig
from routers.auth import get_current_user
from services.rag_service import RAGService
from services.site_central_client import (
    SiteCentralClient,
    SiteCentralError,
    get_business_hours_message,
    is_within_business_hours,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SITE_CENTRAL_URL: str = os.environ.get("SITE_CENTRAL_URL", "https://www.judi-expert.fr")
CONFIG_DIR: str = os.environ.get("CONFIG_DIR", "data/config")

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class DomainResponse(BaseModel):
    domaine: str


class DomainUpdateRequest(BaseModel):
    domaine: str = Field(..., min_length=1, description="Nouveau domaine d'expertise")


class RAGVersionItem(BaseModel):
    version: str
    description: str
    domaine: str


class RAGVersionsResponse(BaseModel):
    versions: list[RAGVersionItem]


class RAGInstallRequest(BaseModel):
    version: str = Field(..., min_length=1, description="Version du module RAG à installer")


class RAGInstallResponse(BaseModel):
    message: str
    version: str


class UploadResponse(BaseModel):
    message: str
    filename: str
    doc_id: str


class DocumentItem(BaseModel):
    doc_id: str
    filename: str
    doc_type: str
    chunk_count: int
    collection: str


class DocumentsListResponse(BaseModel):
    documents: list[DocumentItem]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_config(db: AsyncSession) -> LocalConfig:
    """Récupère la configuration locale ou lève 404."""
    result = await db.execute(select(LocalConfig).limit(1))
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration initiale non effectuée",
        )
    return config


def _require_rag_configured(config: LocalConfig) -> None:
    """Bloque l'accès si le RAG n'est pas configuré."""
    if not config.is_configured or config.rag_version is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="RAG non configuré",
        )


def _ensure_config_dir() -> str:
    """Crée le répertoire data/config/ s'il n'existe pas et retourne le chemin."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    return CONFIG_DIR


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()


# ---- 1. GET /domain -------------------------------------------------------

@router.get("/domain", response_model=DomainResponse)
async def get_domain(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retourne le domaine d'expertise courant."""
    config = await _get_config(db)
    return DomainResponse(domaine=config.domaine)


# ---- 2. PUT /domain -------------------------------------------------------

@router.put("/domain", response_model=DomainResponse)
async def update_domain(
    body: DomainUpdateRequest,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Met à jour le domaine d'expertise."""
    config = await _get_config(db)
    config.domaine = body.domaine
    await db.commit()
    await db.refresh(config)
    return DomainResponse(domaine=config.domaine)


# ---- 3. GET /rag-versions -------------------------------------------------

@router.get("/rag-versions", response_model=RAGVersionsResponse)
async def get_rag_versions(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retourne les versions RAG disponibles sur le Site Central.

    Appelle GET /api/corpus/{domaine}/versions sur le Site Central.
    En cas d'indisponibilité, retourne un message d'erreur clair.
    """
    config = await _get_config(db)
    domaine = config.domaine

    client = SiteCentralClient()
    try:
        resp = await client.get(f"/api/corpus/{domaine}/versions")
    except SiteCentralError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.message,
        )

    if resp.status_code == 200:
        data = resp.json()
        versions = []
        for item in data:
            versions.append(
                RAGVersionItem(
                    version=item.get("version", ""),
                    description=item.get("description", ""),
                    domaine=domaine,
                )
            )
        return RAGVersionsResponse(versions=versions)

    if resp.status_code == 404:
        # Domain not found on Site Central — return empty list
        return RAGVersionsResponse(versions=[])

    # Unexpected error
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Erreur lors de la récupération des versions RAG depuis le Site Central",
    )


# ---- 4. POST /rag-install --------------------------------------------------

@router.post("/rag-install", response_model=RAGInstallResponse)
async def install_rag(
    body: RAGInstallRequest,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Installe une version du module RAG.

    Contacte le Site Central pour valider la version, puis met à jour
    rag_version et is_configured dans LocalConfig.
    En production, téléchargerait l'image Docker RAG depuis ECR.
    """
    config = await _get_config(db)
    domaine = config.domaine

    # Vérifier que la version existe sur le Site Central (best-effort)
    client = SiteCentralClient()
    try:
        resp = await client.get(f"/api/corpus/{domaine}/versions")
        version_found = False
        if resp.status_code == 200:
            data = resp.json()
            for item in data:
                if item.get("version") == body.version:
                    version_found = True
                    break
        if not version_found:
            logger.warning(
                "Version RAG %s non trouvée sur le Site Central pour le domaine %s",
                body.version, domaine,
            )
    except SiteCentralError:
        logger.warning(
            "Site Central indisponible — installation de la version RAG %s sans vérification",
            body.version,
        )

    # Update local config (in production, would also pull Docker image from ECR)
    config.rag_version = body.version
    config.is_configured = True
    await db.commit()
    await db.refresh(config)
    return RAGInstallResponse(
        message=f"Module RAG version {body.version} installé avec succès",
        version=body.version,
    )


# ---- 5. POST /tpe ----------------------------------------------------------

@router.post("/tpe", response_model=UploadResponse)
async def upload_tpe(
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload (ou remplacement) du fichier TPE.

    Sauvegarde dans data/config/ et indexe dans la collection config_{domaine}.
    """
    config = await _get_config(db)
    _require_rag_configured(config)

    config_dir = _ensure_config_dir()
    domaine = config.domaine
    collection = f"config_{domaine}"

    # Supprimer l'ancien TPE s'il existe
    existing_tpe = _find_existing_file(config_dir, "TPE_")
    if existing_tpe:
        os.remove(existing_tpe)

    # Sauvegarder le nouveau fichier
    filename = file.filename or "TPE_upload"
    file_path = os.path.join(config_dir, filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Indexer dans le RAG
    rag = RAGService()
    try:
        # Écrire un fichier texte temporaire pour l'indexation
        text_path = file_path + ".txt"
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(content.decode("utf-8", errors="replace"))
        doc_id = await rag.index_document(
            file_path=text_path,
            collection=collection,
            metadata={"type": "tpe", "domaine": domaine},
        )
        # Nettoyer le fichier texte temporaire
        if os.path.exists(text_path):
            os.remove(text_path)
    except Exception as exc:
        logger.error("Erreur indexation TPE : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'indexation du TPE : {exc}",
        )
    finally:
        await rag.close()

    return UploadResponse(message="TPE uploadé et indexé", filename=filename, doc_id=doc_id)


# ---- 6. POST /template -----------------------------------------------------

@router.post("/template", response_model=UploadResponse)
async def upload_template(
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload (ou remplacement) du Template Rapport (.docx).

    Sauvegarde dans data/config/ et indexe dans la collection config_{domaine}.
    """
    config = await _get_config(db)
    _require_rag_configured(config)

    config_dir = _ensure_config_dir()
    domaine = config.domaine
    collection = f"config_{domaine}"

    # Supprimer l'ancien template s'il existe
    existing_template = _find_existing_file(config_dir, "template_")
    if existing_template:
        os.remove(existing_template)

    # Sauvegarder le nouveau fichier
    filename = file.filename or "template_upload.docx"
    file_path = os.path.join(config_dir, filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Indexer dans le RAG
    rag = RAGService()
    try:
        text_path = file_path + ".txt"
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(content.decode("utf-8", errors="replace"))
        doc_id = await rag.index_document(
            file_path=text_path,
            collection=collection,
            metadata={"type": "template_rapport", "domaine": domaine},
        )
        if os.path.exists(text_path):
            os.remove(text_path)
    except Exception as exc:
        logger.error("Erreur indexation Template : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'indexation du Template : {exc}",
        )
    finally:
        await rag.close()

    return UploadResponse(message="Template Rapport uploadé et indexé", filename=filename, doc_id=doc_id)


# ---- 7. GET /documents -----------------------------------------------------

@router.get("/documents", response_model=DocumentsListResponse)
async def list_documents(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Liste les documents présents dans les collections RAG config et corpus."""
    config = await _get_config(db)
    _require_rag_configured(config)

    domaine = config.domaine
    config_collection = f"config_{domaine}"
    corpus_collection = f"corpus_{domaine}"

    rag = RAGService()
    documents: list[DocumentItem] = []
    try:
        for coll_name in (config_collection, corpus_collection):
            docs = await rag.list_documents(coll_name)
            for doc in docs:
                documents.append(
                    DocumentItem(
                        doc_id=doc.doc_id,
                        filename=doc.filename,
                        doc_type=doc.doc_type,
                        chunk_count=doc.chunk_count,
                        collection=coll_name,
                    )
                )
    except Exception as exc:
        logger.error("Erreur listing documents RAG : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des documents : {exc}",
        )
    finally:
        await rag.close()

    return DocumentsListResponse(documents=documents)


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------


def _find_existing_file(directory: str, prefix: str) -> Optional[str]:
    """Trouve un fichier existant dans le répertoire commençant par le préfixe donné."""
    if not os.path.isdir(directory):
        return None
    for fname in os.listdir(directory):
        if fname.lower().startswith(prefix.lower()):
            return os.path.join(directory, fname)
    return None
