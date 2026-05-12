"""Tests par propriété — Remplacement de fichier via endpoint dossier.

# Feature: workflow-dossier-refactor, Property 9: File replacement round-trip
# Feature: workflow-dossier-refactor, Property 10: Validated step blocks file replacement

**Validates: Requirements 9.3, 9.4, 9.5**

Propriété 9 : Pour tout contenu de remplacement uploadé via PUT
/api/dossiers/{id}/files/{file_id}/replace, le fichier sur disque
contient exactement le nouveau contenu et StepFile.file_size correspond
à la taille réelle du fichier.

Propriété 10 : Pour toute étape avec statut "validé", le remplacement
est rejeté HTTP 403 et le fichier original reste inchangé.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

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

VALID_EXTENSIONS = [".md", ".pdf", ".docx"]

valid_stems = st.from_regex(r"[a-z][a-z0-9_]{0,19}", fullmatch=True)
valid_extensions = st.sampled_from(VALID_EXTENSIONS)
valid_filenames = st.tuples(valid_stems, valid_extensions).map(
    lambda t: f"{t[0]}{t[1]}"
)
# Contenu binaire non vide (1 à 4096 octets)
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

    # Patcher DATA_DIR dans le module file_paths
    from unittest.mock import patch

    with patch("services.file_paths.DATA_DIR", tmp_data_dir):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


async def _create_dossier_step_and_file(
    session_factory,
    tmp_data_dir: str,
    filename: str,
    content: bytes,
    step_number: int = 2,
    step_statut: str = "fait",
    dossier_statut: str = "actif",
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
            statut=dossier_statut,
        )
        session.add(dossier)
        await session.flush()

        step = Step(
            dossier_id=dossier.id,
            step_number=step_number,
            statut=step_statut,
        )
        session.add(step)
        await session.flush()

        # Créer le répertoire et le fichier sur disque
        # Use the same path structure as the router: {DATA_DIR}/{dossier_name}/step{n}/out/
        from services.file_paths import _slugify
        step_dir = (
            Path(tmp_data_dir) / _slugify(dossier.nom) / f"step{step_number}" / "out"
        )
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
# Property 9 — File replacement round-trip
# Feature: workflow-dossier-refactor, Property 9
# Validates: Requirements 9.3, 9.4
# ---------------------------------------------------------------------------


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    filename=valid_filenames,
    original_content=valid_content,
    new_content=valid_content,
)
@pytest.mark.asyncio
async def test_replace_file_roundtrip(
    client: AsyncClient,
    session_factory,
    tmp_data_dir: str,
    filename: str,
    original_content: bytes,
    new_content: bytes,
) -> None:
    """Après remplacement, le fichier sur disque = nouveau contenu et file_size correct."""
    dossier_id, step_id, file_id = await _create_dossier_step_and_file(
        session_factory,
        tmp_data_dir,
        filename,
        original_content,
        step_statut="fait",
        dossier_statut="actif",
    )

    resp = await client.put(
        f"/api/dossiers/{dossier_id}/files/{file_id}/replace",
        files={"file": (filename, new_content)},
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert body["new_size"] == len(new_content)

    # Vérifier le fichier sur disque
    from services.file_paths import _slugify
    step_dir = Path(tmp_data_dir) / _slugify("Test Dossier") / "step2" / "out"
    disk_path = step_dir / filename
    assert disk_path.exists(), f"Fichier manquant sur le disque : {disk_path}"
    assert disk_path.read_bytes() == new_content

    # Vérifier le StepFile en base
    from sqlalchemy import select

    async with session_factory() as session:
        result = await session.execute(
            select(StepFile).where(StepFile.id == file_id)
        )
        sf = result.scalar_one()
        assert sf.file_size == len(new_content), (
            f"file_size attendu {len(new_content)}, obtenu {sf.file_size}"
        )
        assert sf.file_size == disk_path.stat().st_size


# ---------------------------------------------------------------------------
# Property 10 — Validated step blocks file replacement
# Feature: workflow-dossier-refactor, Property 10
# Validates: Requirements 9.5
# ---------------------------------------------------------------------------


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    filename=valid_filenames,
    original_content=valid_content,
    new_content=valid_content,
)
@pytest.mark.asyncio
async def test_validated_step_blocks_replacement(
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
        step_statut="valide",
        dossier_statut="actif",
    )

    resp = await client.put(
        f"/api/dossiers/{dossier_id}/files/{file_id}/replace",
        files={"file": (filename, new_content)},
    )

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    detail = resp.json().get("detail", "")
    assert "verrouillée" in detail.lower() or "modification impossible" in detail.lower()

    # Vérifier que le fichier sur disque est inchangé
    from services.file_paths import _slugify
    step_dir = Path(tmp_data_dir) / _slugify("Test Dossier") / "step2" / "out"
    assert (step_dir / filename).read_bytes() == original_content

    # Vérifier que le StepFile est inchangé en base
    from sqlalchemy import select

    async with session_factory() as session:
        result = await session.execute(
            select(StepFile).where(StepFile.id == file_id)
        )
        sf = result.scalar_one()
        assert sf.is_modified is False
        assert sf.original_file_path is None
        assert sf.file_size == len(original_content)
