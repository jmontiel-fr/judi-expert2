"""Router Admin Chatbot — gestion de l'indexation RAG du site central."""

import logging
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from routers.admin import get_admin_expert
from services.rag_service import RAGError, RAGService

logger = logging.getLogger(__name__)

router = APIRouter()

# Fichiers docs à indexer
DOCS_DIR = os.environ.get("DOCS_PATH", "/data/docs")
CORPUS_DIR = os.environ.get("CORPUS_BASE_PATH", "/data/corpus")

DOCS_FILES = [
    "faq.md",
    "cgu.md",
    "confidentialite.md",
    "mentions_legales.md",
    "methodologie.md",
]

# Fichiers corpus à indexer (contenu.yaml + urls.yaml de chaque domaine actif)
CORPUS_FILES = [
    "contenu.yaml",
    "urls/urls.yaml",
]

# Stockage simple de la date de dernier rafraîchissement
_LAST_REFRESH_FILE = "/tmp/chatbot_last_refresh.txt"


def _get_last_refresh() -> str | None:
    """Retourne la date du dernier rafraîchissement ou None."""
    try:
        with open(_LAST_REFRESH_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def _set_last_refresh(dt: str) -> None:
    """Enregistre la date du dernier rafraîchissement."""
    with open(_LAST_REFRESH_FILE, "w") as f:
        f.write(dt)


def _discover_corpus_files() -> list[tuple[str, str]]:
    """Découvre les fichiers corpus à indexer.

    Returns:
        Liste de tuples (chemin_fichier, nom_source).
    """
    files: list[tuple[str, str]] = []
    if not os.path.isdir(CORPUS_DIR):
        return files

    for domaine in os.listdir(CORPUS_DIR):
        domaine_path = os.path.join(CORPUS_DIR, domaine)
        if not os.path.isdir(domaine_path):
            continue
        for corpus_file in CORPUS_FILES:
            file_path = os.path.join(domaine_path, corpus_file)
            if os.path.isfile(file_path):
                files.append((file_path, f"corpus/{domaine}/{corpus_file}"))
    return files


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ChatbotStatusResponse(BaseModel):
    last_refresh: str | None
    docs_indexed: int
    points_count: int
    available_docs: list[str]


class ChatbotRefreshResponse(BaseModel):
    message: str
    docs_indexed: int
    total_chunks: int
    last_refresh: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/status", response_model=ChatbotStatusResponse)
async def chatbot_status(
    _admin=Depends(get_admin_expert),
):
    """Retourne le statut du chatbot RAG (dernier refresh, nombre de docs)."""
    rag = RAGService()
    stats = await rag.get_stats()

    # Vérifier quels docs sont disponibles
    available = []
    for filename in DOCS_FILES:
        path = os.path.join(DOCS_DIR, filename)
        if os.path.isfile(path):
            available.append(filename)

    # Ajouter les fichiers corpus découverts
    corpus_files = _discover_corpus_files()
    for _, source_name in corpus_files:
        available.append(source_name)

    return ChatbotStatusResponse(
        last_refresh=_get_last_refresh(),
        docs_indexed=len(available),
        points_count=stats.get("points_count", 0),
        available_docs=available,
    )


@router.post("/refresh", response_model=ChatbotRefreshResponse)
async def chatbot_refresh(
    _admin=Depends(get_admin_expert),
):
    """Rafraîchit l'index RAG à partir des fichiers docs et corpus.

    Supprime l'ancienne collection et réindexe tous les documents.
    """
    rag = RAGService()

    # Vider et recréer la collection
    try:
        await rag.clear()
    except RAGError as e:
        logger.error("Erreur lors du clear RAG : %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la réinitialisation du RAG : {e}",
        )

    total_chunks = 0
    docs_indexed = 0

    # Indexer les fichiers docs (FAQ, CGU, etc.)
    for filename in DOCS_FILES:
        path = os.path.join(DOCS_DIR, filename)
        if not os.path.isfile(path):
            logger.warning("Fichier docs manquant : %s", path)
            continue

        try:
            chunks = await rag.index_file(path)
            total_chunks += chunks
            docs_indexed += 1
            logger.info("Indexé %s : %d chunks", filename, chunks)
        except RAGError as e:
            logger.error("Erreur indexation %s : %s", filename, e)

    # Indexer les fichiers corpus (contenu.yaml, urls.yaml de chaque domaine)
    corpus_files = _discover_corpus_files()
    for file_path, source_name in corpus_files:
        try:
            chunks = await rag.index_file(file_path)
            total_chunks += chunks
            docs_indexed += 1
            logger.info("Indexé %s : %d chunks", source_name, chunks)
        except RAGError as e:
            logger.error("Erreur indexation %s : %s", source_name, e)

    # Enregistrer la date
    now = datetime.utcnow().isoformat() + "Z"
    _set_last_refresh(now)

    return ChatbotRefreshResponse(
        message=f"{docs_indexed} documents indexés avec succès.",
        docs_indexed=docs_indexed,
        total_chunks=total_chunks,
        last_refresh=now,
    )
