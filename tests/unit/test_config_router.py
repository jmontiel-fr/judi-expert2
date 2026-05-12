"""Tests unitaires pour le router de configuration."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Backend sur le path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend"))

from models import Base, LocalConfig
from database import get_db
from main import app
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
async def client(session_factory):
    """AsyncClient with in-memory DB and mocked auth."""

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    async def _override_auth():
        return {"sub": "local_admin", "domaine": "psychologie"}

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_auth
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _setup_config(client: AsyncClient, is_configured: bool = True, rag_version: str = "1.0.0"):
    """Helper: create initial config via login endpoint, then optionally update rag fields."""
    from unittest.mock import MagicMock as _MagicMock

    mock_resp = _MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "fake-access",
        "id_token": "fake-id",
        "refresh_token": "fake-refresh",
    }

    # Temporarily restore real auth for login
    original_auth = app.dependency_overrides.get(get_current_user)
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]

    with patch("routers.auth.SiteCentralClient.post", new_callable=AsyncMock, return_value=mock_resp):
        resp = await client.post("/api/auth/login", json={
            "email": "user@test.com",
            "password": "secret123",
        })
    assert resp.status_code == 200

    # Restore mocked auth
    if original_auth is not None:
        app.dependency_overrides[get_current_user] = original_auth

    # Update rag_version and is_configured directly via the install endpoint
    if is_configured and rag_version:
        app.dependency_overrides[get_current_user] = original_auth
        with _mock_site_central_get():
            resp = await client.post("/api/config/rag-install", json={"version": rag_version})
        assert resp.status_code == 200


def _mock_site_central_get():
    """Mock SiteCentralClient.get to return an empty versions list."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []
    return patch(
        "routers.config.SiteCentralClient.get",
        new_callable=AsyncMock,
        return_value=mock_resp,
    )


# ---------------------------------------------------------------------------
# GET /api/config/domain
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_domain(client: AsyncClient):
    await _setup_config(client)
    resp = await client.get("/api/config/domain")
    assert resp.status_code == 200
    assert resp.json()["domaine"] == "psychologie"


@pytest.mark.asyncio
async def test_get_domain_no_config(client: AsyncClient):
    resp = await client.get("/api/config/domain")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/config/domain
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_domain(client: AsyncClient):
    await _setup_config(client)
    resp = await client.put("/api/config/domain", json={"domaine": "batiment"})
    assert resp.status_code == 200
    assert resp.json()["domaine"] == "batiment"


@pytest.mark.asyncio
async def test_update_domain_empty(client: AsyncClient):
    await _setup_config(client)
    resp = await client.put("/api/config/domain", json={"domaine": ""})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/config/rag-versions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_rag_versions(client: AsyncClient):
    await _setup_config(client)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {"version": "1.0.0", "description": "Corpus initial psychologie"},
        {"version": "1.1.0", "description": "Corpus enrichi psychologie"},
    ]
    with patch("routers.config.SiteCentralClient.get", new_callable=AsyncMock, return_value=mock_resp):
        resp = await client.get("/api/config/rag-versions")
    assert resp.status_code == 200
    data = resp.json()
    assert "versions" in data
    assert len(data["versions"]) == 2
    for v in data["versions"]:
        assert "version" in v
        assert "description" in v
        assert v["domaine"] == "psychologie"


# ---------------------------------------------------------------------------
# POST /api/config/rag-install
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rag_install(client: AsyncClient):
    await _setup_config(client, is_configured=False, rag_version=None)
    with _mock_site_central_get():
        resp = await client.post("/api/config/rag-install", json={"version": "1.0.0"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "1.0.0"
    assert "succès" in data["message"].lower() or "succes" in data["message"].lower()


@pytest.mark.asyncio
async def test_rag_install_empty_version(client: AsyncClient):
    await _setup_config(client)
    resp = await client.post("/api/config/rag-install", json={"version": ""})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/config/tpe — RAG not configured → 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tpe_upload_rag_not_configured(client: AsyncClient):
    """Uploading TPE when RAG is not configured should still succeed (saves locally)."""
    # Setup without installing RAG — login creates config with rag_version=None
    original_auth = app.dependency_overrides.get(get_current_user)
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "fake-access",
        "id_token": "fake-id",
        "refresh_token": "fake-refresh",
    }
    with patch("routers.auth.SiteCentralClient.post", new_callable=AsyncMock, return_value=mock_resp):
        await client.post("/api/auth/login", json={"email": "user@test.com", "password": "secret123"})

    if original_auth is not None:
        app.dependency_overrides[get_current_user] = original_auth

    # TPE upload with valid .md extension — should succeed even without RAG
    with patch("routers.config.CONFIG_DIR", str(Path(__file__).parent / "tmp_config")):
        import os
        os.makedirs(str(Path(__file__).parent / "tmp_config"), exist_ok=True)
        resp = await client.post(
            "/api/config/tpe",
            files={"file": ("TPE_test.md", b"contenu test", "text/markdown")},
        )
    # Should succeed — TPE upload doesn't require RAG
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/config/tpe — with RAG configured (mock RAGService)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tpe_upload_success(client: AsyncClient, tmp_path):
    await _setup_config(client)

    mock_rag = MagicMock()
    mock_rag.index_document = AsyncMock(return_value="abc123")
    mock_rag.close = AsyncMock()

    with patch("routers.config.RAGService", return_value=mock_rag), \
         patch("routers.config.CONFIG_DIR", str(tmp_path)):
        resp = await client.post(
            "/api/config/tpe",
            files={"file": ("TPE_psychologie.md", b"contenu du TPE", "text/markdown")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "TPE_psychologie.md"


# ---------------------------------------------------------------------------
# POST /api/config/template — with RAG configured (mock RAGService)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_template_upload_success(client: AsyncClient, tmp_path):
    await _setup_config(client)

    mock_rag = MagicMock()
    mock_rag.index_document = AsyncMock(return_value="def456")
    mock_rag.close = AsyncMock()

    with patch("routers.config.RAGService", return_value=mock_rag), \
         patch("routers.config.CONFIG_DIR", str(tmp_path)):
        resp = await client.post(
            "/api/config/template",
            files={"file": ("template_rapport.docx", b"contenu template", "application/octet-stream")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "template_psychologie.docx"


@pytest.mark.asyncio
async def test_template_upload_rag_not_configured(client: AsyncClient):
    """Uploading template when RAG is not configured should still succeed (saves locally)."""
    original_auth = app.dependency_overrides.get(get_current_user)
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "fake-access",
        "id_token": "fake-id",
        "refresh_token": "fake-refresh",
    }
    with patch("routers.auth.SiteCentralClient.post", new_callable=AsyncMock, return_value=mock_resp):
        await client.post("/api/auth/login", json={"email": "user@test.com", "password": "secret123"})

    if original_auth is not None:
        app.dependency_overrides[get_current_user] = original_auth

    with patch("routers.config.CONFIG_DIR", str(Path(__file__).parent / "tmp_config")):
        import os
        os.makedirs(str(Path(__file__).parent / "tmp_config"), exist_ok=True)
        resp = await client.post(
            "/api/config/template",
            files={"file": ("template_rapport.docx", b"contenu", "application/octet-stream")},
        )
    # Template upload doesn't require RAG — should succeed
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/config/documents
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_documents_success(client: AsyncClient):
    await _setup_config(client)

    from services.rag_service import DocumentInfo
    mock_docs = [
        DocumentInfo(doc_id="a1", filename="TPE.tpl", doc_type="document", chunk_count=3),
        DocumentInfo(doc_id="b2", filename="corpus.pdf", doc_type="document", chunk_count=10),
    ]
    mock_rag = MagicMock()
    mock_rag.list_documents = AsyncMock(return_value=mock_docs)
    mock_rag.close = AsyncMock()

    with patch("routers.config.RAGService", return_value=mock_rag):
        resp = await client.get("/api/config/documents")
    assert resp.status_code == 200
    data = resp.json()
    assert "documents" in data
    # Called for both config_ and corpus_ collections
    assert mock_rag.list_documents.call_count == 2


@pytest.mark.asyncio
async def test_list_documents_rag_not_configured(client: AsyncClient):
    """Listing documents when RAG is not configured should return empty list."""
    original_auth = app.dependency_overrides.get(get_current_user)
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "fake-access",
        "id_token": "fake-id",
        "refresh_token": "fake-refresh",
    }
    with patch("routers.auth.SiteCentralClient.post", new_callable=AsyncMock, return_value=mock_resp):
        await client.post("/api/auth/login", json={"email": "user@test.com", "password": "secret123"})

    if original_auth is not None:
        app.dependency_overrides[get_current_user] = original_auth

    resp = await client.get("/api/config/documents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["documents"] == []
