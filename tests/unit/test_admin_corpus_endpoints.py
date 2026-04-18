"""Tests unitaires pour les endpoints admin de gestion du corpus.

Teste les endpoints POST /api/admin/corpus/{domaine}/documents et
POST /api/admin/corpus/{domaine}/urls ajoutés dans routers/admin_corpus.py.

Exigences validées : 5.3, 5.4, 5.5, 6.3, 7.3, 8.1, 8.2
"""

import sys
import tempfile
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
from models.expert import Expert as _Expert  # noqa: E402
from database import get_db as _get_db  # noqa: E402
from main import app as _app  # noqa: E402

import routers.admin as _admin_mod  # noqa: E402
import routers.admin_corpus as _admin_corpus_mod  # noqa: E402
import routers.profile as _profile_mod  # noqa: E402
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
# Admin email (matches default in routers/admin.py)
# ---------------------------------------------------------------------------
_ADMIN_EMAIL = "admin@judi-expert.fr"


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
                _admin_corpus_mod, "load_domaines", return_value=data
            )
            self._p1.__enter__()
            self._p2.__enter__()
            return self

        def __exit__(self, *args):
            self._p2.__exit__(*args)
            self._p1.__exit__(*args)

    return _Ctx()


# ---------------------------------------------------------------------------
# Helper: build a mock admin Expert
# ---------------------------------------------------------------------------


def _make_admin_expert() -> _Expert:
    """Return an Expert instance with admin email."""
    expert = _Expert(
        id=1,
        cognito_sub="admin-sub-001",
        email=_ADMIN_EMAIL,
        nom="Admin",
        prenom="Super",
        adresse="1 rue Admin",
        ville="Paris",
        code_postal="75001",
        telephone="0100000000",
        domaine="psychologie",
        accept_newsletter=False,
        is_deleted=False,
    )
    return expert


def _make_non_admin_expert() -> _Expert:
    """Return an Expert instance that is NOT admin."""
    expert = _Expert(
        id=2,
        cognito_sub="user-sub-002",
        email="user@example.com",
        nom="Dupont",
        prenom="Jean",
        adresse="2 rue Utilisateur",
        ville="Lyon",
        code_postal="69001",
        telephone="0200000000",
        domaine="psychologie",
        accept_newsletter=False,
        is_deleted=False,
    )
    return expert


# ---------------------------------------------------------------------------
# POST /api/admin/corpus/{domaine}/documents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_document_requires_auth(client: AsyncClient):
    """POST /api/admin/corpus/psychologie/documents sans auth retourne 401/422.

    FastAPI retourne 422 quand le header Authorization requis est absent
    (validation du Header(...) avant même l'exécution de get_current_expert).
    """
    with _patch_domaines():
        resp = await client.post(
            "/api/admin/corpus/psychologie/documents",
            files={"file": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )

    # 422: FastAPI rejects the request because the required Authorization header is missing
    assert resp.status_code in (401, 422)


@pytest.mark.asyncio
async def test_upload_document_non_admin_returns_403(client: AsyncClient):
    """POST /api/admin/corpus/psychologie/documents par un non-admin retourne 403."""
    non_admin = _make_non_admin_expert()

    async def _override_get_current_expert():
        return (non_admin, "fake-token")

    _app.dependency_overrides[_profile_mod.get_current_expert] = (
        _override_get_current_expert
    )
    try:
        with _patch_domaines():
            resp = await client.post(
                "/api/admin/corpus/psychologie/documents",
                files={"file": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")},
            )
    finally:
        _app.dependency_overrides.pop(_profile_mod.get_current_expert, None)

    assert resp.status_code == 403
    assert "administrateur" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_document_unknown_domain_returns_404(client: AsyncClient):
    """POST /api/admin/corpus/inconnu/documents retourne 404."""
    admin = _make_admin_expert()

    async def _override_admin():
        return admin

    _app.dependency_overrides[_admin_mod.get_admin_expert] = _override_admin
    try:
        with _patch_domaines():
            resp = await client.post(
                "/api/admin/corpus/inconnu/documents",
                files={"file": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")},
            )
    finally:
        _app.dependency_overrides.pop(_admin_mod.get_admin_expert, None)

    assert resp.status_code == 404
    assert "introuvable" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_document_non_pdf_returns_400(client: AsyncClient):
    """POST /api/admin/corpus/psychologie/documents avec un non-PDF retourne 400."""
    admin = _make_admin_expert()

    async def _override_admin():
        return admin

    _app.dependency_overrides[_admin_mod.get_admin_expert] = _override_admin
    try:
        with _patch_domaines():
            resp = await client.post(
                "/api/admin/corpus/psychologie/documents",
                files={"file": ("notes.txt", b"text content", "text/plain")},
            )
    finally:
        _app.dependency_overrides.pop(_admin_mod.get_admin_expert, None)

    assert resp.status_code == 400
    assert "pdf" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_document_duplicate_returns_409(client: AsyncClient):
    """POST /api/admin/corpus/psychologie/documents doublon retourne 409."""
    admin = _make_admin_expert()

    async def _override_admin():
        return admin

    _app.dependency_overrides[_admin_mod.get_admin_expert] = _override_admin
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_base = Path(tmp_dir)
            # Pre-create the document so it's a duplicate
            docs_dir = corpus_base / "psychologie" / "documents"
            docs_dir.mkdir(parents=True)
            (docs_dir / "existing.pdf").write_bytes(b"%PDF-1.4 old")

            with _patch_domaines():
                with patch.object(
                    _admin_corpus_mod, "_CORPUS_BASE_PATH", corpus_base
                ):
                    resp = await client.post(
                        "/api/admin/corpus/psychologie/documents",
                        files={
                            "file": (
                                "existing.pdf",
                                b"%PDF-1.4 new",
                                "application/pdf",
                            )
                        },
                    )
    finally:
        _app.dependency_overrides.pop(_admin_mod.get_admin_expert, None)

    assert resp.status_code == 409
    assert "existe déjà" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_document_success(client: AsyncClient):
    """POST /api/admin/corpus/psychologie/documents succès retourne 201."""
    admin = _make_admin_expert()

    async def _override_admin():
        return admin

    _app.dependency_overrides[_admin_mod.get_admin_expert] = _override_admin
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_base = Path(tmp_dir)

            with _patch_domaines():
                with patch.object(
                    _admin_corpus_mod, "_CORPUS_BASE_PATH", corpus_base
                ):
                    resp = await client.post(
                        "/api/admin/corpus/psychologie/documents",
                        files={
                            "file": (
                                "rapport.pdf",
                                b"%PDF-1.4 content",
                                "application/pdf",
                            )
                        },
                    )
    finally:
        _app.dependency_overrides.pop(_admin_mod.get_admin_expert, None)

    assert resp.status_code == 201
    data = resp.json()
    assert data["nom"] == "documents/rapport.pdf"
    assert data["type"] == "document"
    assert "date_ajout" in data


# ---------------------------------------------------------------------------
# POST /api/admin/corpus/{domaine}/urls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_url_requires_auth(client: AsyncClient):
    """POST /api/admin/corpus/psychologie/urls sans auth retourne 401/422.

    FastAPI retourne 422 quand le header Authorization requis est absent
    (validation du Header(...) avant même l'exécution de get_current_expert).
    """
    with _patch_domaines():
        resp = await client.post(
            "/api/admin/corpus/psychologie/urls",
            json={
                "nom": "Test",
                "url": "https://example.com",
                "description": "desc",
                "type": "site_web",
            },
        )

    # 422: FastAPI rejects the request because the required Authorization header is missing
    assert resp.status_code in (401, 422)


@pytest.mark.asyncio
async def test_add_url_non_admin_returns_403(client: AsyncClient):
    """POST /api/admin/corpus/psychologie/urls par un non-admin retourne 403."""
    non_admin = _make_non_admin_expert()

    async def _override_get_current_expert():
        return (non_admin, "fake-token")

    _app.dependency_overrides[_profile_mod.get_current_expert] = (
        _override_get_current_expert
    )
    try:
        with _patch_domaines():
            resp = await client.post(
                "/api/admin/corpus/psychologie/urls",
                json={
                    "nom": "Test",
                    "url": "https://example.com",
                    "description": "desc",
                    "type": "site_web",
                },
            )
    finally:
        _app.dependency_overrides.pop(_profile_mod.get_current_expert, None)

    assert resp.status_code == 403
    assert "administrateur" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_add_url_unknown_domain_returns_404(client: AsyncClient):
    """POST /api/admin/corpus/inconnu/urls retourne 404."""
    admin = _make_admin_expert()

    async def _override_admin():
        return admin

    _app.dependency_overrides[_admin_mod.get_admin_expert] = _override_admin
    try:
        with _patch_domaines():
            resp = await client.post(
                "/api/admin/corpus/inconnu/urls",
                json={
                    "nom": "Test",
                    "url": "https://example.com",
                    "description": "desc",
                    "type": "site_web",
                },
            )
    finally:
        _app.dependency_overrides.pop(_admin_mod.get_admin_expert, None)

    assert resp.status_code == 404
    assert "introuvable" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_add_url_success(client: AsyncClient):
    """POST /api/admin/corpus/psychologie/urls succès retourne 201."""
    admin = _make_admin_expert()

    async def _override_admin():
        return admin

    _app.dependency_overrides[_admin_mod.get_admin_expert] = _override_admin
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_base = Path(tmp_dir)

            with _patch_domaines():
                with patch.object(
                    _admin_corpus_mod, "_CORPUS_BASE_PATH", corpus_base
                ):
                    resp = await client.post(
                        "/api/admin/corpus/psychologie/urls",
                        json={
                            "nom": "Legifrance",
                            "url": "https://www.legifrance.gouv.fr",
                            "description": "Portail juridique",
                            "type": "site_web",
                        },
                    )
    finally:
        _app.dependency_overrides.pop(_admin_mod.get_admin_expert, None)

    assert resp.status_code == 201
    data = resp.json()
    assert data["nom"] == "Legifrance"
    assert data["url"] == "https://www.legifrance.gouv.fr"
    assert data["type"] == "site_web"
    assert "date_ajout" in data
