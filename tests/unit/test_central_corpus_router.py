"""Tests unitaires pour les routers corpus et downloads du Site Central."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Module isolation: load Site Central backend without polluting sys.modules
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

from models import Base as _Base  # noqa: E402
from models.corpus_version import CorpusVersion as _CorpusVersion  # noqa: E402
from models.domaine import Domaine as _Domaine  # noqa: E402
from database import get_db as _get_db  # noqa: E402
from main import app as _app  # noqa: E402

import routers.corpus as _corpus_mod  # noqa: E402
import services.domaines_service as _domaines_svc_mod  # noqa: E402

# Cache central modules, then restore originals
_central_cache = {}
for prefix in _modules_to_isolate:
    for k in list(sys.modules):
        if k == prefix or k.startswith(prefix + "."):
            _central_cache[k] = sys.modules.pop(k)

sys.modules.update(_saved_modules)
sys.path[:] = _saved_path


# ---------------------------------------------------------------------------
# Fake domaines.yaml data
# ---------------------------------------------------------------------------
_FAKE_DOMAINES = [
    {"nom": "psychologie", "repertoire": "corpus/psychologie", "actif": True},
    {"nom": "psychiatrie", "repertoire": "corpus/psychiatrie", "actif": False},
    {"nom": "batiment", "repertoire": "corpus/batiment", "actif": False},
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def seeded_session_factory(engine, session_factory):
    """Session factory with a domain + corpus version seeded in DB."""
    async with session_factory() as session:
        domaine = _Domaine(
            nom="psychologie", repertoire="corpus/psychologie", actif=True
        )
        session.add(domaine)
        await session.flush()

        version = _CorpusVersion(
            domaine_id=domaine.id,
            version="1.0.0",
            description="Corpus psychologie initial",
            ecr_image_uri="123456.dkr.ecr.eu-west-3.amazonaws.com/judi-rag-psychologie:1.0.0",
            published_at=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        )
        session.add(version)
        await session.commit()
    return session_factory


@pytest_asyncio.fixture
async def client(session_factory):
    """AsyncClient wired to the FastAPI app with an in-memory DB (empty)."""

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    _app.dependency_overrides[_get_db] = _override_get_db
    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_client(seeded_session_factory):
    """AsyncClient with seeded domain + corpus version data."""

    async def _override_get_db():
        async with seeded_session_factory() as session:
            yield session

    _app.dependency_overrides[_get_db] = _override_get_db
    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /api/corpus — Liste tous les domaines depuis domaines.yaml
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_corpus_returns_all_domains(client: AsyncClient):
    """GET /api/corpus retourne tous les domaines du fichier domaines.yaml."""
    with patch.object(_domaines_svc_mod, "load_domaines", return_value=_FAKE_DOMAINES):
        with patch.object(_corpus_mod, "load_domaines", return_value=_FAKE_DOMAINES):
            resp = await client.get("/api/corpus")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    noms = [d["nom"] for d in data]
    assert "psychologie" in noms
    assert "psychiatrie" in noms
    assert "batiment" in noms


@pytest.mark.asyncio
async def test_list_corpus_includes_versions_from_db(seeded_client: AsyncClient):
    """GET /api/corpus enrichit les domaines avec les versions depuis la DB."""
    with patch.object(_domaines_svc_mod, "load_domaines", return_value=_FAKE_DOMAINES):
        with patch.object(_corpus_mod, "load_domaines", return_value=_FAKE_DOMAINES):
            resp = await seeded_client.get("/api/corpus")

    assert resp.status_code == 200
    data = resp.json()
    psycho = next(d for d in data if d["nom"] == "psychologie")
    assert len(psycho["versions"]) == 1
    assert psycho["versions"][0]["version"] == "1.0.0"
    assert psycho["actif"] is True

    # Domaines sans versions en DB
    psychiatrie = next(d for d in data if d["nom"] == "psychiatrie")
    assert len(psychiatrie["versions"]) == 0


# ---------------------------------------------------------------------------
# GET /api/corpus/{domaine}/versions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_versions_for_domain(seeded_client: AsyncClient):
    """GET /api/corpus/psychologie/versions retourne les versions du domaine."""
    with patch.object(_domaines_svc_mod, "load_domaines", return_value=_FAKE_DOMAINES):
        with patch.object(_corpus_mod, "load_domaines", return_value=_FAKE_DOMAINES):
            resp = await seeded_client.get("/api/corpus/psychologie/versions")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["version"] == "1.0.0"
    assert data[0]["description"] == "Corpus psychologie initial"
    assert "ecr_image_uri" in data[0]
    assert "published_at" in data[0]


@pytest.mark.asyncio
async def test_list_versions_unknown_domain_returns_404(client: AsyncClient):
    """GET /api/corpus/inconnu/versions retourne 404 pour un domaine inconnu."""
    with patch.object(_domaines_svc_mod, "load_domaines", return_value=_FAKE_DOMAINES):
        with patch.object(_corpus_mod, "load_domaines", return_value=_FAKE_DOMAINES):
            resp = await client.get("/api/corpus/inconnu/versions")

    assert resp.status_code == 404
    assert "introuvable" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_list_versions_domain_not_in_db_returns_empty(client: AsyncClient):
    """GET /api/corpus/batiment/versions retourne une liste vide si pas en DB."""
    with patch.object(_domaines_svc_mod, "load_domaines", return_value=_FAKE_DOMAINES):
        with patch.object(_corpus_mod, "load_domaines", return_value=_FAKE_DOMAINES):
            resp = await client.get("/api/corpus/batiment/versions")

    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /api/downloads/app
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_download_app_returns_info(client: AsyncClient):
    """GET /api/downloads/app retourne les informations de téléchargement."""
    with patch.object(_domaines_svc_mod, "load_domaines", return_value=_FAKE_DOMAINES):
        resp = await client.get("/api/downloads/app")

    assert resp.status_code == 200
    data = resp.json()
    assert "download_url" in data
    assert "version" in data
    assert "description" in data
    assert data["version"] == "0.1.0"
