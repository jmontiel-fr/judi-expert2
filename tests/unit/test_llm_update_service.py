"""Tests unitaires pour le service de suivi de mise à jour du modèle LLM.

Teste la lecture du fichier d'état JSON, la gestion des erreurs (fichier
absent, JSON invalide), et l'appel à l'API Ollama pour le digest du modèle.

Valide : Exigences 7.1, 7.2, 7.3, 7.4
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

# Ajouter le backend au path
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend")
)

from services.llm_update_service import LlmUpdateService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def llm_update_service(tmp_path):
    """Instance de LlmUpdateService avec un fichier d'état temporaire."""
    service = LlmUpdateService()
    service.STATUS_FILE_PATH = tmp_path / "update-status.json"
    service.OLLAMA_API_URL = "http://test-ollama:11434"
    return service


@pytest.fixture
def status_file(llm_update_service):
    """Helper pour écrire un fichier d'état JSON."""

    def _write(data: dict):
        llm_update_service.STATUS_FILE_PATH.write_text(
            json.dumps(data), encoding="utf-8"
        )

    return _write


# ---------------------------------------------------------------------------
# Tests de get_update_status
# ---------------------------------------------------------------------------


class TestGetUpdateStatus:
    """Tests pour la méthode get_update_status."""

    @pytest.mark.asyncio
    async def test_file_absent_returns_idle(self, llm_update_service):
        """Si le fichier d'état n'existe pas, retourne status=idle."""
        result = await llm_update_service.get_update_status()

        assert result["status"] == "idle"
        assert result["progress"] == 0
        assert result["current_model"] is None
        assert result["error_message"] is None

    @pytest.mark.asyncio
    async def test_file_downloading_status(self, llm_update_service, status_file):
        """Lit correctement un statut 'downloading' avec progression."""
        status_file({
            "status": "downloading",
            "progress": 45,
            "model": "mistral:7b-instruct-v0.3-q4_0",
            "started_at": "2026-04-17T10:30:00Z",
            "error": None,
        })

        result = await llm_update_service.get_update_status()

        assert result["status"] == "downloading"
        assert result["progress"] == 45
        assert result["current_model"] == "mistral:7b-instruct-v0.3-q4_0"
        assert result["error_message"] is None

    @pytest.mark.asyncio
    async def test_file_ready_status(self, llm_update_service, status_file):
        """Lit correctement un statut 'ready'."""
        status_file({
            "status": "ready",
            "progress": 100,
            "model": "mistral:7b-instruct-v0.3-q4_0",
            "error": None,
        })

        result = await llm_update_service.get_update_status()

        assert result["status"] == "ready"
        assert result["progress"] == 100
        assert result["current_model"] == "mistral:7b-instruct-v0.3-q4_0"
        assert result["error_message"] is None

    @pytest.mark.asyncio
    async def test_file_error_status(self, llm_update_service, status_file):
        """Lit correctement un statut 'error' avec message."""
        status_file({
            "status": "error",
            "progress": 30,
            "model": "mistral:7b-instruct-v0.3-q4_0",
            "error": "Espace disque insuffisant",
        })

        result = await llm_update_service.get_update_status()

        assert result["status"] == "error"
        assert result["progress"] == 30
        assert result["current_model"] == "mistral:7b-instruct-v0.3-q4_0"
        assert result["error_message"] == "Espace disque insuffisant"

    @pytest.mark.asyncio
    async def test_file_invalid_json_returns_error(self, llm_update_service):
        """Si le fichier contient du JSON invalide, retourne status=error."""
        llm_update_service.STATUS_FILE_PATH.write_text(
            "not valid json {{{", encoding="utf-8"
        )

        result = await llm_update_service.get_update_status()

        assert result["status"] == "error"
        assert result["progress"] == 0
        assert result["error_message"] == "Fichier d'état LLM invalide."

    @pytest.mark.asyncio
    async def test_progress_clamped_to_0_100(self, llm_update_service, status_file):
        """La progression est limitée entre 0 et 100."""
        status_file({
            "status": "downloading",
            "progress": 150,
            "model": "test-model",
            "error": None,
        })

        result = await llm_update_service.get_update_status()
        assert result["progress"] == 100

    @pytest.mark.asyncio
    async def test_progress_negative_clamped_to_0(
        self, llm_update_service, status_file
    ):
        """Une progression négative est ramenée à 0."""
        status_file({
            "status": "downloading",
            "progress": -10,
            "model": "test-model",
            "error": None,
        })

        result = await llm_update_service.get_update_status()
        assert result["progress"] == 0

    @pytest.mark.asyncio
    async def test_idle_status(self, llm_update_service, status_file):
        """Lit correctement un statut 'idle'."""
        status_file({
            "status": "idle",
            "progress": 0,
            "model": "mistral:7b-instruct-v0.3-q4_0",
            "error": None,
        })

        result = await llm_update_service.get_update_status()

        assert result["status"] == "idle"
        assert result["progress"] == 0


# ---------------------------------------------------------------------------
# Tests de get_current_model_digest
# ---------------------------------------------------------------------------


class TestGetCurrentModelDigest:
    """Tests pour la méthode get_current_model_digest."""

    @pytest.mark.asyncio
    async def test_returns_digest_when_model_found(self, llm_update_service):
        """Retourne le digest quand le modèle est trouvé dans /api/tags."""
        mock_response = httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "mistral:7b-instruct-v0.3-q4_0",
                        "digest": "sha256:abc123def456",
                    }
                ]
            },
            request=httpx.Request("GET", "http://test-ollama:11434/api/tags"),
        )

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await llm_update_service.get_current_model_digest()

        assert result == "sha256:abc123def456"

    @pytest.mark.asyncio
    async def test_returns_none_when_model_not_found(self, llm_update_service):
        """Retourne None quand le modèle n'est pas dans la liste."""
        mock_response = httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "llama2:7b",
                        "digest": "sha256:other",
                    }
                ]
            },
            request=httpx.Request("GET", "http://test-ollama:11434/api/tags"),
        )

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await llm_update_service.get_current_model_digest()

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_connection_error(self, llm_update_service):
        """Retourne None si Ollama est injoignable."""
        with patch(
            "httpx.AsyncClient.get",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            result = await llm_update_service.get_current_model_digest()

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self, llm_update_service):
        """Retourne None en cas de timeout."""
        with patch(
            "httpx.AsyncClient.get",
            side_effect=httpx.TimeoutException("Timeout"),
        ):
            result = await llm_update_service.get_current_model_digest()

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self, llm_update_service):
        """Retourne None en cas d'erreur HTTP."""
        mock_response = httpx.Response(
            500,
            request=httpx.Request("GET", "http://test-ollama:11434/api/tags"),
        )

        with patch(
            "httpx.AsyncClient.get",
            side_effect=httpx.HTTPStatusError(
                "Server Error", request=mock_response.request, response=mock_response
            ),
        ):
            result = await llm_update_service.get_current_model_digest()

        assert result is None

    @pytest.mark.asyncio
    async def test_partial_name_match(self, llm_update_service):
        """Trouve le modèle par correspondance partielle du nom de base."""
        mock_response = httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "mistral:latest",
                        "digest": "sha256:partial_match",
                    }
                ]
            },
            request=httpx.Request("GET", "http://test-ollama:11434/api/tags"),
        )

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await llm_update_service.get_current_model_digest()

        assert result == "sha256:partial_match"

    @pytest.mark.asyncio
    async def test_empty_models_list(self, llm_update_service):
        """Retourne None quand la liste de modèles est vide."""
        mock_response = httpx.Response(
            200,
            json={"models": []},
            request=httpx.Request("GET", "http://test-ollama:11434/api/tags"),
        )

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await llm_update_service.get_current_model_digest()

        assert result is None
