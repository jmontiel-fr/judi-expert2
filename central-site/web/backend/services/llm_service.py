"""
Judi-Expert — Service LLM Site Central (Mistral API publique)

Client asynchrone pour l'API Mistral (La Plateforme).
Utilisé par le chatbot du site central pour répondre aux questions
des utilisateurs en s'appuyant sur le contexte RAG.
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MISTRAL_API_KEY: str = os.environ.get("MISTRAL_API_KEY", "")
MISTRAL_API_URL: str = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_MODEL: str = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
LLM_TIMEOUT: float = float(os.environ.get("LLM_TIMEOUT", "60"))

# ---------------------------------------------------------------------------
# Prompt système
# ---------------------------------------------------------------------------

PROMPT_CHATBOT: str = (
    "Tu es l'assistant virtuel du site Judi-Expert (www.judi-expert.fr), "
    "une plateforme d'assistance aux experts judiciaires français.\n\n"
    "Tu disposes du **contexte** suivant, issu de la documentation du site "
    "(FAQ, CGU, mentions légales, méthodologie, politique de confidentialité) :\n\n"
    "{contexte_rag}\n\n"
    "Consignes :\n"
    "1. Réponds de manière claire, concise et professionnelle en français.\n"
    "2. Base tes réponses uniquement sur le contexte fourni.\n"
    "3. Si tu ne disposes pas d'information suffisante, indique-le clairement "
    "et suggère de consulter la page appropriée du site ou de contacter le support.\n"
    "4. Ne fournis jamais de conseil juridique.\n"
    "5. Sois courtois et utile.\n"
    "6. Si on te demande des informations sur les tarifs, renvoie vers la page Tarifs.\n"
    "7. Pour les questions techniques sur l'application locale, renvoie vers la FAQ."
)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LLMError(Exception):
    """Erreur de base pour le service LLM."""


class LLMConnectionError(LLMError):
    """Impossible de se connecter à l'API Mistral."""


class LLMConfigError(LLMError):
    """Clé API manquante ou invalide."""


# ---------------------------------------------------------------------------
# Service LLM
# ---------------------------------------------------------------------------


class LLMService:
    """Client asynchrone pour l'API Mistral publique."""

    def __init__(
        self,
        api_key: str = MISTRAL_API_KEY,
        model: str = MISTRAL_MODEL,
        timeout: float = LLM_TIMEOUT,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def chatbot(
        self,
        messages: list[dict[str, str]],
        contexte_rag: str = "",
    ) -> str:
        """Envoie une conversation au LLM et retourne la réponse.

        Args:
            messages: Historique de conversation [{role, content}, ...].
            contexte_rag: Contexte RAG à injecter dans le prompt système.

        Returns:
            Réponse textuelle de l'assistant.
        """
        if not self.api_key:
            raise LLMConfigError(
                "MISTRAL_API_KEY non configurée. "
                "Ajoutez-la dans les variables d'environnement."
            )

        system_prompt = PROMPT_CHATBOT.format(
            contexte_rag=contexte_rag if contexte_rag else "(Aucun contexte disponible)"
        )

        api_messages = [{"role": "system", "content": system_prompt}]
        api_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": api_messages,
            "temperature": 0.3,
            "max_tokens": 1024,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    MISTRAL_API_URL,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except httpx.TimeoutException:
            logger.error("Mistral API timeout")
            raise LLMConnectionError("L'assistant n'a pas répondu dans le délai imparti.")
        except httpx.HTTPStatusError as exc:
            logger.error("Erreur HTTP Mistral API : %s — %s", exc.response.status_code, exc.response.text)
            if exc.response.status_code == 401:
                raise LLMConfigError("Clé API Mistral invalide.")
            raise LLMConnectionError(
                f"Erreur de l'API Mistral (HTTP {exc.response.status_code})."
            )
        except httpx.ConnectError:
            logger.error("Impossible de se connecter à l'API Mistral")
            raise LLMConnectionError("Impossible de se connecter à l'API Mistral.")
