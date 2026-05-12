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
from services.corpus_service import CorpusService
from services.hardware_service import PROFILES, HardwareInfo, ProfileSelector
from services.llm_service import (
    ActiveProfile,
    ModelDownloadManager,
    ModelDownloadStatus,
    get_all_step_durations,
)
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

# Module-level model download manager instance
_download_manager = ModelDownloadManager()

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


# ---- 0. GET /rag-status — État du RAG local --------------------------------


class RAGStatusResponse(BaseModel):
    is_configured: bool
    rag_built_at: Optional[str] = None
    corpus_downloaded_at: Optional[str] = None
    documents_count: int = 0


@router.get("/rag-status", response_model=RAGStatusResponse)
async def get_rag_status(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retourne l'état du RAG local : dates de build/téléchargement, nombre de docs."""
    config = await _get_config(db)

    # Compter les documents indexés
    doc_count = 0
    if config.is_configured and config.rag_version is not None:
        domaine = config.domaine
        rag = RAGService()
        try:
            for coll_name in (f"config_{domaine}", f"corpus_{domaine}"):
                docs = await rag.list_documents(coll_name)
                doc_count += len(docs)
        except Exception:
            pass
        finally:
            await rag.close()

    return RAGStatusResponse(
        is_configured=config.is_configured,
        rag_built_at=str(config.rag_built_at) if config.rag_built_at else None,
        corpus_downloaded_at=str(config.corpus_downloaded_at) if config.corpus_downloaded_at else None,
        documents_count=doc_count,
    )


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
    """Upload (ou remplacement) du fichier TPE (.docx ou .md).

    Sauvegarde dans data/config/. Si le RAG est configuré, indexe dans
    la collection config_{domaine}. Sinon, stocke uniquement sur disque.
    """
    config = await _get_config(db)

    # Valider le format
    filename = file.filename or "TPE_upload"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".docx", ".md"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le TPE doit être au format .docx ou .md",
        )

    config_dir = _ensure_config_dir()
    domaine = config.domaine

    # Supprimer l'ancien TPE s'il existe
    existing_tpe = _find_existing_file(config_dir, "TPE_")
    if existing_tpe:
        os.remove(existing_tpe)

    # Sauvegarder le nouveau fichier
    safe_filename = f"TPE_{domaine}{ext}"
    file_path = os.path.join(config_dir, safe_filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Indexer dans le RAG si configuré (optionnel)
    doc_id = "local-only"
    if config.rag_version is not None:
        collection = f"config_{domaine}"
        rag = RAGService()
        try:
            # Supprimer l'ancien TPE du RAG (par défaut ou custom précédent)
            await rag.delete_by_metadata(collection, "type", "tpe")

            # Indexer le nouveau
            text_path = file_path + ".txt"
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(content.decode("utf-8", errors="replace"))
            doc_id = await rag.index_document(
                file_path=text_path,
                collection=collection,
                metadata={"type": "tpe", "domaine": domaine},
            )
            if os.path.exists(text_path):
                os.remove(text_path)
        except Exception as exc:
            logger.warning("Indexation RAG du TPE échouée (non bloquant) : %s", exc)
            doc_id = "index-failed"
        finally:
            await rag.close()

    return UploadResponse(message="TPE uploadé avec succès", filename=safe_filename, doc_id=doc_id)


# ---- 6. POST /template -----------------------------------------------------

@router.post("/template", response_model=UploadResponse)
async def upload_template(
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload (ou remplacement) du Template Rapport (.docx).

    Sauvegarde dans data/config/. Si le RAG est configuré, indexe dans
    la collection config_{domaine}. Sinon, stocke uniquement sur disque.
    """
    config = await _get_config(db)

    # Valider le format
    filename = file.filename or "template_upload.docx"
    ext = os.path.splitext(filename)[1].lower()
    if ext != ".docx":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le Template Rapport doit être au format .docx",
        )

    config_dir = _ensure_config_dir()
    domaine = config.domaine

    # Supprimer l'ancien template s'il existe
    existing_template = _find_existing_file(config_dir, "template_")
    if existing_template:
        os.remove(existing_template)

    # Sauvegarder le nouveau fichier
    safe_filename = f"template_{domaine}.docx"
    file_path = os.path.join(config_dir, safe_filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Indexer dans le RAG si configuré (optionnel)
    doc_id = "local-only"
    if config.rag_version is not None:
        collection = f"config_{domaine}"
        rag = RAGService()
        try:
            # Supprimer l'ancien template du RAG
            await rag.delete_by_metadata(collection, "type", "template_rapport")

            # Indexer le nouveau
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
            logger.warning("Indexation RAG du Template échouée (non bloquant) : %s", exc)
            doc_id = "index-failed"
        finally:
            await rag.close()

    return UploadResponse(message="Template Rapport uploadé avec succès", filename=safe_filename, doc_id=doc_id)


# ---- 6b. GET /tpe/download — Télécharger le TPE installé --------------------

@router.get("/tpe/download")
async def download_tpe(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Télécharge le fichier TPE actuellement installé."""
    from fastapi.responses import FileResponse

    config = await _get_config(db)
    config_dir = _ensure_config_dir()

    tpe_path = _find_existing_file(config_dir, "TPE_")
    if not tpe_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun TPE installé",
        )

    filename = os.path.basename(tpe_path)
    ext = os.path.splitext(filename)[1].lower()
    media_types = {".md": "text/markdown", ".tpl": "text/markdown", ".txt": "text/plain"}
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(path=tpe_path, filename=filename, media_type=media_type)


# ---- 6c. GET /template/download — Télécharger le Template installé -----------

@router.get("/template/download")
async def download_template(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Télécharge le fichier Template Rapport actuellement installé."""
    from fastapi.responses import FileResponse

    config = await _get_config(db)
    config_dir = _ensure_config_dir()

    template_path = _find_existing_file(config_dir, "template_")
    if not template_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun Template Rapport installé",
        )

    filename = os.path.basename(template_path)
    return FileResponse(
        path=template_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# ---- 6d. GET /tpe/info — Infos sur le TPE installé --------------------------

@router.get("/tpe/info")
async def get_tpe_info(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retourne les infos du TPE installé (nom, taille) ou 404 si absent."""
    config = await _get_config(db)
    config_dir = _ensure_config_dir()

    tpe_path = _find_existing_file(config_dir, "TPE_")
    if not tpe_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun TPE installé",
        )

    return {
        "filename": os.path.basename(tpe_path),
        "size": os.path.getsize(tpe_path),
        "installed": True,
    }


# ---- 6e. GET /template/info — Infos sur le Template installé -----------------

@router.get("/template/info")
async def get_template_info(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retourne les infos du Template installé (nom, taille) ou 404 si absent."""
    config = await _get_config(db)
    config_dir = _ensure_config_dir()

    template_path = _find_existing_file(config_dir, "template_")
    if not template_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun Template Rapport installé",
        )

    return {
        "filename": os.path.basename(template_path),
        "size": os.path.getsize(template_path),
        "installed": True,
    }


# ---- 7. GET /documents -----------------------------------------------------

@router.get("/documents", response_model=DocumentsListResponse)
async def list_documents(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Liste les documents présents dans les collections RAG config et corpus."""
    config = await _get_config(db)

    # Si RAG pas configuré, retourner une liste vide
    if not config.is_configured or config.rag_version is None:
        return DocumentsListResponse(documents=[])

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


# ---------------------------------------------------------------------------
# Corpus RAG — Initialisation, rebuild, reset, ajout/suppression
# ---------------------------------------------------------------------------


class CorpusActionResponse(BaseModel):
    message: str
    indexed: int = 0
    errors: list[str] = []


class CorpusDocumentItem(BaseModel):
    filename: str
    type: str
    collection: str
    source: str  # "default" ou "custom"


class CorpusListResponse(BaseModel):
    documents: list[CorpusDocumentItem]
    rag_initialized: bool


# ---- POST /corpus/initialize — Initialiser le corpus (premier démarrage) ---

@router.post("/corpus/initialize")
async def initialize_corpus(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initialise le corpus RAG avec les documents par défaut (streaming SSE)."""
    from fastapi.responses import StreamingResponse
    import json

    config = await _get_config(db)
    domaine = config.domaine

    async def stream_initialize():
        service = CorpusService(domaine)
        rag = RAGService()
        indexed = 0
        errors = []

        try:
            yield f"data: {json.dumps({'log': 'Suppression des collections existantes…'})}\n\n"
            await rag.delete_collection(service.config_collection)
            await rag.delete_collection(service.corpus_collection)

            yield f"data: {json.dumps({'log': 'Téléchargement de la liste du corpus depuis le Site Central…'})}\n\n"
            contenu_items = await service._fetch_contenu_from_central()

            if contenu_items:
                yield f"data: {json.dumps({'log': f'{len(contenu_items)} éléments trouvés sur le Site Central'})}\n\n"

                for item in contenu_items:
                    nom = item.get("nom", "")
                    item_type = item.get("type", "document")

                    # Ignorer les templates (TPE/TRE) — gérés séparément
                    if item_type == "template":
                        yield f"data: {json.dumps({'log': f'  ⏭ Ignoré (template) : {nom}'})}\n\n"
                        continue

                    collection = service.corpus_collection

                    yield f"data: {json.dumps({'log': f'Téléchargement : {nom}…'})}\n\n"

                    try:
                        content = await service._download_file_from_central(nom)
                        if not content:
                            yield f"data: {json.dumps({'log': f'  ⚠ Non trouvé : {nom}'})}\n\n"
                            continue

                        safe_name = nom.replace("/", "_")
                        cache_dir = service._ensure_cache_dir()
                        cache_path = os.path.join(cache_dir, safe_name)
                        with open(cache_path, "wb") as f:
                            f.write(content)

                        text = service._read_document_text(cache_path)
                        if text.strip():
                            await rag.index_document(
                                file_path=None,
                                collection=collection,
                                metadata={
                                    "type": item_type,
                                    "filename": safe_name,
                                    "domaine": domaine,
                                    "description": item.get("description", ""),
                                },
                                text_content=text,
                            )
                            indexed += 1
                            yield f"data: {json.dumps({'log': f'  ✔ Indexé : {safe_name}'})}\n\n"
                        else:
                            yield f"data: {json.dumps({'log': f'  ⚠ Contenu vide : {safe_name}'})}\n\n"
                    except Exception as exc:
                        errors.append(f"{nom}: {exc}")
                        yield f"data: {json.dumps({'log': f'  ✕ Erreur : {nom} — {exc}'})}\n\n"
            else:
                yield f"data: {json.dumps({'log': 'Site Central indisponible — indexation des fichiers locaux'})}\n\n"
                for doc in service._get_default_documents():
                    try:
                        text = service._read_document_text(doc["path"])
                        if text.strip():
                            await rag.index_document(
                                file_path=None,
                                collection=doc["collection"],
                                metadata={"type": doc["type"], "filename": doc["filename"], "domaine": domaine},
                                text_content=text,
                            )
                            indexed += 1
                            fname = doc["filename"]
                            yield f"data: {json.dumps({'log': f'  ✔ Indexé local : {fname}'})}\n\n"
                    except Exception as exc:
                        errors.append(f"{doc['filename']}: {exc}")
                        fname = doc["filename"]
                        yield f"data: {json.dumps({'log': f'  ✕ Erreur : {fname} — {exc}'})}\n\n"

            # Note : les documents custom de l'expert sont conservés
            # Seul le cache central est re-téléchargé

            # Télécharger les contenus pré-crawlés des URLs
            yield f"data: {json.dumps({'log': 'Téléchargement des contenus pré-crawlés (URLs)…'})}\n\n"
            try:
                client = SiteCentralClient()
                urls_resp = await client.get(f"/api/corpus/{domaine}/urls")
                if urls_resp.status_code == 200:
                    url_items = urls_resp.json()
                    cache_dir = service._ensure_cache_dir()
                    for idx, url_item in enumerate(url_items):
                        url_nom = url_item.get("nom", f"url_{idx}")
                        try:
                            content_resp = await client.get(f"/api/corpus/{domaine}/urls/{idx}/content")
                            if content_resp.status_code == 200:
                                safe_name = f"url_{idx}_{url_nom[:30].replace(' ', '_')}.url.txt"
                                safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._-")
                                cache_path = os.path.join(cache_dir, safe_name)
                                with open(cache_path, "w", encoding="utf-8") as f:
                                    f.write(content_resp.text)
                                indexed += 1
                                yield f"data: {json.dumps({'log': f'  ✔ URL pré-crawlée : {url_nom}'})}\n\n"
                            else:
                                yield f"data: {json.dumps({'log': f'  ⚠ Non pré-crawlée : {url_nom}'})}\n\n"
                        except Exception as exc:
                            yield f"data: {json.dumps({'log': f'  ⚠ Erreur URL {url_nom} : {exc}'})}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'log': f'  ⚠ URLs non récupérées : {exc}'})}\n\n"

        finally:
            await rag.close()

        # Mettre à jour la config (re-fetch pour éviter les problèmes de session expirée)
        from datetime import datetime, UTC
        result = await db.execute(select(LocalConfig).limit(1))
        config_fresh = result.scalar_one_or_none()
        if config_fresh:
            config_fresh.rag_version = "default-1.0"
            config_fresh.is_configured = True
            config_fresh.corpus_downloaded_at = datetime.now(UTC)
            await db.commit()

        yield f"data: {json.dumps({'log': f'✔ Terminé — {indexed} documents indexés', 'done': True, 'indexed': indexed, 'errors': errors})}\n\n"

    return StreamingResponse(stream_initialize(), media_type="text/event-stream")


# ---- POST /corpus/rebuild — Reconstruire le RAG (défaut + custom) ----------

@router.post("/corpus/rebuild", response_model=CorpusActionResponse)
async def rebuild_corpus(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reconstruit le RAG avec les documents par défaut + personnalisés."""
    config = await _get_config(db)
    service = CorpusService(config.domaine)

    result = await service.rebuild()

    # Mettre à jour la date du dernier build
    from datetime import datetime, UTC
    config.rag_built_at = datetime.now(UTC)
    config.is_configured = True
    await db.commit()

    # Construire un message détaillé avec les chunks par document
    details = result.get("details", [])
    detail_lines = [f"  • {d['filename']} ({d['source']}) — {d['chunks']} chunks, {d['chars']} chars" for d in details]
    detail_msg = "\n".join(detail_lines) if detail_lines else ""

    return CorpusActionResponse(
        message=f"Corpus reconstruit — {result['indexed']} documents indexés",
        indexed=result["indexed"],
        errors=result["errors"],
    )


# ---- POST /corpus/reset — Reset to original (supprimer custom + ré-indexer) -

@router.post("/corpus/reset")
async def reset_corpus(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Réinitialise le corpus — redirige vers initialize (même logique)."""
    return await initialize_corpus(_user, db)


# ---- POST /corpus/add — Ajouter un document personnalisé -------------------

@router.post("/corpus/add", response_model=UploadResponse)
async def add_corpus_document(
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ajoute un document personnalisé au corpus et l'indexe dans le RAG."""
    config = await _get_config(db)

    filename = file.filename or "document_custom"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".pdf", ".md", ".txt", ".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formats acceptés : .pdf, .md, .txt, .docx",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier est vide",
        )

    service = CorpusService(config.domaine)
    result = await service.add_document(filename, content)

    return UploadResponse(
        message=f"Document '{filename}' ajouté au corpus",
        filename=result["filename"],
        doc_id=result["doc_id"],
    )


# ---- DELETE /corpus/{filename} — Supprimer un document personnalisé ---------

@router.delete("/corpus/{filename}")
async def remove_corpus_document(
    filename: str,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Supprime un document personnalisé du corpus."""
    config = await _get_config(db)
    service = CorpusService(config.domaine)

    deleted = await service.remove_document(filename)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document non trouvé dans le corpus personnalisé",
        )

    return {"message": f"Document '{filename}' supprimé du corpus"}


# ---- GET /corpus/list — Lister tous les documents du corpus -----------------

@router.get("/corpus/list", response_model=CorpusListResponse)
async def list_corpus_documents(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Liste tous les documents du corpus (par défaut + personnalisés)."""
    config = await _get_config(db)
    service = CorpusService(config.domaine)

    docs = service.list_all_documents()
    rag_initialized = config.rag_version is not None

    return CorpusListResponse(
        documents=[CorpusDocumentItem(**d) for d in docs],
        rag_initialized=rag_initialized,
    )


# ---- GET /defaults/tpe — Télécharger le TPE par défaut depuis le Site Central

@router.get("/defaults/tpe")
async def get_default_tpe(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Télécharge le TPE par défaut depuis le Site Central et le retourne."""
    from fastapi.responses import Response

    config = await _get_config(db)
    domaine = config.domaine

    client = SiteCentralClient()
    try:
        resp = await client.get(f"/api/corpus/{domaine}/fichier/TPE_{domaine}.tpl")
    except SiteCentralError as exc:
        raise HTTPException(status_code=503, detail=exc.message)

    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail="TPE par défaut non trouvé sur le Site Central")

    return Response(
        content=resp.content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="TPE_{domaine}.md"'},
    )


# ---- GET /defaults/template — Télécharger le Template par défaut depuis le Site Central

@router.get("/defaults/template")
async def get_default_template(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Télécharge le Template Rapport par défaut depuis le Site Central et le retourne."""
    from fastapi.responses import Response

    config = await _get_config(db)
    domaine = config.domaine

    client = SiteCentralClient()
    try:
        resp = await client.get(f"/api/corpus/{domaine}/fichier/template_rapport_{domaine}.docx")
    except SiteCentralError as exc:
        raise HTTPException(status_code=503, detail=exc.message)

    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Template par défaut non trouvé sur le Site Central")

    return Response(
        content=resp.content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="template_rapport_{domaine}.docx"'},
    )


# ---- GET /corpus/central-contenu — Récupérer le contenu corpus depuis le Site Central

@router.get("/corpus/central-contenu")
async def get_central_contenu(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Récupère la liste du contenu corpus depuis le Site Central (documents)."""
    config = await _get_config(db)
    domaine = config.domaine

    client = SiteCentralClient()
    try:
        resp = await client.get(f"/api/corpus/{domaine}/contenu")
        if resp.status_code == 200:
            items = resp.json()
            # Filtrer les templates
            docs = [item for item in items if item.get("type") != "template"]
            return {"documents": docs}
        return {"documents": []}
    except SiteCentralError:
        return {"documents": []}


# ---- GET /corpus/central-urls — Récupérer les URLs depuis le Site Central

@router.get("/corpus/central-urls")
async def get_central_urls(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Récupère la liste des URLs de référence depuis le Site Central."""
    config = await _get_config(db)
    domaine = config.domaine

    client = SiteCentralClient()
    try:
        resp = await client.get(f"/api/corpus/{domaine}/urls")
        if resp.status_code == 200:
            return {"urls": resp.json()}
        return {"urls": []}
    except SiteCentralError:
        return {"urls": []}


# ---- POST /corpus/crawl-url — Pré-crawler une URL custom (local) ----------


class CrawlUrlRequest(BaseModel):
    url: str = Field(..., min_length=1, description="URL à pré-crawler")


class CrawlUrlResponse(BaseModel):
    message: str
    filename: str
    chars: int


@router.post("/corpus/crawl-url", response_model=CrawlUrlResponse)
async def crawl_custom_url(
    body: CrawlUrlRequest,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pré-crawle une URL custom et stocke le contenu textuel dans le corpus.

    Le texte extrait est sauvegardé dans le répertoire custom et sera
    indexé au prochain "Build RAG".
    """
    import re
    import hashlib

    config = await _get_config(db)
    service = CorpusService(config.domaine)
    custom_dir = service._ensure_custom_dir()

    url = body.url.strip()

    # Télécharger le contenu
    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "JudiExpert-Crawler/1.0"},
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"URL inaccessible (HTTP {resp.status_code})",
                )

            content_type = resp.headers.get("content-type", "")

            # Si c'est un PDF, le stocker directement
            if "pdf" in content_type or url.lower().endswith(".pdf"):
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', url.split("/")[-1] or "document")[:50]
                if not safe_name.endswith(".pdf"):
                    safe_name += ".pdf"
                filename = f"dl_{url_hash}_{safe_name}"
                file_path = os.path.join(custom_dir, filename)
                with open(file_path, "wb") as f:
                    f.write(resp.content)
                return CrawlUrlResponse(
                    message=f"PDF téléchargé : {filename}",
                    filename=filename,
                    chars=len(resp.content),
                )

            # Sinon, extraire le texte HTML
            if "html" in content_type:
                text = _extract_text_from_html(resp.text)
            else:
                text = resp.text

            if not text.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Contenu vide après extraction",
                )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timeout lors du téléchargement de l'URL",
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Impossible de se connecter à l'URL",
        )

    # Sauvegarder le texte extrait dans le corpus custom
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    domain_part = re.sub(r'https?://(www\.)?', '', url).split('/')[0]
    safe_domain = re.sub(r'[^a-zA-Z0-9.-]', '_', domain_part)[:30]
    filename = f"{safe_domain}_{url_hash}.url.txt"
    file_path = os.path.join(custom_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)

    return CrawlUrlResponse(
        message=f"URL pré-crawlée : {len(text)} caractères extraits",
        filename=filename,
        chars=len(text),
    )


def _extract_text_from_html(html: str) -> str:
    """Extrait le texte principal d'une page HTML."""
    import re as _re
    text = _re.sub(r'<script[^>]*>.*?</script>', '', html, flags=_re.DOTALL | _re.IGNORECASE)
    text = _re.sub(r'<style[^>]*>.*?</style>', '', text, flags=_re.DOTALL | _re.IGNORECASE)
    text = _re.sub(r'<[^>]+>', ' ', text)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = _re.sub(r'\s+', ' ', text).strip()
    return text[:50000]


# ---- GET /corpus/file-content/{filename} — Lire le contenu d'un fichier custom

@router.get("/corpus/file-content/{filename}")
async def get_corpus_file_content(
    filename: str,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retourne le contenu textuel d'un fichier du corpus custom.

    Utile pour lire l'URL stockée dans un fichier .url.txt.
    """
    config = await _get_config(db)
    service = CorpusService(config.domaine)

    # Sécurité : empêcher la traversée de répertoire
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nom de fichier invalide",
        )

    file_path = os.path.join(service.custom_dir, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier non trouvé",
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur de lecture du fichier",
        )

    return {"filename": filename, "content": content}


# ---------------------------------------------------------------------------
# Hardware Performance Tuning — Schemas & Endpoints
# ---------------------------------------------------------------------------


class HardwareInfoResponse(BaseModel):
    """Detected hardware information response."""

    cpu_model: str
    cpu_freq_ghz: float
    cpu_cores: int
    ram_total_gb: float
    gpu_name: str | None
    gpu_vram_gb: float | None


class ProfileResponse(BaseModel):
    """Single performance profile response."""

    name: str
    display_name: str
    ram_range: str
    ctx_max: int
    model: str
    rag_chunks: int
    tokens_per_sec: float
    step_durations: dict[str, str]


class PerformanceProfileResponse(BaseModel):
    """Full performance profile response with hardware info."""

    active_profile: ProfileResponse
    is_override: bool
    auto_detected_profile: str
    all_profiles: list[ProfileResponse]
    hardware_info: HardwareInfoResponse


# ---- GET /hardware-info — Informations matérielles détectées ----------------


@router.get("/hardware-info", response_model=HardwareInfoResponse)
async def get_hardware_info(
    _user: dict = Depends(get_current_user),
):
    """Return detected hardware information."""
    hw = ActiveProfile.get_hardware_info()
    if hw is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hardware not yet detected",
        )
    return HardwareInfoResponse(
        cpu_model=hw.cpu_model,
        cpu_freq_ghz=hw.cpu_freq_ghz,
        cpu_cores=hw.cpu_cores,
        ram_total_gb=hw.ram_total_gb,
        gpu_name=hw.gpu_name,
        gpu_vram_gb=hw.gpu_vram_gb,
    )


# ---- GET /performance-profile — Profil actif + tous les profils -------------


@router.get("/performance-profile", response_model=PerformanceProfileResponse)
async def get_performance_profile(
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return active profile, all profiles, and hardware info."""
    hw = ActiveProfile.get_hardware_info()
    if hw is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hardware not yet detected",
        )

    profile = ActiveProfile.get_profile()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Performance profile not yet initialized",
        )

    # Determine if override is active
    config = await _get_config(db)
    is_override = config.performance_profile_override is not None

    # Compute auto-detected profile name
    selector = ProfileSelector()
    auto_detected = selector.select(hw)

    # Build active profile response with step durations
    active_durations = get_all_step_durations(profile.tokens_per_sec)
    active_profile_resp = ProfileResponse(
        name=profile.name,
        display_name=profile.display_name,
        ram_range=profile.ram_range,
        ctx_max=profile.ctx_max,
        model=profile.model,
        rag_chunks=profile.rag_chunks,
        tokens_per_sec=profile.tokens_per_sec,
        step_durations=active_durations,
    )

    # Build all profiles list with step durations
    all_profiles: list[ProfileResponse] = []
    for p in PROFILES.values():
        # Compute tokens_per_sec for each profile using actual hardware
        tps = selector.compute_tokens_per_sec(hw)
        durations = get_all_step_durations(tps)
        all_profiles.append(
            ProfileResponse(
                name=p.name,
                display_name=p.display_name,
                ram_range=p.ram_range,
                ctx_max=p.ctx_max,
                model=p.model,
                rag_chunks=p.rag_chunks,
                tokens_per_sec=tps,
                step_durations=durations,
            )
        )

    hardware_info_resp = HardwareInfoResponse(
        cpu_model=hw.cpu_model,
        cpu_freq_ghz=hw.cpu_freq_ghz,
        cpu_cores=hw.cpu_cores,
        ram_total_gb=hw.ram_total_gb,
        gpu_name=hw.gpu_name,
        gpu_vram_gb=hw.gpu_vram_gb,
    )

    return PerformanceProfileResponse(
        active_profile=active_profile_resp,
        is_override=is_override,
        auto_detected_profile=auto_detected.name,
        all_profiles=all_profiles,
        hardware_info=hardware_info_resp,
    )


# ---- PUT /performance-profile/override — Override manuel du profil ----------


class OverrideRequest(BaseModel):
    """Request body for setting a manual profile override."""

    profile_name: str | None = None  # None = revert to auto


@router.put("/performance-profile/override")
async def set_performance_override(
    request: OverrideRequest,
    _user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply a manual profile override or revert to auto.

    Validates the profile name, persists the override to the database,
    applies the new profile to ActiveProfile immediately, and triggers
    a model download if the new profile requires a different model.
    """
    # 1. Validate profile name (if not None)
    if request.profile_name is not None and request.profile_name not in PROFILES:
        raise HTTPException(
            status_code=400,
            detail=f"Profil inconnu: {request.profile_name}",
        )

    # 2. Persist to DB
    config = await _get_config(db)
    config.performance_profile_override = request.profile_name
    await db.commit()

    # 3. Apply new profile
    hw = ActiveProfile.get_hardware_info()
    if hw is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hardware not yet detected",
        )

    selector = ProfileSelector()
    new_profile = selector.get_active_profile(hw, request.profile_name)
    ActiveProfile.set(new_profile, hw)

    # 4. Trigger model download if model changed
    await _download_manager.check_and_pull_if_needed(new_profile.model)

    return {"status": "ok", "active_profile": new_profile.name}


# ---- GET /model-download-status — État du téléchargement de modèle ----------


class ModelDownloadStatusResponse(BaseModel):
    """Response for model download status."""

    needed: bool
    in_progress: bool
    progress_percent: float | None = None
    error: str | None = None


@router.get("/model-download-status", response_model=ModelDownloadStatusResponse)
async def get_model_download_status(
    _user: dict = Depends(get_current_user),
):
    """Return current model download status."""
    dl_status = _download_manager.get_status()
    return ModelDownloadStatusResponse(
        needed=dl_status.needed,
        in_progress=dl_status.in_progress,
        progress_percent=dl_status.progress_percent,
        error=dl_status.error,
    )
