"""Tests par propriété — Endpoints fichiers d'étape.

# Feature: step-files-management, Property 6: Download endpoint returns attachment disposition
# Feature: step-files-management, Property 7: View endpoint returns inline disposition
# Feature: step-files-management, Property 8: Replace is rejected on validated steps

**Validates: Requirements 3.2, 7.1, 7.2, 7.4, 7.5, 4.5**

Propriétés 6–8 : Vérifient le comportement des endpoints download, view
et replace du router step_files via des requêtes HTTP réelles contre
l'application FastAPI avec une base SQLite en mémoire.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
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
# Strategies
# ---------------------------------------------------------------------------

VALID_EXTENSIONS = [".md", ".pdf", ".docx", ".zip"]
CONTENT_TYPE_MAP = {
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".docx": (
        "application/vnd.openxmlformats-officedocument"
        ".wordprocessingml.document"
    ),
    ".zip": "application/zip",
}

valid_stems = st.from_regex(r"[a-z][a-z0-9_]{0,19}", fullmatch=True)
valid_extensions = st.sampled_from(VALID_EXTENSIONS)
valid_filenames = st.tuples(valid_stems, valid_extensions).map(
    lambda t: f"{t[0]}{t[1]}"
)
valid_content = st.binary(min_size=1, max_size=4096)


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
    """Répertoire temporaire servant de DATA_DIR pour les tests."""
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

    # Patcher DATA_DIR dans le module step_files
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
    filename: str,
    content: bytes,
    step_number: int = 0,
    statut: str = "réalisé",
) -> tuple[int, int, int]:
    """Crée un dossier, une étape et un StepFile en base + fichier sur disque.

    Returns:
        Tuple (dossier_id, step_id, step_file_id).
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

        # Créer le répertoire et le fichier sur disque
        step_dir = Path(tmp_data_dir) / "dossiers" / str(dossier.id) / f"step{step_number}"
        step_dir.mkdir(parents=True, exist_ok=True)
        file_path = step_dir / filename
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

        return dossier.id, step.id, step_file.id


# ---------------------------------------------------------------------------
# Property 6: Download endpoint returns attachment disposition with original
# filename
# Feature: step-files-management, Property 6
# Validates: Requirements 3.2, 7.1
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    filename=valid_filenames,
    content=valid_content,
)
@pytest.mark.asyncio
async def test_download_returns_attachment_with_original_filename(
    client: AsyncClient,
    session_factory,
    tmp_data_dir: str,
    filename: str,
    content: bytes,
) -> None:
    """Le download retourne Content-Disposition: attachment avec le nom original."""
    dossier_id, _, file_id = await _create_dossier_step_and_file(
        session_factory, tmp_data_dir, filename, content,
    )

    resp = await client.get(
        f"/api/dossiers/{dossier_id}/steps/0/files/{file_id}/download"
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    # Vérifier Content-Disposition: attachment avec le bon filename
    cd = resp.headers.get("content-disposition", "")
    assert "attachment" in cd, f"Expected 'attachment' in Content-Disposition, got: {cd}"
    assert filename in cd, f"Expected filename '{filename}' in Content-Disposition, got: {cd}"

    # Vérifier que le corps correspond au contenu du fichier
    assert resp.content == content


# ---------------------------------------------------------------------------
# Property 7: View endpoint returns inline disposition
# Feature: step-files-management, Property 7
# Validates: Requirements 7.2
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    filename=valid_filenames,
    content=valid_content,
)
@pytest.mark.asyncio
async def test_view_returns_inline_disposition_with_correct_content_type(
    client: AsyncClient,
    session_factory,
    tmp_data_dir: str,
    filename: str,
    content: bytes,
) -> None:
    """Le view retourne Content-Disposition: inline et le bon Content-Type."""
    dossier_id, _, file_id = await _create_dossier_step_and_file(
        session_factory, tmp_data_dir, filename, content,
    )

    resp = await client.get(
        f"/api/dossiers/{dossier_id}/steps/0/files/{file_id}/view"
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    # Vérifier Content-Disposition: inline
    cd = resp.headers.get("content-disposition", "")
    assert "inline" in cd, f"Expected 'inline' in Content-Disposition, got: {cd}"

    # Vérifier le Content-Type correct
    ext = Path(filename).suffix.lower()
    expected_ct = CONTENT_TYPE_MAP.get(ext, "application/octet-stream")
    actual_ct = resp.headers.get("content-type", "")
    assert expected_ct in actual_ct, (
        f"Expected Content-Type '{expected_ct}', got: {actual_ct}"
    )


# ---------------------------------------------------------------------------
# Property 8: Replace is rejected on validated steps
# Feature: step-files-management, Property 8
# Validates: Requirements 7.4, 7.5, 4.5
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    filename=valid_filenames,
    original_content=valid_content,
    new_content=valid_content,
)
@pytest.mark.asyncio
async def test_replace_rejected_on_validated_step(
    client: AsyncClient,
    session_factory,
    tmp_data_dir: str,
    filename: str,
    original_content: bytes,
    new_content: bytes,
) -> None:
    """Le remplacement est rejeté (403) quand l'étape est validée."""
    dossier_id, _, file_id = await _create_dossier_step_and_file(
        session_factory,
        tmp_data_dir,
        filename,
        original_content,
        statut="validé",
    )

    resp = await client.post(
        f"/api/dossiers/{dossier_id}/steps/0/files/{file_id}/replace",
        files={"file": (filename, new_content)},
    )

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    # Vérifier que le message d'erreur est correct
    detail = resp.json().get("detail", "")
    assert "verrouillée" in detail.lower() or "modification impossible" in detail.lower(), (
        f"Expected lock message, got: {detail}"
    )

    # Vérifier que le fichier sur disque est inchangé
    step_dir = Path(tmp_data_dir) / "dossiers" / str(dossier_id) / "step0"
    original_path = step_dir / filename
    assert original_path.read_bytes() == original_content, (
        "Le fichier sur disque ne devrait pas avoir changé"
    )

    # Vérifier que le StepFile est inchangé en base
    async with session_factory() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(StepFile).where(StepFile.id == file_id)
        )
        sf = result.scalar_one()
        assert sf.is_modified is False, "is_modified ne devrait pas avoir changé"
        assert sf.original_file_path is None, "original_file_path ne devrait pas avoir changé"
        assert sf.file_size == len(original_content), "file_size ne devrait pas avoir changé"
