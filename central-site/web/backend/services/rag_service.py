"""
Judi-Expert — Service RAG Site Central (client Qdrant)

Service asynchrone pour l'indexation et la recherche de documents
dans la base vectorielle Qdrant. Indexe les docs du site central
(FAQ, CGU, mentions légales, méthodologie, confidentialité).
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

from qdrant_client import AsyncQdrantClient, models

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

QDRANT_URL: str = os.environ.get("QDRANT_URL", "http://localhost:6333")
EMBEDDING_MODEL: str = os.environ.get(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
VECTOR_SIZE: int = int(os.environ.get("VECTOR_SIZE", "384"))
CHUNK_SIZE: int = int(os.environ.get("RAG_CHUNK_SIZE", "500"))
CHUNK_OVERLAP: int = int(os.environ.get("RAG_CHUNK_OVERLAP", "50"))

COLLECTION_NAME: str = "central_docs"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Document:
    """Résultat de recherche RAG."""

    content: str
    score: float
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


def _chunk_text(
    text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """Découpe un texte en chunks avec chevauchement (par mots)."""
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
    """Génère un identifiant déterministe pour un document."""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


def _point_id(doc_id: str, chunk_index: int) -> str:
    """Génère un identifiant de point Qdrant pour un chunk."""
    raw = f"{doc_id}_{chunk_index}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Service RAG
# ---------------------------------------------------------------------------


class RAGService:
    """Service asynchrone pour l'indexation et la recherche dans Qdrant."""

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

    async def _get_client(self) -> AsyncQdrantClient:
        """Retourne le client Qdrant, en le créant si nécessaire."""
        if self._client is None:
            try:
                self._client = AsyncQdrantClient(url=self.url)
            except Exception as exc:
                logger.error("Impossible de se connecter à Qdrant : %s", exc)
                raise RAGConnectionError(
                    "Impossible de se connecter à la base RAG."
                ) from exc
        return self._client

    async def close(self) -> None:
        """Ferme la connexion au client Qdrant."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def _ensure_collection(self) -> None:
        """Crée la collection si elle n'existe pas."""
        client = await self._get_client()
        collections = await client.get_collections()
        existing = {c.name for c in collections.collections}
        if COLLECTION_NAME not in existing:
            await client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info("Collection '%s' créée.", COLLECTION_NAME)

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        """Génère les embeddings via FastEmbed."""
        from fastembed import TextEmbedding  # type: ignore[import-untyped]

        if not hasattr(self, "_embedding_model_instance"):
            self._embedding_model_instance = TextEmbedding(
                model_name=self.embedding_model
            )
        embeddings = list(self._embedding_model_instance.embed(texts))
        return [e.tolist() for e in embeddings]

    async def index_text(
        self,
        text: str,
        source: str,
        metadata: Optional[dict] = None,
    ) -> int:
        """Indexe un texte dans la collection central_docs.

        Returns:
            Nombre de chunks indexés.
        """
        await self._ensure_collection()
        client = await self._get_client()

        chunks = _chunk_text(text)
        if not chunks:
            return 0

        doc_id = _doc_id(source)

        # Supprimer les anciens points de ce document
        try:
            await client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="doc_id",
                                match=models.MatchValue(value=doc_id),
                            )
                        ]
                    )
                ),
            )
        except Exception:
            pass  # Collection peut être vide

        # Embeddings
        embeddings = await self._embed(chunks)

        # Upsert
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = _point_id(doc_id, i)
            payload = {
                "content": chunk,
                "source": source,
                "doc_id": doc_id,
                "chunk_index": i,
                **(metadata or {}),
            }
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            )

        await client.upsert(collection_name=COLLECTION_NAME, points=points)
        logger.info("Indexé %d chunks pour '%s'", len(points), source)
        return len(points)

    async def index_file(self, file_path: str) -> int:
        """Indexe un fichier markdown dans Qdrant.

        Returns:
            Nombre de chunks indexés.
        """
        if not os.path.isfile(file_path):
            raise RAGIndexError(f"Fichier introuvable : {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            raise RAGIndexError(f"Fichier vide : {file_path}")

        return await self.index_text(
            text=content,
            source=os.path.basename(file_path),
            metadata={"filename": os.path.basename(file_path)},
        )

    async def search(self, query: str, limit: int = 5) -> list[Document]:
        """Recherche les chunks les plus pertinents pour une requête.

        Returns:
            Liste de Documents triés par pertinence.
        """
        await self._ensure_collection()
        client = await self._get_client()

        query_embedding = (await self._embed([query]))[0]

        results = await client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding,
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
                        "source": payload.get("source", ""),
                        "filename": payload.get("filename", ""),
                    },
                )
            )
        return documents

    async def clear(self) -> None:
        """Supprime et recrée la collection."""
        client = await self._get_client()
        collections = await client.get_collections()
        existing = {c.name for c in collections.collections}
        if COLLECTION_NAME in existing:
            await client.delete_collection(collection_name=COLLECTION_NAME)
        await self._ensure_collection()
        logger.info("Collection '%s' vidée et recréée.", COLLECTION_NAME)

    async def get_stats(self) -> dict:
        """Retourne les statistiques de la collection."""
        try:
            client = await self._get_client()
            collections = await client.get_collections()
            existing = {c.name for c in collections.collections}
            if COLLECTION_NAME not in existing:
                return {"points_count": 0, "exists": False}
            info = await client.get_collection(collection_name=COLLECTION_NAME)
            return {
                "points_count": info.points_count,
                "exists": True,
            }
        except Exception:
            return {"points_count": 0, "exists": False}
