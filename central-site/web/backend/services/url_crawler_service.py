"""Service de pré-crawl des URLs du corpus.

Télécharge le contenu textuel des URLs de référence et le stocke
dans un cache local pour distribution aux applications locales.

Le cache est stocké dans /data/corpus/{domaine}/urls_cache/
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Optional

import httpx
import yaml

logger = logging.getLogger(__name__)

CORPUS_BASE_PATH = Path(os.environ.get("CORPUS_BASE_PATH", "/data/corpus"))
CRAWL_TIMEOUT = 30.0  # secondes par URL


class UrlCrawlerService:
    """Service de crawl des URLs du corpus."""

    def __init__(self, domaine: str):
        self.domaine = domaine
        self.urls_file = CORPUS_BASE_PATH / domaine / "urls" / "urls.yaml"
        self.cache_dir = CORPUS_BASE_PATH / domaine / "urls_cache"

    def _ensure_cache_dir(self) -> Path:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        return self.cache_dir

    def _url_to_cache_filename(self, url: str) -> str:
        """Génère un nom de fichier cache stable à partir d'une URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        # Extraire le domaine pour lisibilité
        domain = re.sub(r'https?://(www\.)?', '', url).split('/')[0]
        safe_domain = re.sub(r'[^a-zA-Z0-9.-]', '_', domain)[:30]
        return f"{safe_domain}_{url_hash}.txt"

    def load_urls(self) -> list[dict]:
        """Charge la liste des URLs depuis urls.yaml."""
        if not self.urls_file.is_file():
            return []
        with open(self.urls_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("urls", []) if data else []

    def get_cached_content(self, url: str) -> Optional[str]:
        """Retourne le contenu pré-crawlé d'une URL, ou None si non crawlé."""
        cache_file = self.cache_dir / self._url_to_cache_filename(url)
        if cache_file.is_file():
            return cache_file.read_text(encoding="utf-8")
        return None

    def get_cached_content_by_index(self, index: int) -> Optional[str]:
        """Retourne le contenu pré-crawlé par index dans la liste des URLs."""
        urls = self.load_urls()
        if index < 0 or index >= len(urls):
            return None
        url = urls[index].get("url", "")
        return self.get_cached_content(url)

    async def crawl_all(self) -> dict:
        """Crawle toutes les URLs et stocke le contenu textuel.

        Returns:
            dict avec crawled (nombre réussi), errors (liste d'erreurs), total
        """
        urls = self.load_urls()
        if not urls:
            return {"crawled": 0, "errors": [], "total": 0}

        self._ensure_cache_dir()
        crawled = 0
        errors = []

        async with httpx.AsyncClient(
            timeout=CRAWL_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "JudiExpert-Crawler/1.0 (corpus indexation)"},
        ) as client:
            for item in urls:
                url = item.get("url", "")
                nom = item.get("nom", url)
                if not url:
                    continue

                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        errors.append(f"{nom}: HTTP {resp.status_code}")
                        logger.warning("Crawl %s → HTTP %d", url, resp.status_code)
                        continue

                    # Extraire le texte du HTML
                    content_type = resp.headers.get("content-type", "")
                    if "html" in content_type:
                        text = self._extract_text_from_html(resp.text)
                    else:
                        text = resp.text

                    if not text.strip():
                        errors.append(f"{nom}: contenu vide")
                        continue

                    # Sauvegarder dans le cache
                    cache_file = self.cache_dir / self._url_to_cache_filename(url)
                    cache_file.write_text(text, encoding="utf-8")
                    crawled += 1
                    logger.info("Crawlé : %s (%d chars)", nom, len(text))

                except httpx.TimeoutException:
                    errors.append(f"{nom}: timeout")
                    logger.warning("Timeout crawl %s", url)
                except httpx.ConnectError as exc:
                    errors.append(f"{nom}: connexion impossible")
                    logger.warning("Erreur connexion %s: %s", url, exc)
                except Exception as exc:
                    errors.append(f"{nom}: {type(exc).__name__}")
                    logger.warning("Erreur crawl %s: %s", url, exc)

        return {"crawled": crawled, "errors": errors, "total": len(urls)}

    @staticmethod
    def _extract_text_from_html(html: str) -> str:
        """Extrait le texte principal d'une page HTML (supprime tags, scripts, styles)."""
        # Supprimer scripts et styles
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Supprimer les tags HTML
        text = re.sub(r'<[^>]+>', ' ', text)
        # Décoder les entités HTML courantes
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        # Nettoyer les espaces multiples
        text = re.sub(r'\s+', ' ', text).strip()
        # Limiter à 50000 caractères (éviter les pages trop longues)
        return text[:50000]
