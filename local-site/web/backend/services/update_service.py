"""Service de mise à jour forcée de l'Application Locale.

Orchestre le processus complet de mise à jour :
1. Téléchargement des images Docker depuis l'URL fournie par le Site Central
2. Arrêt des conteneurs existants (docker compose down)
3. Chargement des nouvelles images (docker load)
4. Redémarrage des conteneurs (docker compose up -d)
5. Mise à jour de LocalConfig.app_version en base

En cas d'échec à n'importe quelle étape, un rollback restaure les conteneurs
précédents. Les volumes Docker sont toujours préservés.

Valide : Exigences 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.local_config import LocalConfig

logger = logging.getLogger(__name__)

# Chemin vers le fichier docker-compose.yml de l'Application Locale
# En conteneur, le fichier est sur l'hôte — on utilise une variable d'env.
# Le fallback "/app/docker-compose.yml" est un placeholder ; la vraie valeur
# doit être fournie via COMPOSE_FILE si une mise à jour est déclenchée.
COMPOSE_FILE: str = os.environ.get(
    "COMPOSE_FILE",
    "/app/docker-compose.yml",
)

# Timeout pour le téléchargement des images (10 minutes)
DOWNLOAD_TIMEOUT: float = float(os.environ.get("UPDATE_DOWNLOAD_TIMEOUT", "600"))

# Timeout pour les commandes Docker (5 minutes)
DOCKER_COMMAND_TIMEOUT: float = float(
    os.environ.get("UPDATE_DOCKER_TIMEOUT", "300")
)


class UpdateError(Exception):
    """Erreur survenue pendant le processus de mise à jour."""

    def __init__(self, message: str, step: str):
        self.message = message
        self.step = step
        super().__init__(message)


class UpdateService:
    """Service orchestrant la mise à jour forcée de l'Application Locale.

    Attributes:
        db_session: Session SQLAlchemy async pour la mise à jour de LocalConfig.
        download_url: URL de téléchargement de l'archive d'images Docker.
        new_version: Numéro de version cible (semver).
    """

    def __init__(
        self,
        db_session: AsyncSession,
        download_url: str,
        new_version: str,
    ) -> None:
        self.db_session = db_session
        self.download_url = download_url
        self.new_version = new_version

        # État interne de progression
        self._status: str = "idle"
        self._progress: int = 0
        self._step: str = ""
        self._error_message: Optional[str] = None

        # Chemin temporaire pour l'archive téléchargée
        self._archive_path: Optional[str] = None

    # ──────────────────────────────────────────────────────────────
    # API publique
    # ──────────────────────────────────────────────────────────────

    async def execute_update(self) -> None:
        """Exécute le processus complet de mise à jour forcée.

        Étapes :
            1. Télécharger les images Docker (0-50%)
            2. Arrêter les conteneurs (50-60%)
            3. Charger les nouvelles images (60-80%)
            4. Redémarrer les conteneurs (80-95%)
            5. Mettre à jour LocalConfig.app_version (95-100%)

        Raises:
            UpdateError: Si une étape échoue après tentative de rollback.
        """
        try:
            await self._download_images()
            await self._stop_containers()
            await self._load_images()
            await self._start_containers()
            await self._update_config()
            self._set_status("completed", 100, "Mise à jour terminée")
        except UpdateError:
            # Le rollback est déjà tenté dans chaque étape qui le nécessite
            raise
        except Exception as exc:
            error_msg = f"Erreur inattendue : {exc}"
            logger.exception("Erreur inattendue pendant la mise à jour")
            self._set_status("error", self._progress, self._step, error_msg)
            await self.rollback()
            raise UpdateError(error_msg, self._step) from exc
        finally:
            self._cleanup_temp_files()

    async def rollback(self) -> None:
        """Restaure les conteneurs précédents en cas d'échec.

        Tente de redémarrer les conteneurs avec les images existantes.
        Les volumes Docker sont toujours préservés (jamais supprimés).
        """
        logger.info("Rollback : tentative de restauration des conteneurs précédents")
        try:
            await self._run_docker_command(
                ["docker", "compose", "-f", COMPOSE_FILE, "up", "-d"],
                timeout=DOCKER_COMMAND_TIMEOUT,
            )
            logger.info("Rollback réussi : conteneurs précédents restaurés")
        except Exception as exc:
            logger.error("Échec du rollback : %s", exc)
            # On ne relance pas l'exception — le rollback est un best-effort

    def get_status(self) -> dict:
        """Retourne l'état courant de la mise à jour.

        Returns:
            Dictionnaire avec les clés :
            - status: "idle"|"downloading"|"installing"|"restarting"|"completed"|"error"
            - progress: 0-100
            - step: Description de l'étape courante
            - error_message: Message d'erreur (None si pas d'erreur)
        """
        return {
            "status": self._status,
            "progress": self._progress,
            "step": self._step,
            "error_message": self._error_message,
        }

    # ──────────────────────────────────────────────────────────────
    # Étapes internes
    # ──────────────────────────────────────────────────────────────

    async def _download_images(self) -> None:
        """Télécharge l'archive d'images Docker depuis download_url.

        Progression : 0% → 50%
        """
        self._set_status("downloading", 0, "Téléchargement des images Docker")
        logger.info("Téléchargement des images depuis %s", self.download_url)

        try:
            # Créer un fichier temporaire pour l'archive
            tmp_file = tempfile.NamedTemporaryFile(
                suffix=".tar.gz", delete=False, prefix="judi_update_"
            )
            self._archive_path = tmp_file.name
            tmp_file.close()

            async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT) as client:
                async with client.stream("GET", self.download_url) as response:
                    response.raise_for_status()

                    total_size = int(response.headers.get("content-length", 0))
                    downloaded = 0

                    with open(self._archive_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=65536):
                            f.write(chunk)
                            downloaded += len(chunk)

                            # Mettre à jour la progression (0-50%)
                            if total_size > 0:
                                pct = int((downloaded / total_size) * 50)
                            else:
                                # Progression indéterminée, avancer lentement
                                pct = min(45, self._progress + 1)
                            self._set_status(
                                "downloading", pct, "Téléchargement des images Docker"
                            )

            self._set_status("downloading", 50, "Téléchargement terminé")
            logger.info("Téléchargement terminé : %s", self._archive_path)

        except httpx.HTTPStatusError as exc:
            error_msg = (
                f"Échec du téléchargement : HTTP {exc.response.status_code}"
            )
            logger.error(error_msg)
            self._set_status("error", self._progress, self._step, error_msg)
            raise UpdateError(error_msg, "downloading") from exc
        except (httpx.RequestError, OSError) as exc:
            error_msg = f"Échec du téléchargement : {exc}"
            logger.error(error_msg)
            self._set_status("error", self._progress, self._step, error_msg)
            raise UpdateError(error_msg, "downloading") from exc

    async def _stop_containers(self) -> None:
        """Arrête les conteneurs existants via docker compose down.

        Progression : 50% → 60%
        Note : --volumes n'est PAS utilisé pour préserver les données.
        """
        self._set_status("installing", 50, "Arrêt des conteneurs")
        logger.info("Arrêt des conteneurs (docker compose down)")

        try:
            await self._run_docker_command(
                ["docker", "compose", "-f", COMPOSE_FILE, "down"],
                timeout=DOCKER_COMMAND_TIMEOUT,
            )
            self._set_status("installing", 60, "Conteneurs arrêtés")
            logger.info("Conteneurs arrêtés avec succès")
        except Exception as exc:
            error_msg = f"Échec de l'arrêt des conteneurs : {exc}"
            logger.error(error_msg)
            self._set_status("error", self._progress, self._step, error_msg)
            raise UpdateError(error_msg, "stopping") from exc

    async def _load_images(self) -> None:
        """Charge les nouvelles images Docker via docker load.

        Progression : 60% → 80%
        """
        self._set_status("installing", 60, "Chargement des nouvelles images")
        logger.info("Chargement des images depuis %s", self._archive_path)

        if not self._archive_path or not Path(self._archive_path).exists():
            error_msg = "Archive d'images introuvable"
            self._set_status("error", self._progress, self._step, error_msg)
            raise UpdateError(error_msg, "loading")

        try:
            await self._run_docker_command(
                ["docker", "load", "-i", self._archive_path],
                timeout=DOCKER_COMMAND_TIMEOUT,
            )
            self._set_status("installing", 80, "Images chargées")
            logger.info("Images chargées avec succès")
        except Exception as exc:
            error_msg = f"Échec du chargement des images : {exc}"
            logger.error(error_msg)
            self._set_status("error", self._progress, self._step, error_msg)
            await self.rollback()
            raise UpdateError(error_msg, "loading") from exc

    async def _start_containers(self) -> None:
        """Redémarre les conteneurs via docker compose up -d.

        Progression : 80% → 95%
        """
        self._set_status("restarting", 80, "Redémarrage des conteneurs")
        logger.info("Redémarrage des conteneurs (docker compose up -d)")

        try:
            await self._run_docker_command(
                ["docker", "compose", "-f", COMPOSE_FILE, "up", "-d"],
                timeout=DOCKER_COMMAND_TIMEOUT,
            )
            self._set_status("restarting", 95, "Conteneurs redémarrés")
            logger.info("Conteneurs redémarrés avec succès")
        except Exception as exc:
            error_msg = f"Échec du redémarrage des conteneurs : {exc}"
            logger.error(error_msg)
            self._set_status("error", self._progress, self._step, error_msg)
            await self.rollback()
            raise UpdateError(error_msg, "restarting") from exc

    async def _update_config(self) -> None:
        """Met à jour LocalConfig.app_version en base de données.

        Progression : 95% → 100%
        """
        self._set_status("restarting", 95, "Mise à jour de la configuration")
        logger.info("Mise à jour de LocalConfig.app_version → %s", self.new_version)

        try:
            result = await self.db_session.execute(
                select(LocalConfig).limit(1)
            )
            config = result.scalar_one_or_none()

            if config:
                config.app_version = self.new_version
            else:
                # Cas improbable : pas de config existante
                logger.warning("Aucune LocalConfig trouvée, création impossible ici")

            await self.db_session.commit()
            logger.info("LocalConfig.app_version mis à jour")
        except Exception as exc:
            error_msg = f"Échec de la mise à jour de la configuration : {exc}"
            logger.error(error_msg)
            self._set_status("error", self._progress, self._step, error_msg)
            raise UpdateError(error_msg, "config_update") from exc

    # ──────────────────────────────────────────────────────────────
    # Utilitaires
    # ──────────────────────────────────────────────────────────────

    def _set_status(
        self,
        status: str,
        progress: int,
        step: str,
        error_message: Optional[str] = None,
    ) -> None:
        """Met à jour l'état interne de progression."""
        self._status = status
        self._progress = progress
        self._step = step
        self._error_message = error_message

    async def _run_docker_command(
        self,
        cmd: list[str],
        timeout: float = DOCKER_COMMAND_TIMEOUT,
    ) -> str:
        """Exécute une commande Docker en subprocess async.

        Args:
            cmd: Commande et arguments à exécuter.
            timeout: Timeout en secondes.

        Returns:
            Sortie standard de la commande.

        Raises:
            RuntimeError: Si la commande échoue ou dépasse le timeout.
        """
        logger.debug("Exécution : %s", " ".join(cmd))

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            raise RuntimeError(
                f"Commande expirée après {timeout}s : {' '.join(cmd)}"
            )

        if process.returncode != 0:
            stderr_text = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(
                f"Commande échouée (code {process.returncode}) : "
                f"{' '.join(cmd)}\n{stderr_text}"
            )

        return stdout.decode("utf-8", errors="replace")

    def _cleanup_temp_files(self) -> None:
        """Supprime les fichiers temporaires créés pendant la mise à jour."""
        if self._archive_path and Path(self._archive_path).exists():
            try:
                Path(self._archive_path).unlink()
                logger.debug("Fichier temporaire supprimé : %s", self._archive_path)
            except OSError as exc:
                logger.warning(
                    "Impossible de supprimer le fichier temporaire %s : %s",
                    self._archive_path,
                    exc,
                )
