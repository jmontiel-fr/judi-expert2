"""Test par propriété — Round-trip d'indexation RAG.

**Validates: Requirements 3.5**

Propriété 13 : Pour tout document valide, l'indexation dans la base Qdrant
suivie d'une recherche par le contenu du document doit retourner le document
indexé parmi les résultats.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

# Ajouter le backend au path pour les imports
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "local-site"
        / "web"
        / "backend"
    ),
)

from services.rag_service import RAGService, RAGIndexError, _chunk_text, _doc_id


# ---------------------------------------------------------------------------
# Tests unitaires purs pour les helpers (pas besoin de Qdrant)
# ---------------------------------------------------------------------------


class TestChunkText:
    """Tests par propriété pour le découpage de texte en chunks."""

    @given(
        text=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
            min_size=1,
            max_size=500,
        ).filter(lambda s: s.strip() != ""),
    )
    @settings(max_examples=50, deadline=None)
    def test_chunking_preserves_all_words(self, text: str):
        """Tous les mots du texte original doivent apparaître dans les chunks."""
        chunks = _chunk_text(text, chunk_size=10, overlap=2)
        original_words = text.split()
        chunk_words: list[str] = []
        for chunk in chunks:
            chunk_words.extend(chunk.split())
        # Chaque mot original doit apparaître au moins une fois dans les chunks
        for word in original_words:
            assert word in chunk_words, f"Mot '{word}' absent des chunks"

    @given(
        text=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
            min_size=1,
            max_size=500,
        ).filter(lambda s: s.strip() != ""),
    )
    @settings(max_examples=50, deadline=None)
    def test_chunking_produces_nonempty_chunks(self, text: str):
        """Chaque chunk produit doit être non-vide."""
        chunks = _chunk_text(text, chunk_size=10, overlap=2)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.strip() != ""

    def test_empty_text_produces_no_chunks(self):
        """Un texte vide ne produit aucun chunk."""
        assert _chunk_text("") == []
        assert _chunk_text("   ") == []

    @given(
        text=st.text(
            alphabet=st.characters(whitelist_categories=("L",)),
            min_size=1,
            max_size=50,
        ).filter(lambda s: len(s.split()) <= 10 and s.strip() != ""),
    )
    @settings(max_examples=30, deadline=None)
    def test_short_text_single_chunk(self, text: str):
        """Un texte plus court que chunk_size produit un seul chunk."""
        chunks = _chunk_text(text, chunk_size=100, overlap=10)
        assert len(chunks) == 1
        assert chunks[0] == text


class TestDocId:
    """Tests par propriété pour la génération d'identifiants de documents."""

    @given(source=st.text(min_size=1, max_size=200))
    @settings(max_examples=50, deadline=None)
    def test_doc_id_deterministic(self, source: str):
        """Le même source produit toujours le même doc_id."""
        assert _doc_id(source) == _doc_id(source)

    @given(
        source_a=st.text(min_size=1, max_size=100),
        source_b=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=50, deadline=None)
    def test_doc_id_different_sources(self, source_a: str, source_b: str):
        """Deux sources différentes produisent (très probablement) des doc_id différents."""
        if source_a != source_b:
            # Collision possible mais extrêmement improbable sur 16 hex chars
            assert _doc_id(source_a) != _doc_id(source_b)

    @given(source=st.text(min_size=1, max_size=200))
    @settings(max_examples=30, deadline=None)
    def test_doc_id_length(self, source: str):
        """Le doc_id fait toujours 16 caractères hexadécimaux."""
        doc_id = _doc_id(source)
        assert len(doc_id) == 16
        assert all(c in "0123456789abcdef" for c in doc_id)


# ---------------------------------------------------------------------------
# Tests d'intégration RAG (nécessitent Qdrant)
# ---------------------------------------------------------------------------


@pytest.fixture
def qdrant_url():
    """URL Qdrant pour les tests. Utilise la variable d'environnement ou localhost."""
    return os.environ.get("QDRANT_TEST_URL", "http://localhost:6333")


def _qdrant_available(url: str) -> bool:
    """Vérifie si Qdrant est accessible."""
    try:
        import httpx as _httpx
        resp = _httpx.get(f"{url}/healthz", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False


def _fastembed_available() -> bool:
    """Vérifie si fastembed est installé."""
    try:
        import fastembed  # noqa: F401
        return True
    except ImportError:
        return False


@pytest_asyncio.fixture
async def rag_service(qdrant_url):
    """Crée un RAGService connecté à Qdrant de test."""
    service = RAGService(url=qdrant_url)
    yield service
    await service.close()


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _qdrant_available(os.environ.get("QDRANT_TEST_URL", "http://localhost:6333")),
    reason="Qdrant non disponible pour les tests d'intégration",
)
@pytest.mark.skipif(
    not _fastembed_available(),
    reason="fastembed non installé — requis pour l'indexation RAG",
)
@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much],
)
@given(
    content=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
        min_size=20,
        max_size=200,
    ).filter(lambda s: len(s.split()) >= 3),
)
async def test_rag_index_then_search_roundtrip(
    rag_service: RAGService,
    content: str,
):
    """Propriété 13 : un document indexé est retrouvable par recherche sur son contenu.

    Pour tout texte valide :
    1. Écrire le texte dans un fichier temporaire
    2. Indexer le fichier dans une collection de test
    3. Rechercher avec le contenu du document
    4. Vérifier que le document indexé apparaît dans les résultats
    """
    collection = "test_roundtrip"

    # Nettoyage préalable
    await rag_service.delete_collection(collection)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        tmp_path = f.name

    try:
        doc_id = await rag_service.index_document(
            file_path=tmp_path,
            collection=collection,
            metadata={"test": True},
        )

        # Recherche avec le contenu original
        results = await rag_service.search(
            query=content,
            collection=collection,
            limit=10,
        )

        # Le document doit apparaître dans les résultats
        found_doc_ids = {r.metadata.get("doc_id") for r in results}
        assert doc_id in found_doc_ids, (
            f"Document {doc_id} non trouvé dans les résultats de recherche. "
            f"IDs trouvés : {found_doc_ids}"
        )
    finally:
        os.unlink(tmp_path)
        await rag_service.delete_collection(collection)


@pytest.mark.asyncio
async def test_index_nonexistent_file_raises():
    """L'indexation d'un fichier inexistant lève RAGIndexError."""
    service = RAGService(url="http://localhost:6333")
    with pytest.raises(RAGIndexError, match="introuvable"):
        await service.index_document(
            file_path="/nonexistent/file.txt",
            collection="test",
        )
    await service.close()


@pytest.mark.asyncio
async def test_index_empty_file_raises():
    """L'indexation d'un fichier vide lève RAGIndexError."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write("   ")
        tmp_path = f.name

    service = RAGService(url="http://localhost:6333")
    try:
        with pytest.raises(RAGIndexError, match="vide"):
            await service.index_document(
                file_path=tmp_path,
                collection="test",
            )
    finally:
        os.unlink(tmp_path)
        await service.close()
