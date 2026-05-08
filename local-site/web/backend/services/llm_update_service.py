"""
Judi-Expert — Service de suivi de l'état de mise à jour du modèle LLM.

Lit le fichier d'état JSON écrit par ollama-entrypoint.sh dans le volume Ollama
et interroge l'API Ollama pour obtenir le digest du modèle courant.

Valide : Exigences 7.1, 7.2, 7.3, 7.4
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class LlmUpdateService:
    """Service de suivi de l'état de mise à jour du modèle LLM.

    Lit le fichier ``/root/.ollama/update-status.json`` (écrit par
    ``ollama-entrypoint.sh``) et interroge l'API Ollama pour le digest
    du modèle courant.
    """

    STATUS_FILE_PATH: Path = Path(
        os.environ.get(
            "LLM_STATUS_FILE",
            "/root/.ollama/update-status.json",
        )
    )
    OLLAMA_API_URL: str = os.environ.get("OLLAMA_URL", "http://judi-llm:11434")
    OLLAMA_TIMEOUT: float = float(os.environ.get("OLLAMA_TIMEOUT", "10"))

    async def get_update_status(self) -> dict:
        """Retourne l'état de la mise à jour du modèle LLM.

        Lit le fichier d'état JSON depuis le volume Ollama. Si le fichier
        n'existe pas, retourne un statut « idle ». Si le JSON est invalide,
        retourne un statut « error ».

        Returns:
            dict avec les clés : status, progress, current_model, error_message.
        """
        if not self.STATUS_FILE_PATH.exists():
            logger.debug(
                "Fichier d'état LLM absent (%s) — statut idle.",
                self.STATUS_FILE_PATH,
            )
            return {
                "status": "idle",
                "progress": 0,
                "current_model": None,
                "error_message": None,
            }

        try:
            raw = self.STATUS_FILE_PATH.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "Fichier d'état LLM invalide (%s) : %s",
                self.STATUS_FILE_PATH,
                exc,
            )
            return {
                "status": "error",
                "progress": 0,
                "current_model": None,
                "error_message": "Fichier d'état LLM invalide.",
            }
        except OSError as exc:
            logger.error(
                "Impossible de lire le fichier d'état LLM (%s) : %s",
                self.STATUS_FILE_PATH,
                exc,
            )
            return {
                "status": "error",
                "progress": 0,
                "current_model": None,
                "error_message": f"Erreur de lecture du fichier d'état : {exc}",
            }

        status = data.get("status", "idle")
        progress = data.get("progress", 0)
        model = data.get("model")
        error = data.get("error")

        # Clamp progress to 0-100
        progress = max(0, min(100, int(progress)))

        return {
            "status": status,
            "progress": progress,
            "current_model": model,
            "error_message": error,
        }

    async def get_current_model_digest(self) -> Optional[str]:
        """Lit le digest du modèle courant via l'API Ollama.

        Interroge ``GET /api/tags`` sur le serveur Ollama pour récupérer
        le digest SHA256 du modèle actuellement chargé.

        Returns:
            Le digest du modèle (ex: ``sha256:abc123...``) ou None si
            le modèle n'est pas trouvé ou si Ollama est injoignable.
        """
        model_name = os.environ.get(
            "LLM_MODEL", "mistral:7b-instruct-v0.3-q4_0"
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.OLLAMA_TIMEOUT
            ) as client:
                response = await client.get(
                    f"{self.OLLAMA_API_URL}/api/tags"
                )
                response.raise_for_status()
                data = response.json()
        except httpx.ConnectError:
            logger.warning(
                "Impossible de se connecter à Ollama (%s) pour lire le digest.",
                self.OLLAMA_API_URL,
            )
            return None
        except httpx.TimeoutException:
            logger.warning(
                "Timeout lors de la connexion à Ollama (%s).",
                self.OLLAMA_API_URL,
            )
            return None
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Erreur HTTP Ollama /api/tags : %s",
                exc.response.status_code,
            )
            return None

        # Chercher le modèle dans la liste retournée par /api/tags
        models = data.get("models", [])
        for model in models:
            name = model.get("name", "")
            if name == model_name or name.startswith(f"{model_name}:"):
                return model.get("digest")

        # Essayer une correspondance partielle (sans le tag)
        base_name = model_name.split(":")[0] if ":" in model_name else model_name
        for model in models:
            name = model.get("name", "")
            if name.startswith(base_name):
                return model.get("digest")

        logger.info(
            "Modèle '%s' non trouvé dans la liste Ollama.", model_name
        )
        return None
