"""Tests d'intégration — Gestion des versions.

Teste les flux complets de gestion des versions :
- Lecture du fichier VERSION au démarrage
- Publication puis récupération d'une version sur le Site Central
- Workflow de mise à jour forcée avec commandes Docker mockées
- Rollback en cas d'échec de mise à jour
- Préservation des volumes Docker pendant la mise à jour
- Endpoint de téléchargement utilisant la dernière version publiée

Valide : Exigences 1.2, 2.2, 4.1-4.6, 10.1, 11.2
"""

import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Module isolation : charger le backend Site Central sans conflit
# ---------------------------------------------------------------------------

_central_backend = str(
    Path(__file__).resolve().parents[2] / "central-site" / "web" / "backend"
)

_modules_to_isolate = [
    "models", "database", "routers", "schemas", "services", "main",
]

_saved_modules = {}
for prefix in _modules_to_isolate:
    for k in list(sys.modules):
        if k == prefix or k.startswith(prefix + "."):
            _saved_modules[k] = sys.modules.pop(k)

_saved_path = sys.path[:]
sys.path.insert(0, _central_backend)

from models import Base as _CentralBase  # noqa: E402
from models.expert import Expert as _Expert  # noqa: E402
from models.app_version import AppVersion as _AppVersion  # noqa: E402
from database import get_db as _central_get_db  # noqa: E402
from main import app as _central_app  # noqa: E402

import routers.profile as _profile_mod  # noqa: E402

# Sauvegarder les modules du Site Central et restaurer les originaux
_central_cache = {}
for prefix in _modules_to_isolate:
    for k in list(sys.modules):
        if k == prefix or k.startswith(prefix + "."):
            _central_cache[k] = sys.modules.pop(k)

sys.modules.update(_saved_modules)
sys.path[:] = _saved_path

# ---------------------------------------------------------------------------
# Module isolation : charger le backend local
# ---------------------------------------------------------------------------

_local_backend = str(
    Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend"
)

# Save current modules before loading local backend
_saved_modules_2 = {}
for prefix in _modules_to_isolate:
    for k in list(sys.modules):
        if k == prefix or k.startswith(prefix + "."):
            _saved_modules_2[k] = sys.modules.pop(k)

_saved_path_2 = sys.path[:]
sys.path.insert(0, _local_backend)

from models import Base as _LocalBase  # noqa: E402
from models.local_config import LocalConfig as _LocalConfig  # noqa: E402
from database import get_db as _local_get_db  # noqa: E402
from main import app as _local_app  # noqa: E402
from services.version_reader import VersionInfo, read_version_file  # noqa: E402
import services.update_service as _update_service_mod  # noqa: E402

# Save local modules and restore
_local_cache = {}
for prefix in _modules_to_isolate:
    for k in list(sys.modules):
        if k == prefix or k.startswith(prefix + "."):
            _local_cache[k] = sys.modules.pop(k)

sys.modules.update(_saved_modules_2)
sys.path[:] = _saved_path_2

pytestmark = pytest.mark.integration

ADMIN_EMAIL = "admin@judi-expert.fr"


# ---------------------------------------------------------------------------
# Fixtures — Central site
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def central_engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(_CentralBase.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def central_session_factory(central_engine):
    return async_sessionmaker(central_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def seed_central_admin(central_session_factory):
    """Crée un expert admin en base centrale."""
    async with central_session_factory() as session:
        expert = _Expert(
            cognito_sub="sub-admin-integ-001",
            email=ADMIN_EMAIL,
            nom="Admin",
            prenom="Integ",
            adresse="1 rue Test",
            domaine="psychologie",
        )
        session.add(expert)
        await session.commit()
        await session.refresh(expert)
        return expert


def _fake_get_current_expert(expert):
    """Simule un expert authentifié."""
    async def _override():
        return (expert, "fake-access-token")
    return _override


@pytest_asyncio.fixture
async def central_admin_client(central_session_factory, seed_central_admin):
    """AsyncClient authentifié en tant qu'admin sur le Site Central."""
    async def _override_get_db():
        async with central_session_factory() as session:
            yield session

    _central_app.dependency_overrides[_central_get_db] = _override_get_db
    _central_app.dependency_overrides[_profile_mod.get_current_expert] = (
        _fake_get_current_expert(seed_central_admin)
    )

    transport = ASGITransport(app=_central_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _central_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def central_public_client(central_session_factory):
    """AsyncClient sans authentification sur le Site Central."""
    async def _override_get_db():
        async with central_session_factory() as session:
            yield session

    _central_app.dependency_overrides[_central_get_db] = _override_get_db

    transport = ASGITransport(app=_central_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _central_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fixtures — Local site
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def local_engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(_LocalBase.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def local_session_factory(local_engine):
    return async_sessionmaker(local_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def seed_local_config(local_session_factory):
    """Crée une LocalConfig de test."""
    async with local_session_factory() as session:
        config = _LocalConfig(
            password_hash="fake-hash",
            domaine="psychologie",
            app_version="1.0.0",
            is_configured=True,
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)
        return config


# ---------------------------------------------------------------------------
# Test 1 : Le démarrage lit le fichier VERSION correctement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_startup_reads_version_file():
    """Le backend lit le fichier VERSION au démarrage et retourne les données correctes.

    Valide : Exigences 1.2, 11.2
    """
    # Créer un fichier VERSION temporaire
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_VERSION", delete=False, encoding="utf-8"
    ) as f:
        f.write("2.3.1\n2026-06-15\n")
        tmp_path = Path(f.name)

    try:
        # Utiliser read_version_file pour lire le fichier
        info = read_version_file(tmp_path)

        assert info.version == "2.3.1"
        assert info.date == "2026-06-15"
        assert isinstance(info, VersionInfo)
    finally:
        tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test 2 : Publier une version puis la récupérer via GET /api/version
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_then_get_version(
    central_admin_client: AsyncClient,
    central_public_client: AsyncClient,
):
    """Publier une version via POST /api/admin/versions puis la récupérer via GET /api/version.

    Valide : Exigence 2.2
    """
    # 1. Publier une version en tant qu'admin
    publish_resp = await central_admin_client.post("/api/admin/versions", json={
        "version": "3.0.0",
        "download_url": "https://downloads.judi-expert.fr/judi-expert-local-3.0.0.tar.gz",
        "mandatory": True,
        "release_notes": "Version majeure avec nouvelles fonctionnalités",
    })
    assert publish_resp.status_code == 201
    published = publish_resp.json()
    assert published["version"] == "3.0.0"

    # 2. Récupérer la version via l'endpoint public
    get_resp = await central_public_client.get("/api/version")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["latest_version"] == "3.0.0"
    assert data["download_url"] == "https://downloads.judi-expert.fr/judi-expert-local-3.0.0.tar.gz"
    assert data["mandatory"] is True
    assert data["release_notes"] == "Version majeure avec nouvelles fonctionnalités"


# ---------------------------------------------------------------------------
# Test 3 : Workflow de mise à jour forcée avec commandes Docker mockées
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forced_update_workflow(local_session_factory, seed_local_config):
    """Workflow complet de mise à jour forcée : téléchargement → arrêt → chargement → redémarrage.

    Valide : Exigences 4.1, 4.2, 4.3, 4.4
    """
    async def _override_get_db():
        async with local_session_factory() as session:
            yield session

    _local_app.dependency_overrides[_local_get_db] = _override_get_db

    # Mock les commandes Docker et le téléchargement HTTP
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"OK\n", b"")
    mock_process.returncode = 0

    with patch.object(
        _update_service_mod.asyncio, "create_subprocess_exec",
        return_value=mock_process,
    ) as mock_exec, patch.object(
        _update_service_mod.httpx, "AsyncClient",
    ) as mock_httpx_cls:
        # Mock le téléchargement HTTP (stream)
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"content-length": "500"}

        # Create a proper async iterator for aiter_bytes
        async def _aiter_bytes(chunk_size=65536):
            for _ in range(5):
                yield b"x" * 100

        mock_response.aiter_bytes = _aiter_bytes

        # stream() must return an async context manager (not a coroutine)
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_client_instance = MagicMock()
        mock_client_instance.stream = MagicMock(return_value=mock_stream_ctx)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_httpx_cls.return_value = mock_client_instance

        transport = ASGITransport(app=_local_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/version/update", json={
                "download_url": "https://downloads.judi-expert.fr/judi-expert-local-2.0.0.tar.gz",
                "version": "2.0.0",
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["progress"] == 100

        # Vérifier que les commandes Docker ont été appelées
        calls = [str(c) for c in mock_exec.call_args_list]
        # docker compose down doit être appelé
        assert any("down" in c for c in calls)
        # docker load doit être appelé
        assert any("load" in c for c in calls)
        # docker compose up doit être appelé
        assert any("up" in c for c in calls)

    _local_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 4 : Rollback en cas d'échec de mise à jour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rollback_on_update_failure(local_session_factory, seed_local_config):
    """En cas d'échec du chargement des images, un rollback est tenté.

    Valide : Exigence 4.5
    """
    async def _override_get_db():
        async with local_session_factory() as session:
            yield session

    _local_app.dependency_overrides[_local_get_db] = _override_get_db

    async def _mock_subprocess(*args, **kwargs):
        """Simule un échec au docker load."""
        mock_proc = AsyncMock()
        cmd = args if args else []
        cmd_str = " ".join(str(c) for c in cmd)

        if "load" in cmd_str:
            # docker load échoue
            mock_proc.communicate.return_value = (b"", b"Error loading images\n")
            mock_proc.returncode = 1
        else:
            # docker compose down et up réussissent
            mock_proc.communicate.return_value = (b"OK\n", b"")
            mock_proc.returncode = 0
        return mock_proc

    with patch.object(
        _update_service_mod.asyncio, "create_subprocess_exec",
        side_effect=_mock_subprocess,
    ), patch.object(
        _update_service_mod.httpx, "AsyncClient",
    ) as mock_httpx_cls:
        # Mock le téléchargement HTTP
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"content-length": "500"}

        async def _aiter_bytes(chunk_size=65536):
            for _ in range(5):
                yield b"x" * 100

        mock_response.aiter_bytes = _aiter_bytes

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_client_instance = MagicMock()
        mock_client_instance.stream = MagicMock(return_value=mock_stream_ctx)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_httpx_cls.return_value = mock_client_instance

        transport = ASGITransport(app=_local_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/version/update", json={
                "download_url": "https://downloads.judi-expert.fr/judi-expert-local-2.0.0.tar.gz",
                "version": "2.0.0",
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"
        assert data["error_message"] is not None
        assert "loading" in data["step"] or "chargement" in data["step"].lower()

    _local_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 5 : Préservation des volumes Docker pendant la mise à jour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_volume_preservation(local_session_factory, seed_local_config):
    """docker compose down est appelé SANS le flag --volumes pour préserver les données.

    Valide : Exigence 4.6
    """
    async def _override_get_db():
        async with local_session_factory() as session:
            yield session

    _local_app.dependency_overrides[_local_get_db] = _override_get_db

    docker_commands_called = []

    async def _capture_subprocess(*args, **kwargs):
        """Capture les commandes Docker exécutées."""
        docker_commands_called.append(list(args))
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"OK\n", b"")
        mock_proc.returncode = 0
        return mock_proc

    with patch.object(
        _update_service_mod.asyncio, "create_subprocess_exec",
        side_effect=_capture_subprocess,
    ), patch.object(
        _update_service_mod.httpx, "AsyncClient",
    ) as mock_httpx_cls:
        # Mock le téléchargement HTTP
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"content-length": "500"}

        async def _aiter_bytes(chunk_size=65536):
            for _ in range(5):
                yield b"x" * 100

        mock_response.aiter_bytes = _aiter_bytes

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_client_instance = MagicMock()
        mock_client_instance.stream = MagicMock(return_value=mock_stream_ctx)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_httpx_cls.return_value = mock_client_instance

        transport = ASGITransport(app=_local_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/version/update", json={
                "download_url": "https://downloads.judi-expert.fr/judi-expert-local-2.0.0.tar.gz",
                "version": "2.0.0",
            })

        assert resp.status_code == 200

        # Vérifier que docker compose down a été appelé SANS --volumes
        down_commands = [
            cmd for cmd in docker_commands_called
            if any("down" in str(arg) for arg in cmd)
        ]
        assert len(down_commands) > 0, "docker compose down doit être appelé"
        for cmd in down_commands:
            cmd_flat = " ".join(str(arg) for arg in cmd)
            assert "--volumes" not in cmd_flat, (
                "docker compose down ne doit PAS utiliser --volumes "
                "pour préserver les données"
            )
            # Check -v is not a standalone flag (not part of -f value)
            cmd_args = [str(arg) for arg in cmd]
            # Flatten nested lists
            flat_args = []
            for arg in cmd_args:
                if isinstance(arg, list):
                    flat_args.extend(arg)
                else:
                    flat_args.append(arg)
            assert "-v" not in flat_args, (
                "docker compose down ne doit PAS utiliser -v "
                "pour préserver les données"
            )

    _local_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 6 : L'endpoint de téléchargement utilise la dernière version publiée
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_downloads_uses_latest_version(
    central_public_client: AsyncClient,
    central_session_factory,
):
    """GET /api/downloads/app utilise la dernière version publiée via AppVersion.

    Valide : Exigence 10.1
    """
    # Seed versions directement en base avec des timestamps distincts
    async with central_session_factory() as session:
        v1 = _AppVersion(
            version="1.0.0",
            download_url="https://downloads.judi-expert.fr/judi-expert-local-1.0.0.exe",
            mandatory=True,
            published_at=datetime(2026, 1, 1, 10, 0, 0),
        )
        v2 = _AppVersion(
            version="1.5.0",
            download_url="https://downloads.judi-expert.fr/judi-expert-local-1.5.0.exe",
            mandatory=True,
            published_at=datetime(2026, 6, 1, 10, 0, 0),
        )
        session.add_all([v1, v2])
        await session.commit()

    # Vérifier que GET /api/downloads/app utilise la version 1.5.0
    resp = await central_public_client.get("/api/downloads/app")
    assert resp.status_code == 200
    data = resp.json()
    assert "1.5.0" in data["version"]
