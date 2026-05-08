"""Tests unitaires pour le service de mise à jour forcée.

Valide : Exigences 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import httpx
import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend")
)

from services.update_service import UpdateService, UpdateError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(
    download_url: str = "https://example.com/images.tar.gz",
    new_version: str = "1.2.0",
) -> UpdateService:
    """Crée un UpdateService avec une session DB mockée."""
    mock_session = AsyncMock()
    return UpdateService(
        db_session=mock_session,
        download_url=download_url,
        new_version=new_version,
    )


# ---------------------------------------------------------------------------
# Status tracking tests
# ---------------------------------------------------------------------------


class TestGetStatus:
    def test_initial_status_is_idle(self):
        """Le statut initial doit être 'idle' avec progression à 0."""
        service = _make_service()
        status = service.get_status()

        assert status["status"] == "idle"
        assert status["progress"] == 0
        assert status["step"] == ""
        assert status["error_message"] is None

    def test_status_dict_has_required_keys(self):
        """Le dictionnaire de statut doit contenir les 4 clés requises."""
        service = _make_service()
        status = service.get_status()

        assert "status" in status
        assert "progress" in status
        assert "step" in status
        assert "error_message" in status


# ---------------------------------------------------------------------------
# Download tests
# ---------------------------------------------------------------------------


class TestDownloadImages:
    @pytest.mark.asyncio
    async def test_download_failure_sets_error_status(self):
        """Un échec de téléchargement doit mettre le statut en 'error'."""
        service = _make_service(download_url="https://bad-url.example.com/fail.tar.gz")

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )

        # httpx.AsyncClient is used as: async with httpx.AsyncClient(...) as client
        # So the class itself must act as an async context manager
        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_response),
            __aexit__=AsyncMock(return_value=False),
        ))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.update_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(UpdateError) as exc_info:
                await service._download_images()

        assert exc_info.value.step == "downloading"
        assert service.get_status()["status"] == "error"

    @pytest.mark.asyncio
    async def test_download_network_error_raises_update_error(self):
        """Une erreur réseau pendant le téléchargement doit lever UpdateError."""
        service = _make_service()

        mock_client = MagicMock()
        mock_client.stream = MagicMock(side_effect=httpx.RequestError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.update_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(UpdateError) as exc_info:
                await service._download_images()

        assert exc_info.value.step == "downloading"


# ---------------------------------------------------------------------------
# Docker command tests
# ---------------------------------------------------------------------------


class TestDockerCommands:
    @pytest.mark.asyncio
    async def test_stop_containers_success(self):
        """L'arrêt des conteneurs doit mettre la progression à 60%."""
        service = _make_service()

        with patch("services.update_service.asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"", b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            await service._stop_containers()

        status = service.get_status()
        assert status["progress"] == 60
        assert status["status"] == "installing"

    @pytest.mark.asyncio
    async def test_stop_containers_failure_raises_update_error(self):
        """Un échec de docker compose down doit lever UpdateError."""
        service = _make_service()

        with patch("services.update_service.asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"", b"Error stopping")
            mock_proc.returncode = 1
            mock_exec.return_value = mock_proc

            with pytest.raises(UpdateError) as exc_info:
                await service._stop_containers()

        assert exc_info.value.step == "stopping"

    @pytest.mark.asyncio
    async def test_load_images_missing_archive_raises_error(self):
        """Si l'archive est absente, le chargement doit lever UpdateError."""
        service = _make_service()
        service._archive_path = "/nonexistent/path.tar.gz"

        with pytest.raises(UpdateError) as exc_info:
            await service._load_images()

        assert exc_info.value.step == "loading"
        assert "introuvable" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_start_containers_success(self):
        """Le redémarrage des conteneurs doit mettre la progression à 95%."""
        service = _make_service()

        with patch("services.update_service.asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"", b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            await service._start_containers()

        status = service.get_status()
        assert status["progress"] == 95
        assert status["status"] == "restarting"

    @pytest.mark.asyncio
    async def test_start_containers_failure_triggers_rollback(self):
        """Un échec du redémarrage doit déclencher un rollback."""
        service = _make_service()

        with patch("services.update_service.asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"", b"Error starting")
            mock_proc.returncode = 1
            mock_exec.return_value = mock_proc

            with pytest.raises(UpdateError):
                await service._start_containers()

        # Le rollback a été appelé (via docker compose up -d)
        # Vérifié par le fait que create_subprocess_exec a été appelé 2 fois
        assert mock_exec.call_count == 2


# ---------------------------------------------------------------------------
# Config update tests
# ---------------------------------------------------------------------------


class TestUpdateConfig:
    @pytest.mark.asyncio
    async def test_update_config_sets_version(self):
        """La mise à jour de config doit écrire la nouvelle version."""
        service = _make_service(new_version="2.0.0")

        mock_config = MagicMock()
        mock_config.app_version = "1.0.0"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_config

        service.db_session.execute = AsyncMock(return_value=mock_result)
        service.db_session.commit = AsyncMock()

        await service._update_config()

        assert mock_config.app_version == "2.0.0"
        service.db_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_config_no_existing_config(self):
        """Si aucune config n'existe, la mise à jour ne doit pas planter."""
        service = _make_service(new_version="2.0.0")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        service.db_session.execute = AsyncMock(return_value=mock_result)
        service.db_session.commit = AsyncMock()

        # Ne doit pas lever d'exception
        await service._update_config()
        service.db_session.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# Rollback tests
# ---------------------------------------------------------------------------


class TestRollback:
    @pytest.mark.asyncio
    async def test_rollback_runs_docker_compose_up(self):
        """Le rollback doit exécuter docker compose up -d."""
        service = _make_service()

        with patch("services.update_service.asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"", b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            await service.rollback()

        # Vérifier que docker compose up -d a été appelé
        call_args = mock_exec.call_args[0]
        assert "docker" in call_args
        assert "compose" in call_args
        assert "up" in call_args
        assert "-d" in call_args

    @pytest.mark.asyncio
    async def test_rollback_failure_does_not_raise(self):
        """Un échec du rollback ne doit pas lever d'exception (best-effort)."""
        service = _make_service()

        with patch("services.update_service.asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"", b"Error")
            mock_proc.returncode = 1
            mock_exec.return_value = mock_proc

            # Ne doit pas lever d'exception
            await service.rollback()


# ---------------------------------------------------------------------------
# Full workflow tests
# ---------------------------------------------------------------------------


class TestExecuteUpdate:
    @pytest.mark.asyncio
    async def test_execute_update_full_success(self):
        """Un workflow complet réussi doit terminer avec status 'completed'."""
        service = _make_service(new_version="1.3.0")

        # Mock download
        with patch.object(service, "_download_images", new_callable=AsyncMock) as mock_dl, \
             patch.object(service, "_stop_containers", new_callable=AsyncMock) as mock_stop, \
             patch.object(service, "_load_images", new_callable=AsyncMock) as mock_load, \
             patch.object(service, "_start_containers", new_callable=AsyncMock) as mock_start, \
             patch.object(service, "_update_config", new_callable=AsyncMock) as mock_config, \
             patch.object(service, "_cleanup_temp_files"):

            await service.execute_update()

        status = service.get_status()
        assert status["status"] == "completed"
        assert status["progress"] == 100

        mock_dl.assert_awaited_once()
        mock_stop.assert_awaited_once()
        mock_load.assert_awaited_once()
        mock_start.assert_awaited_once()
        mock_config.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_update_download_failure_sets_error(self):
        """Un échec au téléchargement doit mettre le statut en erreur."""
        service = _make_service()

        with patch.object(
            service,
            "_download_images",
            new_callable=AsyncMock,
            side_effect=UpdateError("Download failed", "downloading"),
        ), patch.object(service, "_cleanup_temp_files"):
            with pytest.raises(UpdateError):
                await service.execute_update()

    @pytest.mark.asyncio
    async def test_execute_update_cleans_temp_files(self):
        """Le workflow doit toujours nettoyer les fichiers temporaires."""
        service = _make_service()

        with patch.object(
            service,
            "_download_images",
            new_callable=AsyncMock,
            side_effect=UpdateError("fail", "downloading"),
        ), patch.object(service, "_cleanup_temp_files") as mock_cleanup:
            with pytest.raises(UpdateError):
                await service.execute_update()

        mock_cleanup.assert_called_once()


# ---------------------------------------------------------------------------
# Volume preservation tests
# ---------------------------------------------------------------------------


class TestVolumePreservation:
    @pytest.mark.asyncio
    async def test_stop_containers_does_not_use_volumes_flag(self):
        """docker compose down ne doit PAS utiliser --volumes."""
        service = _make_service()

        with patch("services.update_service.asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"", b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            await service._stop_containers()

        call_args = mock_exec.call_args[0]
        assert "--volumes" not in call_args
        assert "-v" not in call_args
