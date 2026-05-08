"""Service de gestion du corpus RAG — indexation, reset, ajout/suppression.

Gère l'indexation des documents du corpus par défaut (depuis le répertoire
corpus/{domaine}/ ou téléchargé depuis le Site Central) et les modifications
personnalisées de l'expert.

Le corpus par défaut est monté en lecture seule dans le conteneur à /data/corpus/.
Les documents personnalisés sont stockés dans data/config/corpus_custom/.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

import httpx

from services.rag_service import RAGService

logger = logging.getLogger(__name__)

# Répertoire du corpus par défaut (monté depuis le repo)
CORPUS_BASE_DIR: str = os.environ.get("CORPUS_DIR", "/data/corpus")

# Répertoire des documents personnalisés de l'expert
CUSTOM_CORPUS_DIR: str = os.environ.get("CUSTOM_CORPUS_DIR", "data/config/corpus_custom")

# Répertoire de cache des fichiers téléchargés depuis le Site Central
CORPUS_CACHE_DIR: str = os.environ.get("CORPUS_CACHE_DIR", "data/config/corpus_cache")

# URL du Site Central
SITE_CENTRAL_URL: str = os.environ.get("SITE_CENTRAL_URL", "http://host.docker.internal:8002")


class CorpusService:
    """Service de gestion du corpus RAG."""

    def __init__(self, domaine: str):
        self.domaine = domaine
        self.corpus_dir = os.path.join(CORPUS_BASE_DIR, domaine)
        self.custom_dir = CUSTOM_CORPUS_DIR
        self.cache_dir = CORPUS_CACHE_DIR
        self.config_collection = f"config_{domaine}"
        self.corpus_collection = f"corpus_{domaine}"

    def _ensure_custom_dir(self) -> str:
        """Crée le répertoire custom s'il n'existe pas."""
        os.makedirs(self.custom_dir, exist_ok=True)
        return self.custom_dir

    def _ensure_cache_dir(self) -> str:
        """Crée le répertoire cache s'il n'existe pas."""
        os.makedirs(self.cache_dir, exist_ok=True)
        return self.cache_dir

    def _get_default_documents(self) -> list[dict]:
        """Liste les documents du corpus par défaut disponibles sur disque (hors templates)."""
        docs = []

        # Documents PDF/MD dans documents/
        docs_dir = os.path.join(self.corpus_dir, "documents")
        if os.path.isdir(docs_dir):
            for fname in sorted(os.listdir(docs_dir)):
                fpath = os.path.join(docs_dir, fname)
                if os.path.isfile(fpath) and fname.lower().endswith((".pdf", ".md", ".txt")):
                    docs.append({
                        "path": fpath,
                        "filename": fname,
                        "type": "document",
                        "collection": self.corpus_collection,
                    })

        return docs

    def _get_cached_documents(self) -> list[dict]:
        """Liste les documents téléchargés depuis le Site Central (cache), hors templates."""
        docs = []
        if not os.path.isdir(self.cache_dir):
            return docs

        for fname in sorted(os.listdir(self.cache_dir)):
            fpath = os.path.join(self.cache_dir, fname)
            if os.path.isfile(fpath) and not fname.startswith("."):
                # Ignorer les templates (TPE/TRE)
                fname_lower = fname.lower()
                if "tpe" in fname_lower or "template_rapport" in fname_lower:
                    continue
                # Identifier les URLs (fichiers .url.txt ou provenant de urls/)
                if fname_lower.endswith(".url.txt") or "urls_" in fname_lower:
                    doc_type = "url"
                else:
                    doc_type = "document"
                docs.append({
                    "path": fpath,
                    "filename": fname,
                    "type": doc_type,
                    "collection": self.corpus_collection,
                })

        return docs

    def _get_custom_documents(self) -> list[dict]:
        """Liste les documents personnalisés de l'expert."""
        docs = []
        if not os.path.isdir(self.custom_dir):
            return docs

        for fname in sorted(os.listdir(self.custom_dir)):
            fpath = os.path.join(self.custom_dir, fname)
            if os.path.isfile(fpath) and not fname.startswith("."):
                # Identifier les URLs
                if fname.lower().endswith(".url.txt"):
                    doc_type = "url"
                else:
                    doc_type = "custom"
                docs.append({
                    "path": fpath,
                    "filename": fname,
                    "type": doc_type,
                    "collection": self.corpus_collection,
                })

        return docs

    async def initialize(self) -> dict:
        """Initialise le corpus RAG avec les documents par défaut.

        1. Télécharge la liste du contenu depuis le Site Central
        2. Télécharge chaque fichier disponible
        3. Indexe tout dans le RAG
        Équivalent à "Reset to original".

        Returns:
            dict avec le nombre de documents indexés et les erreurs éventuelles.
        """
        rag = RAGService()
        indexed = 0
        errors = []
        cache_dir = self._ensure_cache_dir()

        try:
            # Supprimer les collections existantes
            await rag.delete_collection(self.config_collection)
            await rag.delete_collection(self.corpus_collection)

            # 1. Télécharger la liste du contenu depuis le Site Central
            contenu_items = await self._fetch_contenu_from_central()

            if contenu_items:
                # 2. Télécharger et indexer chaque fichier depuis le Site Central
                for item in contenu_items:
                    nom = item.get("nom", "")
                    item_type = item.get("type", "document")

                    # Déterminer la collection cible
                    if item_type == "template":
                        collection = self.config_collection
                    else:
                        collection = self.corpus_collection

                    # Télécharger le fichier
                    try:
                        content = await self._download_file_from_central(nom)
                        if not content:
                            continue

                        # Sauvegarder en cache
                        safe_name = nom.replace("/", "_")
                        cache_path = os.path.join(cache_dir, safe_name)
                        with open(cache_path, "wb") as f:
                            f.write(content)

                        # Lire le texte pour indexation
                        text = self._read_document_text(cache_path)
                        if text.strip():
                            await rag.index_document(
                                file_path=None,
                                collection=collection,
                                metadata={
                                    "type": item_type,
                                    "filename": safe_name,
                                    "domaine": self.domaine,
                                    "description": item.get("description", ""),
                                },
                                text_content=text,
                            )
                            indexed += 1
                            logger.info("Indexé depuis Site Central : %s → %s", nom, collection)
                    except Exception as exc:
                        error_msg = f"{nom}: {exc}"
                        errors.append(error_msg)
                        logger.warning("Erreur téléchargement/indexation %s : %s", nom, exc)
            else:
                # Fallback : indexer les fichiers locaux si le Site Central est indisponible
                logger.info("Site Central indisponible — indexation des fichiers locaux")
                for doc in self._get_default_documents():
                    try:
                        text = self._read_document_text(doc["path"])
                        if text.strip():
                            await rag.index_document(
                                file_path=None,
                                collection=doc["collection"],
                                metadata={
                                    "type": doc["type"],
                                    "filename": doc["filename"],
                                    "domaine": self.domaine,
                                },
                                text_content=text,
                            )
                            indexed += 1
                            logger.info("Indexé local : %s → %s", doc["filename"], doc["collection"])
                    except Exception as exc:
                        errors.append(f"{doc['filename']}: {exc}")
                        logger.warning("Erreur indexation locale %s : %s", doc["filename"], exc)

        finally:
            await rag.close()

        # Nettoyer les documents custom (reset to original)
        if os.path.isdir(self.custom_dir):
            shutil.rmtree(self.custom_dir)

        return {
            "indexed": indexed,
            "errors": errors,
            "total_available": len(contenu_items) if contenu_items else len(self._get_default_documents()),
        }

    async def _fetch_contenu_from_central(self) -> list[dict]:
        """Récupère la liste du contenu corpus depuis le Site Central."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{SITE_CENTRAL_URL}/api/corpus/{self.domaine}/contenu"
                )
                if resp.status_code == 200:
                    return resp.json()
                logger.warning("Site Central contenu HTTP %d", resp.status_code)
                return []
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.warning("Site Central indisponible pour contenu : %s", exc)
            return []

    async def _download_file_from_central(self, filename: str) -> bytes | None:
        """Télécharge un fichier du corpus depuis le Site Central."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(
                    f"{SITE_CENTRAL_URL}/api/corpus/{self.domaine}/fichier/{filename}"
                )
                if resp.status_code == 200:
                    return resp.content
                logger.warning("Fichier %s non trouvé sur Site Central (HTTP %d)", filename, resp.status_code)
                return None
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.warning("Erreur téléchargement %s : %s", filename, exc)
            return None

    async def rebuild(self) -> dict:
        """Reconstruit le RAG avec les documents par défaut + cache + custom.

        Returns:
            dict avec le nombre de documents indexés.
        """
        rag = RAGService()
        indexed = 0
        errors = []

        try:
            # Supprimer les collections existantes
            await rag.delete_collection(self.config_collection)
            await rag.delete_collection(self.corpus_collection)

            # Indexer les documents par défaut (locaux)
            for doc in self._get_default_documents():
                try:
                    text = self._read_document_text(doc["path"])
                    if text.strip():
                        await rag.index_document(
                            file_path=None,
                            collection=doc["collection"],
                            metadata={
                                "type": doc["type"],
                                "filename": doc["filename"],
                                "domaine": self.domaine,
                            },
                            text_content=text,
                        )
                        indexed += 1
                except Exception as exc:
                    errors.append(f"{doc['filename']}: {exc}")
                    logger.warning("Erreur indexation %s : %s", doc["filename"], exc)

            # Indexer les documents du cache (téléchargés depuis le Site Central)
            for doc in self._get_cached_documents():
                try:
                    text = self._read_document_text(doc["path"])
                    if text.strip():
                        await rag.index_document(
                            file_path=None,
                            collection=doc["collection"],
                            metadata={
                                "type": doc["type"],
                                "filename": doc["filename"],
                                "domaine": self.domaine,
                                "source": "central",
                            },
                            text_content=text,
                        )
                        indexed += 1
                except Exception as exc:
                    errors.append(f"{doc['filename']}: {exc}")
                    logger.warning("Erreur indexation cache %s : %s", doc["filename"], exc)

            # Indexer les documents custom
            for doc in self._get_custom_documents():
                try:
                    text = self._read_document_text(doc["path"])
                    if text.strip():
                        await rag.index_document(
                            file_path=None,
                            collection=doc["collection"],
                            metadata={
                                "type": doc["type"],
                                "filename": doc["filename"],
                                "domaine": self.domaine,
                                "custom": True,
                            },
                            text_content=text,
                        )
                        indexed += 1
                except Exception as exc:
                    errors.append(f"{doc['filename']}: {exc}")
                    logger.warning("Erreur indexation custom %s : %s", doc["filename"], exc)

        finally:
            await rag.close()

        return {"indexed": indexed, "errors": errors}

    async def add_document(self, filename: str, content: bytes) -> dict:
        """Ajoute un document personnalisé au corpus.

        Le document est stocké dans le répertoire custom et indexé dans le RAG.
        """
        custom_dir = self._ensure_custom_dir()
        file_path = os.path.join(custom_dir, filename)

        # Sauvegarder sur disque
        with open(file_path, "wb") as f:
            f.write(content)

        # Indexer dans le RAG
        rag = RAGService()
        doc_id = ""
        try:
            text = self._read_document_text(file_path)
            if text.strip():
                doc_id = await rag.index_document(
                    file_path=None,
                    collection=self.corpus_collection,
                    metadata={
                        "type": "custom",
                        "filename": filename,
                        "domaine": self.domaine,
                        "custom": True,
                    },
                    text_content=text,
                )
        finally:
            await rag.close()

        return {"filename": filename, "doc_id": doc_id}

    async def remove_document(self, filename: str) -> bool:
        """Supprime un document personnalisé du corpus.

        Supprime du disque et du RAG.
        """
        file_path = os.path.join(self.custom_dir, filename)

        # Supprimer du disque
        if os.path.isfile(file_path):
            os.remove(file_path)

        # Supprimer du RAG
        rag = RAGService()
        try:
            deleted = await rag.delete_by_metadata(
                self.corpus_collection, "filename", filename
            )
            return deleted > 0
        finally:
            await rag.close()

    def list_all_documents(self) -> list[dict]:
        """Liste tous les documents (défaut + cache + custom) avec leur statut."""
        docs = []

        for doc in self._get_default_documents():
            docs.append({
                "filename": doc["filename"],
                "type": doc["type"],
                "collection": doc["collection"],
                "source": "default",
            })

        for doc in self._get_cached_documents():
            # Éviter les doublons avec les fichiers par défaut
            if not any(d["filename"] == doc["filename"] for d in docs):
                docs.append({
                    "filename": doc["filename"],
                    "type": doc["type"],
                    "collection": doc["collection"],
                    "source": "central",
                })

        for doc in self._get_custom_documents():
            docs.append({
                "filename": doc["filename"],
                "type": doc["type"],
                "collection": doc["collection"],
                "source": "custom",
            })

        return docs

    @staticmethod
    def _read_document_text(file_path: str) -> str:
        """Lit le contenu textuel d'un document (txt, md, tpl, ou fallback binaire)."""
        ext = os.path.splitext(file_path)[1].lower()

        if ext in (".txt", ".md", ".tpl"):
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        if ext == ".pdf":
            # Pour les PDFs, on retourne un placeholder — l'OCR devrait être fait en amont
            # En production, utiliser PyMuPDF pour extraire le texte
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
                return text
            except ImportError:
                logger.warning("PyMuPDF non disponible — PDF non indexé : %s", file_path)
                return ""

        if ext == ".docx":
            try:
                from docx import Document
                doc = Document(file_path)
                return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            except Exception:
                pass

        # Fallback : lire comme texte
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return ""
