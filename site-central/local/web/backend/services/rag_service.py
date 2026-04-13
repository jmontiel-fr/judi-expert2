"""
Judi-Expert — Service RAG (client Qdrant)

Service asynchrone pour l'indexation et la recherche de documents dans la base
vectorielle Qdrant. Gère les collections par domaine et fournit les méthodes
de haut niveau pour le workflow d'expertise et le ChatBot.

Valide : Exigences 3.5, 3.6, 11.2
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx
from qdrant_client import AsyncQdrantClient, models

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

QDRANT_URL: str = os.environ.get("QDRANT_URL", "http://judi-rag:6333")
EMBEDDING_MODEL: str = os.environ.get(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
# Default vector size for all-MiniLM-L6-v2
VECTOR_SIZE: int = int(os.environ.get("VECTOR_SIZE", "384"))
CHUNK_SIZE: int = int(os.environ.get("RAG_CHUNK_SIZE", "500"))
CHUNK_OVERLAP: int = int(os.environ.get("RAG_CHUNK_OVERLAP", "50"))


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Document:
    """Résultat de recherche RAG."""

    content: str
    score: float
    metadata: dict = field(default_factory=dict)


@dataclass
class DocumentInfo:
    """Informations sur un document indexé."""

    doc_id: str
    filename: str
    doc_type: str
    chunk_count: int
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class RAGError(Exception):
    """Erreur de base pour le service RAG."""


class RAGConnectionError(RAGError):
    """Impossible de se connecter à Qdrant."""


class RAGIndexError(RAGError):
    """Erreur lors de l'indexation d'un document."""


# ---------------------------------------------------------------------------
# Helpers : chunking
# ---------------------------------------------------------------------------


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Découpe un texte en chunks avec chevauchement.

    Parameters
    ----------
    text:
        Texte brut à découper.
    chunk_size:
        Nombre de mots par chunk.
    overlap:
        Nombre de mots de chevauchement entre chunks consécutifs.

    Returns
    -------
    list[str]
        Liste de chunks textuels.
    """
    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def _doc_id(source: str) -> str:
    """Génère un identifiant déterministe pour un document/URL."""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


def _point_id(doc_id: str, chunk_index: int) -> str:
    """Génère un identifiant de point Qdrant pour un chunk."""
    raw = f"{doc_id}_{chunk_index}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Service RAG
# ---------------------------------------------------------------------------


class RAGService:
    """Service asynchrone pour l'indexation et la recherche dans Qdrant.

    Gère les collections :
    - ``corpus_{domaine}`` : documents du corpus domaine (PDF, URLs)
    - ``config_{domaine}`` : TPE et Template Rapport de l'expert
    - ``system_docs`` : documentation système (user-guide, CGU, mentions légales)
    """

    def __init__(
        self,
        url: str = QDRANT_URL,
        embedding_model: str = EMBEDDING_MODEL,
        vector_size: int = VECTOR_SIZE,
    ) -> None:
        self.url = url
        self.embedding_model = embedding_model
        self.vector_size = vector_size
        self._client: Optional[AsyncQdrantClient] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> AsyncQdrantClient:
        """Retourne le client Qdrant, en le créant si nécessaire."""
        if self._client is None:
            try:
                self._client = AsyncQdrantClient(url=self.url)
            except Exception as exc:
                logger.error("Impossible de se connecter à Qdrant : %s", exc)
                raise RAGConnectionError(
                    "Impossible de se connecter à la base RAG. "
                    "Vérifiez que le conteneur judi-rag est démarré."
                ) from exc
        return self._client

    async def close(self) -> None:
        """Ferme la connexion au client Qdrant."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    async def _ensure_collection(self, collection: str) -> None:
        """Crée la collection si elle n'existe pas."""
        client = await self._get_client()
        collections = await client.get_collections()
        existing = {c.name for c in collections.collections}
        if collection not in existing:
            await client.create_collection(
                collection_name=collection,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info("Collection '%s' créée.", collection)

    async def delete_collection(self, collection: str) -> bool:
        """Supprime une collection Qdrant.

        Returns
        -------
        bool
            True si la collection a été supprimée, False si elle n'existait pas.
        """
        client = await self._get_client()
        collections = await client.get_collections()
        existing = {c.name for c in collections.collections}
        if collection not in existing:
            return False
        await client.delete_collection(collection_name=collection)
        logger.info("Collection '%s' supprimée.", collection)
        return True

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        """Génère les embeddings pour une liste de textes via FastEmbed.

        Utilise le modèle configuré (par défaut all-MiniLM-L6-v2).
        """
        # Import tardif pour éviter le chargement du modèle au démarrage
        from fastembed import TextEmbedding  # type: ignore[import-untyped]

        if not hasattr(self, "_embedding_model_instance"):
            self._embedding_model_instance = TextEmbedding(
                model_name=self.embedding_model
            )
        embeddings = list(self._embedding_model_instance.embed(texts))
        return [e.tolist() for e in embeddings]

    # ------------------------------------------------------------------
    # Indexation
    # ------------------------------------------------------------------

    async def index_document(
        self,
        file_path: str,
        collection: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """Indexe un document (texte brut lu depuis un fichier) dans Qdrant.

        Le fichier est lu, découpé en chunks, et chaque chunk est indexé
        comme un point dans la collection spécifiée.

        Parameters
        ----------
        file_path:
            Chemin vers le fichier texte à indexer.
        collection:
            Nom de la collection Qdrant cible.
        metadata:
            Métadonnées supplémentaires à associer à chaque chunk.

        Returns
        -------
        str
            Identifiant du document indexé.

        Raises
        ------
        RAGIndexError
            Si le fichier est introuvable ou vide.
        """
        if not os.path.isfile(file_path):
            raise RAGIndexError(f"Fichier introuvable : {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            raise RAGIndexError(f"Fichier vide : {file_path}")

        return await self._index_text(
            text=content,
            source=file_path,
            collection=collection,
            doc_type="document",
            filename=os.path.basename(file_path),
            metadata=metadata,
        )

    async def index_url(
        self,
        url: str,
        collection: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """Indexe le contenu d'une URL dans Qdrant.

        Télécharge le contenu textuel de l'URL, le découpe en chunks,
        et indexe chaque chunk dans la collection spécifiée.

        Parameters
        ----------
        url:
            URL à indexer.
        collection:
            Nom de la collection Qdrant cible.
        metadata:
            Métadonnées supplémentaires.

        Returns
        -------
        str
            Identifiant du document indexé.

        Raises
        ------
        RAGIndexError
            Si l'URL est inaccessible ou le contenu vide.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                response = await http_client.get(url)
                response.raise_for_status()
                content = response.text
        except Exception as exc:
            raise RAGIndexError(f"Impossible de récupérer l'URL {url} : {exc}") from exc

        if not content.strip():
            raise RAGIndexError(f"Contenu vide pour l'URL : {url}")

        # Nettoyage basique du HTML
        content = _strip_html(content)

        return await self._index_text(
            text=content,
            source=url,
            collection=collection,
            doc_type="url",
            filename=url,
            metadata=metadata,
        )

    async def _index_text(
        self,
        text: str,
        source: str,
        collection: str,
        doc_type: str,
        filename: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """Méthode interne : découpe, embed et indexe un texte."""
        await self._ensure_collection(collection)
        client = await self._get_client()

        doc_id = _doc_id(source)
        chunks = _chunk_text(text)

        if not chunks:
            raise RAGIndexError("Aucun contenu à indexer après découpage.")

        vectors = await self._embed(chunks)

        points = []
        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            payload = {
                "content": chunk,
                "doc_id": doc_id,
                "doc_type": doc_type,
                "filename": filename,
                "chunk_index": i,
                "total_chunks": len(chunks),
                **(metadata or {}),
            }
            point_id = _point_id(doc_id, i)
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            )

        await client.upsert(collection_name=collection, points=points)
        logger.info(
            "Document '%s' indexé dans '%s' (%d chunks).",
            filename,
            collection,
            len(chunks),
        )
        return doc_id

    # ------------------------------------------------------------------
    # Recherche
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        collection: str,
        limit: int = 5,
    ) -> list[Document]:
        """Recherche sémantique dans une collection Qdrant.

        Parameters
        ----------
        query:
            Texte de la requête de recherche.
        collection:
            Nom de la collection Qdrant à interroger.
        limit:
            Nombre maximum de résultats.

        Returns
        -------
        list[Document]
            Liste de documents triés par pertinence décroissante.
        """
        await self._ensure_collection(collection)
        client = await self._get_client()

        query_vector = (await self._embed([query]))[0]

        results = await client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=limit,
            with_payload=True,
        )

        documents: list[Document] = []
        for point in results.points:
            payload = point.payload or {}
            documents.append(
                Document(
                    content=payload.get("content", ""),
                    score=point.score,
                    metadata={
                        k: v
                        for k, v in payload.items()
                        if k != "content"
                    },
                )
            )
        return documents

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    async def list_documents(self, collection: str) -> list[DocumentInfo]:
        """Liste les documents indexés dans une collection.

        Agrège les chunks par ``doc_id`` pour retourner un résumé par document.

        Parameters
        ----------
        collection:
            Nom de la collection Qdrant.

        Returns
        -------
        list[DocumentInfo]
            Liste des documents avec leur nombre de chunks.
        """
        await self._ensure_collection(collection)
        client = await self._get_client()

        # Scroll all points to aggregate by doc_id
        docs_map: dict[str, DocumentInfo] = {}
        offset = None
        while True:
            scroll_kwargs: dict = {
                "collection_name": collection,
                "limit": 100,
                "with_payload": True,
                "with_vectors": False,
            }
            if offset is not None:
                scroll_kwargs["offset"] = offset

            points, next_offset = await client.scroll(**scroll_kwargs)

            for point in points:
                payload = point.payload or {}
                doc_id = payload.get("doc_id", "unknown")
                if doc_id not in docs_map:
                    docs_map[doc_id] = DocumentInfo(
                        doc_id=doc_id,
                        filename=payload.get("filename", "unknown"),
                        doc_type=payload.get("doc_type", "unknown"),
                        chunk_count=0,
                        metadata={
                            k: v
                            for k, v in payload.items()
                            if k not in ("content", "doc_id", "doc_type", "filename", "chunk_index", "total_chunks")
                        },
                    )
                docs_map[doc_id].chunk_count += 1

            if next_offset is None:
                break
            offset = next_offset

        return list(docs_map.values())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_html(text: str) -> str:
    """Supprime les balises HTML basiques d'un texte."""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()
