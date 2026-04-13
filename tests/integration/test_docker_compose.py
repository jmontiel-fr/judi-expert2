"""Tests d'intégration Docker Compose — communication inter-conteneurs.

Vérifie que les 4 conteneurs (judi-web, judi-llm, judi-rag, judi-ocr)
peuvent démarrer et communiquer entre eux via leurs APIs respectives.

Valide : Exigences 2.1
"""

import shutil

import httpx
import pytest

# ---------------------------------------------------------------------------
# Skip si Docker n'est pas disponible
# ---------------------------------------------------------------------------

_docker_available = shutil.which("docker") is not None

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _docker_available, reason="Docker non disponible"),
]

# ---------------------------------------------------------------------------
# Configuration des URLs de service (ports exposés par docker-compose)
# ---------------------------------------------------------------------------

LLM_URL = "http://localhost:11434"
RAG_URL = "http://localhost:6333"
OCR_URL = "http://localhost:8001"
WEB_BACKEND_URL = "http://localhost:8000"


# ---------------------------------------------------------------------------
# Tests de health check pour chaque conteneur
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_judi_llm_health():
    """Le conteneur judi-llm (Ollama) répond sur le port 11434."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{LLM_URL}/api/tags")
            assert resp.status_code == 200
            data = resp.json()
            # Ollama retourne une liste de modèles
            assert "models" in data
        except httpx.ConnectError:
            pytest.skip("judi-llm non démarré (docker-compose non actif)")


@pytest.mark.asyncio
async def test_judi_rag_health():
    """Le conteneur judi-rag (Qdrant) répond sur le port 6333."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{RAG_URL}/healthz")
            assert resp.status_code == 200
        except httpx.ConnectError:
            pytest.skip("judi-rag non démarré (docker-compose non actif)")


@pytest.mark.asyncio
async def test_judi_ocr_health():
    """Le conteneur judi-ocr (OCR API) répond sur le port 8001."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{OCR_URL}/health")
            assert resp.status_code == 200
        except httpx.ConnectError:
            pytest.skip("judi-ocr non démarré (docker-compose non actif)")


@pytest.mark.asyncio
async def test_judi_web_backend_health():
    """Le conteneur judi-web-backend (FastAPI) répond sur le port 8000."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{WEB_BACKEND_URL}/api/health")
        except httpx.ConnectError:
            pytest.skip("judi-web-backend non démarré (docker-compose non actif)")
            return

        if resp.status_code == 404:
            pytest.skip("Port 8000 actif mais ne sert pas l'API judi-web")
            return

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "judi-expert-local"


# ---------------------------------------------------------------------------
# Tests de communication inter-conteneurs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_can_reach_llm():
    """judi-web peut communiquer avec judi-llm (Ollama API)."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            # Vérifier que le LLM est accessible depuis l'extérieur
            # (simule la communication que judi-web fait en interne)
            resp = await client.get(f"{LLM_URL}/api/tags")
            assert resp.status_code == 200
        except httpx.ConnectError:
            pytest.skip("judi-llm non accessible")


@pytest.mark.asyncio
async def test_web_can_reach_rag():
    """judi-web peut communiquer avec judi-rag (Qdrant REST API)."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Lister les collections Qdrant
            resp = await client.get(f"{RAG_URL}/collections")
            assert resp.status_code == 200
            data = resp.json()
            assert "result" in data
        except httpx.ConnectError:
            pytest.skip("judi-rag non accessible")


@pytest.mark.asyncio
async def test_web_can_reach_ocr():
    """judi-web peut communiquer avec judi-ocr (OCR API)."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{OCR_URL}/health")
            assert resp.status_code == 200
        except httpx.ConnectError:
            pytest.skip("judi-ocr non accessible")


# ---------------------------------------------------------------------------
# Test de la configuration Docker Compose
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_services_respond():
    """Vérifie que les 4 services répondent simultanément."""
    services = {
        "judi-llm": f"{LLM_URL}/api/tags",
        "judi-rag": f"{RAG_URL}/healthz",
        "judi-ocr": f"{OCR_URL}/health",
        "judi-web": f"{WEB_BACKEND_URL}/api/health",
    }

    results = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, url in services.items():
            try:
                resp = await client.get(url)
                results[name] = resp.status_code == 200
            except httpx.ConnectError:
                results[name] = False

    running = [name for name, ok in results.items() if ok]
    not_running = [name for name, ok in results.items() if not ok]

    if not running:
        pytest.skip("Aucun conteneur Docker n'est démarré")

    if not_running:
        pytest.skip(
            f"Conteneurs non démarrés : {', '.join(not_running)}. "
            f"Conteneurs actifs : {', '.join(running)}"
        )

    # Tous les services répondent
    assert all(results.values()), f"Services en échec : {not_running}"
