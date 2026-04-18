"""Tests unitaires pour le router step_files.

Valide : Exigences 2.5, 3.4, 4.5, 4.6, 7.4, 7.5

Tests ciblés :
- download retourne 404 quand le fichier n'existe pas sur le disque
- view retourne 404 quand le fichier n'existe pas sur le disque
- replace retourne 403 quand l'étape est validée
- replace retourne 400 quand l'extension ne correspond pas
- replace retourne 400 quand le fichier uploadé est vide
- StepFile créé avec is_modified=False par défaut
- StepFile créé avec original_file_path=None par défaut
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Backend sur le path
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / "local-site"
        / "web"
        / "backend"
    ),
)

from database import get_db
from main import app
from models import Base, Dossier, Step, StepFile
from routers.auth import get_current_user


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def tmp_data_dir():
    """Répertoire temporaire servant de DATA_DIR."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest_asyncio.fixture
async def client(session_factory, tmp_data_dir):
    """AsyncClient avec DB en mémoire, auth mockée et DATA_DIR temporaire."""

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    async def _override_auth():
        return {"sub": "local_admin", "domaine": "psychologie"}

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_auth

    import routers.step_files as sf_module
    original_data_dir = sf_module.DATA_DIR
    sf_module.DATA_DIR = tmp_data_dir

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    sf_module.DATA_DIR = original_data_dir
    app.dependency_overrides.clear()


async def _create_dossier_step_and_file(
    session_factory,
    tmp_data_dir: str,
    filename: str = "rapport.md",
    content: bytes = b"# Contenu original",
    step_number: int = 0,
    statut: str = "réalisé",
    write_to_disk: bool = True,
) -> tuple[int, int, int, str]:
    """Crée un dossier, une étape et un StepFile.

    Returns:
        Tuple (dossier_id, step_id, step_file_id, file_path_on_disk).
    """
    async with session_factory() as session:
        dossier = Dossier(
            nom="Test Dossier",
            ticket_id=f"T-{os.urandom(4).hex()}",
            domaine="psychologie",
        )
        session.add(dossier)
        await session.flush()

        step = Step(
            dossier_id=dossier.id,
            step_number=step_number,
            statut=statut,
        )
        session.add(step)
        await session.flush()

        step_dir = Path(tmp_data_dir) / "dossiers" / str(dossier.id) / f"step{step_number}"
        step_dir.mkdir(parents=True, exist_ok=True)
        file_path = step_dir / filename

        if write_to_disk:
            file_path.write_bytes(content)

        ext = Path(filename).suffix.lower()
        step_file = StepFile(
            step_id=step.id,
            filename=filename,
            file_path=str(file_path),
            file_type=ext.lstrip("."),
            file_size=len(content),
        )
        session.add(step_file)
        await session.commit()

        return dossier.id, step.id, step_file.id, str(file_path)


# ---------------------------------------------------------------------------
# Download — 404 quand fichier absent du disque
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_download_returns_404_when_file_missing_on_disk(
    client: AsyncClient, session_factory, tmp_data_dir: str,
) -> None:
    """Download retourne 404 si le fichier n'existe pas sur le disque."""
    dossier_id, _, file_id, _ = await _create_dossier_step_and_file(
        session_factory, tmp_data_dir, write_to_disk=False,
    )

    resp = await client.get(
        f"/api/dossiers/{dossier_id}/steps/0/files/{file_id}/download"
    )

    assert resp.status_code == 404
    assert "introuvable" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# View — 404 quand fichier absent du disque
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_view_returns_404_when_file_missing_on_disk(
    client: AsyncClient, session_factory, tmp_data_dir: str,
) -> None:
    """View retourne 404 si le fichier n'existe pas sur le disque."""
    dossier_id, _, file_id, _ = await _create_dossier_step_and_file(
        session_factory, tmp_data_dir, write_to_disk=False,
    )

    resp = await client.get(
        f"/api/dossiers/{dossier_id}/steps/0/files/{file_id}/view"
    )

    assert resp.status_code == 404
    assert "introuvable" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Replace — 403 quand étape validée
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_replace_returns_403_when_step_validated(
    client: AsyncClient, session_factory, tmp_data_dir: str,
) -> None:
    """Replace retourne 403 si l'étape est validée (verrouillée)."""
    dossier_id, _, file_id, _ = await _create_dossier_step_and_file(
        session_factory, tmp_data_dir, statut="validé",
    )

    resp = await client.post(
        f"/api/dossiers/{dossier_id}/steps/0/files/{file_id}/replace",
        files={"file": ("rapport.md", b"nouveau contenu")},
    )

    assert resp.status_code == 403
    detail = resp.json()["detail"].lower()
    assert "verrouillée" in detail or "modification impossible" in detail


# ---------------------------------------------------------------------------
# Replace — 400 quand extension différente
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_replace_returns_400_when_extension_mismatch(
    client: AsyncClient, session_factory, tmp_data_dir: str,
) -> None:
    """Replace retourne 400 si l'extension du fichier uploadé diffère."""
    dossier_id, _, file_id, _ = await _create_dossier_step_and_file(
        session_factory, tmp_data_dir, filename="rapport.md",
    )

    # Upload un .pdf au lieu d'un .md
    resp = await client.post(
        f"/api/dossiers/{dossier_id}/steps/0/files/{file_id}/replace",
        files={"file": ("rapport.pdf", b"fake pdf content")},
    )

    assert resp.status_code == 400
    assert "même extension" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Replace — 400 quand fichier vide
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_replace_returns_400_when_file_empty(
    client: AsyncClient, session_factory, tmp_data_dir: str,
) -> None:
    """Replace retourne 400 si le fichier uploadé est vide."""
    dossier_id, _, file_id, _ = await _create_dossier_step_and_file(
        session_factory, tmp_data_dir, filename="rapport.md",
    )

    resp = await client.post(
        f"/api/dossiers/{dossier_id}/steps/0/files/{file_id}/replace",
        files={"file": ("rapport.md", b"")},
    )

    assert resp.status_code == 400
    assert "vide" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# StepFile defaults — is_modified=False, original_file_path=None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step_file_defaults_is_modified_false(
    session_factory,
) -> None:
    """Un StepFile nouvellement créé a is_modified=False."""
    async with session_factory() as session:
        dossier = Dossier(
            nom="Test", ticket_id="T-DEF1", domaine="psychologie",
        )
        session.add(dossier)
        await session.flush()

        step = Step(dossier_id=dossier.id, step_number=0, statut="initial")
        session.add(step)
        await session.flush()

        sf = StepFile(
            step_id=step.id,
            filename="test.md",
            file_path="/tmp/test.md",
            file_type="md",
            file_size=100,
        )
        session.add(sf)
        await session.commit()
        await session.refresh(sf)

        assert sf.is_modified is False


@pytest.mark.asyncio
async def test_step_file_defaults_original_file_path_none(
    session_factory,
) -> None:
    """Un StepFile nouvellement créé a original_file_path=None."""
    async with session_factory() as session:
        dossier = Dossier(
            nom="Test", ticket_id="T-DEF2", domaine="psychologie",
        )
        session.add(dossier)
        await session.flush()

        step = Step(dossier_id=dossier.id, step_number=0, statut="initial")
        session.add(step)
        await session.flush()

        sf = StepFile(
            step_id=step.id,
            filename="test.md",
            file_path="/tmp/test.md",
            file_type="md",
            file_size=100,
        )
        session.add(sf)
        await session.commit()
        await session.refresh(sf)

        assert sf.original_file_path is None
