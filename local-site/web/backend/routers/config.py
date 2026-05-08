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

            # Nettoyer les documents custom
            if os.path.isdir(service.custom_dir):
                shutil.rmtree(service.custom_dir)

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

        # Mettre à jour la config
        config.rag_version = "default-1.0"
        config.is_configured = True
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
