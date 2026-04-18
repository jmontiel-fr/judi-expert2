"""Tests unitaires pour les endpoints publics de contenu corpus.

Teste les endpoints GET /api/corpus/{domaine}/contenu et
GET /api/corpus/{domaine}/urls ajoutés dans routers/corpus.py.

Exigences validées : 1.1, 1.2, 1.3, 1.4
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
import yaml
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
async def client(session_factory):
    """AsyncClient wired to the FastAPI app with an in-memory DB."""

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    _app.dependency_overrides[_get_db] = _override_get_db
    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper: patch load_domaines at both module levels
# ---------------------------------------------------------------------------


def _patch_domaines(domaines=None):
    """Context manager that patches load_domaines in both modules."""
    data = domaines if domaines is not None else _FAKE_DOMAINES

    class _Ctx:
        def __enter__(self):
            self._p1 = patch.object(
                _domaines_svc_mod, "load_domaines", return_value=data
            )
            self._p2 = patch.object(
                _corpus_mod, "load_domaines", return_value=data
            )
            self._p1.__enter__()
            self._p2.__enter__()
            return self

        def __exit__(self, *args):
            self._p2.__exit__(*args)
            self._p1.__exit__(*args)

    return _Ctx()


# ---------------------------------------------------------------------------
# GET /api/corpus/{domaine}/contenu
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_contenu_unknown_domain_returns_404(client: AsyncClient):
    """GET /api/corpus/inconnu/contenu retourne 404 pour un domaine inexistant."""
    with _patch_domaines():
        resp = await client.get("/api/corpus/inconnu/contenu")

    assert resp.status_code == 404
    assert "introuvable" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_contenu_missing_file_returns_empty_list(client: AsyncClient):
    """GET /api/corpus/psychologie/contenu retourne [] si contenu.yaml absent."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        with _patch_domaines():
            with patch.object(
                _corpus_mod, "_CORPUS_BASE_PATH", Path(tmp_dir)
            ):
                resp = await client.get("/api/corpus/psychologie/contenu")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_contenu_returns_items(client: AsyncClient):
    """GET /api/corpus/psychologie/contenu retourne les éléments du YAML."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        corpus_base = Path(tmp_dir)
        domaine_dir = corpus_base / "psychologie"
        domaine_dir.mkdir(parents=True)

        contenu_data = {
            "contenu": [
                {
                    "nom": "documents/rapport.pdf",
                    "description": "Rapport initial",
                    "type": "document",
                    "date_ajout": "2025-01-15",
                },
                {
                    "nom": "documents/guide.pdf",
                    "description": "Guide pratique",
                    "type": "template",
                    "date_ajout": "2025-02-01",
                },
            ]
        }
        with open(domaine_dir / "contenu.yaml", "w", encoding="utf-8") as f:
            yaml.dump(contenu_data, f, allow_unicode=True)

        with _patch_domaines():
            with patch.object(_corpus_mod, "_CORPUS_BASE_PATH", corpus_base):
                resp = await client.get("/api/corpus/psychologie/contenu")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["nom"] == "documents/rapport.pdf"
    assert data[0]["description"] == "Rapport initial"
    assert data[0]["type"] == "document"
    assert data[0]["date_ajout"] == "2025-01-15"
    assert data[1]["nom"] == "documents/guide.pdf"


# ---------------------------------------------------------------------------
# GET /api/corpus/{domaine}/urls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_urls_unknown_domain_returns_404(client: AsyncClient):
    """GET /api/corpus/inconnu/urls retourne 404 pour un domaine inexistant."""
    with _patch_domaines():
        resp = await client.get("/api/corpus/inconnu/urls")

    assert resp.status_code == 404
    assert "introuvable" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_urls_missing_file_returns_empty_list(client: AsyncClient):
    """GET /api/corpus/psychologie/urls retourne [] si urls.yaml absent."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        with _patch_domaines():
            with patch.object(
                _corpus_mod, "_CORPUS_BASE_PATH", Path(tmp_dir)
            ):
                resp = await client.get("/api/corpus/psychologie/urls")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_urls_returns_items(client: AsyncClient):
    """GET /api/corpus/psychologie/urls retourne les URLs du YAML."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        corpus_base = Path(tmp_dir)
        urls_dir = corpus_base / "psychologie" / "urls"
        urls_dir.mkdir(parents=True)

        urls_data = {
            "urls": [
                {
                    "nom": "Legifrance",
                    "url": "https://www.legifrance.gouv.fr",
                    "description": "Portail juridique officiel",
                    "type": "institutionnel",
                    "date_ajout": "2025-01-10",
                },
                {
                    "nom": "PubMed",
                    "url": "https://pubmed.ncbi.nlm.nih.gov",
                    "description": "Base de données médicale",
                    "type": "academique",
                    "date_ajout": "2025-03-20",
                },
            ]
        }
        with open(urls_dir / "urls.yaml", "w", encoding="utf-8") as f:
            yaml.dump(urls_data, f, allow_unicode=True)

        with _patch_domaines():
            with patch.object(_corpus_mod, "_CORPUS_BASE_PATH", corpus_base):
                resp = await client.get("/api/corpus/psychologie/urls")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["nom"] == "Legifrance"
    assert data[0]["url"] == "https://www.legifrance.gouv.fr"
    assert data[0]["description"] == "Portail juridique officiel"
    assert data[0]["type"] == "institutionnel"
    assert data[0]["date_ajout"] == "2025-01-10"
    assert data[1]["nom"] == "PubMed"
