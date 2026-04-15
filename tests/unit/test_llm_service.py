"""Tests unitaires pour le service LLM (client Ollama).

Teste les appels à l'API Ollama (/api/chat, /api/generate), les méthodes
de haut niveau du workflow d'expertise, et la gestion des erreurs réseau.

Valide : Exigences 6.4, 7.2, 9.2, 9.3, 11.2
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

# Ajouter le backend au path
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend")
)

from services.llm_service import (
    LLM_MODEL,
    LLMConnectionError,
    LLMService,
    LLMTimeoutError,
    PROMPT_CHATBOT,
    PROMPT_GENERATION_QMEC,
    PROMPT_GENERATION_RAUX_P1,
    PROMPT_GENERATION_RAUX_P2,
    PROMPT_GENERATION_REF,
    PROMPT_STRUCTURATION_MD,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def llm_service():
    """Instance de LLMService avec URL de test."""
    return LLMService(base_url="http://test-llm:11434", model="test-model", timeout=10)


def _mock_chat_response(content: str) -> httpx.Response:
    """Crée une réponse HTTP simulée pour /api/chat."""
    return httpx.Response(
        200,
        json={"message": {"role": "assistant", "content": content}},
        request=httpx.Request("POST", "http://test-llm:11434/api/chat"),
    )


def _mock_generate_response(content: str) -> httpx.Response:
    """Crée une réponse HTTP simulée pour /api/generate."""
    return httpx.Response(
        200,
        json={"response": content},
        request=httpx.Request("POST", "http://test-llm:11434/api/generate"),
    )


# ---------------------------------------------------------------------------
# Tests des prompts
# ---------------------------------------------------------------------------

class TestPrompts:
    """Vérifie que les prompts système sont définis et non vides."""

    def test_prompt_structuration_md_defined(self):
        assert len(PROMPT_STRUCTURATION_MD) > 100

    def test_prompt_generation_qmec_defined(self):
        assert len(PROMPT_GENERATION_QMEC) > 100

    def test_prompt_generation_ref_defined(self):
        assert len(PROMPT_GENERATION_REF) > 100

    def test_prompt_generation_raux_p1_defined(self):
        assert len(PROMPT_GENERATION_RAUX_P1) > 100

    def test_prompt_generation_raux_p2_defined(self):
        assert len(PROMPT_GENERATION_RAUX_P2) > 100

    def test_prompt_chatbot_defined(self):
        assert len(PROMPT_CHATBOT) > 100

    def test_prompt_chatbot_has_rag_placeholder(self):
        """Le prompt chatbot contient le placeholder pour le contexte RAG."""
        assert "{contexte_rag}" in PROMPT_CHATBOT


# ---------------------------------------------------------------------------
# Tests de configuration
# ---------------------------------------------------------------------------

class TestConfiguration:
    """Vérifie la configuration par défaut et personnalisée."""

    def test_default_configuration(self):
        service = LLMService()
        assert service.base_url == "http://judi-llm:11434"
        assert service.model == "mistral:7b-instruct-v0.3"

    def test_custom_configuration(self, llm_service):
        assert llm_service.base_url == "http://test-llm:11434"
        assert llm_service.model == "test-model"
        assert llm_service.timeout == 10

    def test_trailing_slash_stripped(self):
        service = LLMService(base_url="http://localhost:11434/")
        assert service.base_url == "http://localhost:11434"


# ---------------------------------------------------------------------------
# Tests de la méthode chat()
# ---------------------------------------------------------------------------

class TestChat:
    """Tests pour la méthode chat (POST /api/chat)."""

    @pytest.mark.asyncio
    async def test_chat_returns_content(self, llm_service):
        mock_response = _mock_chat_response("Réponse du LLM")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            result = await llm_service.chat(
                [{"role": "user", "content": "Bonjour"}]
            )
        assert result == "Réponse du LLM"

    @pytest.mark.asyncio
    async def test_chat_with_system_prompt(self, llm_service):
        mock_response = _mock_chat_response("Réponse structurée")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            await llm_service.chat(
                [{"role": "user", "content": "texte"}],
                system_prompt="Tu es un assistant.",
            )
            call_args = mock_post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            # Le system prompt doit être le premier message
            assert payload["messages"][0]["role"] == "system"
            assert payload["messages"][0]["content"] == "Tu es un assistant."

    @pytest.mark.asyncio
    async def test_chat_sends_stream_false(self, llm_service):
        mock_response = _mock_chat_response("ok")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            await llm_service.chat([{"role": "user", "content": "test"}])
            payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
            assert payload["stream"] is False

    @pytest.mark.asyncio
    async def test_chat_timeout_raises_llm_timeout_error(self, llm_service):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(LLMTimeoutError):
                await llm_service.chat([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_chat_connect_error_raises_llm_connection_error(self, llm_service):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=httpx.ConnectError("refused")):
            with pytest.raises(LLMConnectionError):
                await llm_service.chat([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_chat_http_error_raises_llm_connection_error(self, llm_service):
        error_response = httpx.Response(
            500,
            json={"error": "internal"},
            request=httpx.Request("POST", "http://test-llm:11434/api/chat"),
        )
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=error_response):
            with pytest.raises(LLMConnectionError):
                await llm_service.chat([{"role": "user", "content": "test"}])


# ---------------------------------------------------------------------------
# Tests de la méthode generate()
# ---------------------------------------------------------------------------

class TestGenerate:
    """Tests pour la méthode generate (POST /api/generate)."""

    @pytest.mark.asyncio
    async def test_generate_returns_response(self, llm_service):
        mock_response = _mock_generate_response("Texte généré")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            result = await llm_service.generate("Mon prompt")
        assert result == "Texte généré"

    @pytest.mark.asyncio
    async def test_generate_sends_correct_payload(self, llm_service):
        mock_response = _mock_generate_response("ok")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            await llm_service.generate("Mon prompt")
            payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
            assert payload["prompt"] == "Mon prompt"
            assert payload["model"] == "test-model"
            assert payload["stream"] is False

    @pytest.mark.asyncio
    async def test_generate_timeout_raises_llm_timeout_error(self, llm_service):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(LLMTimeoutError):
                await llm_service.generate("test")

    @pytest.mark.asyncio
    async def test_generate_connect_error_raises_llm_connection_error(self, llm_service):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=httpx.ConnectError("refused")):
            with pytest.raises(LLMConnectionError):
                await llm_service.generate("test")


# ---------------------------------------------------------------------------
# Tests des méthodes de haut niveau
# ---------------------------------------------------------------------------

class TestStructurerMarkdown:
    """Tests pour structurer_markdown (Step0)."""

    @pytest.mark.asyncio
    async def test_structurer_markdown_calls_chat_with_correct_prompt(self, llm_service):
        mock_response = _mock_chat_response("# Document structuré")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            result = await llm_service.structurer_markdown("Texte brut OCR")
            assert result == "# Document structuré"
            payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
            # System prompt = PROMPT_STRUCTURATION_MD
            assert payload["messages"][0]["role"] == "system"
            assert "Questions du Tribunal" in payload["messages"][0]["content"]
            # User message = texte brut
            assert payload["messages"][1]["content"] == "Texte brut OCR"


class TestGenererQmec:
    """Tests pour generer_qmec (Step1)."""

    @pytest.mark.asyncio
    async def test_generer_qmec_includes_all_inputs(self, llm_service):
        mock_response = _mock_chat_response("# Plan d'entretien")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            result = await llm_service.generer_qmec(
                qt="Question 1?", tpe="Section 1", contexte_rag="Contexte domaine"
            )
            assert result == "# Plan d'entretien"
            payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
            user_content = payload["messages"][1]["content"]
            assert "Question 1?" in user_content
            assert "Section 1" in user_content
            assert "Contexte domaine" in user_content


class TestGenererRef:
    """Tests pour generer_ref (Step3)."""

    @pytest.mark.asyncio
    async def test_generer_ref_includes_all_inputs(self, llm_service):
        mock_response = _mock_chat_response("# Rapport Final")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            result = await llm_service.generer_ref(
                reb="Rapport brut", qt="Questions", ne="Notes", template="Template"
            )
            assert result == "# Rapport Final"
            payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
            user_content = payload["messages"][1]["content"]
            assert "Rapport brut" in user_content
            assert "Questions" in user_content
            assert "Notes" in user_content
            assert "Template" in user_content


class TestGenererRauxP1:
    """Tests pour generer_raux_p1 (Step3 — contestations)."""

    @pytest.mark.asyncio
    async def test_generer_raux_p1_includes_ref_and_corpus(self, llm_service):
        mock_response = _mock_chat_response("# Contestations")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            result = await llm_service.generer_raux_p1(
                ref="Rapport final", corpus="Corpus domaine"
            )
            assert result == "# Contestations"
            payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
            user_content = payload["messages"][1]["content"]
            assert "Rapport final" in user_content
            assert "Corpus domaine" in user_content


class TestGenererRauxP2:
    """Tests pour generer_raux_p2 (Step3 — révision)."""

    @pytest.mark.asyncio
    async def test_generer_raux_p2_includes_ref_and_p1(self, llm_service):
        mock_response = _mock_chat_response("# REF Révisé")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            result = await llm_service.generer_raux_p2(
                ref="Rapport final", raux_p1="Contestations"
            )
            assert result == "# REF Révisé"
            payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
            user_content = payload["messages"][1]["content"]
            assert "Rapport final" in user_content
            assert "Contestations" in user_content


class TestChatbot:
    """Tests pour chatbot (ChatBot avec contexte RAG)."""

    @pytest.mark.asyncio
    async def test_chatbot_injects_rag_context(self, llm_service):
        mock_response = _mock_chat_response("Voici la réponse")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            result = await llm_service.chatbot(
                messages=[{"role": "user", "content": "Comment utiliser Step0 ?"}],
                contexte_rag="Guide utilisateur : Step0 permet l'extraction OCR.",
            )
            assert result == "Voici la réponse"
            payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
            system_content = payload["messages"][0]["content"]
            # Le contexte RAG doit être injecté dans le prompt système
            assert "Guide utilisateur : Step0 permet l'extraction OCR." in system_content
            # Le placeholder ne doit plus être présent
            assert "{contexte_rag}" not in system_content
