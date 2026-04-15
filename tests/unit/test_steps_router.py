"""Tests unitaires pour le router des étapes (Step0, Step1, Step2, Step3)."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Backend sur le path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "local-site" / "web" / "backend"))

from models import Base
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
async def client(session_factory, tmp_path):
    """AsyncClient with in-memory DB, mocked auth, and temp DATA_DIR."""

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    async def _override_auth():
        return {"sub": "local_admin", "domaine": "psychologie"}

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_auth

    # Use tmp_path as DATA_DIR so tests don't write to real filesystem
    with patch("routers.steps.DATA_DIR", str(tmp_path)):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


async def _setup_config(client: AsyncClient):
    """Helper: create initial config via setup endpoint."""
    original_auth = app.dependency_overrides.get(get_current_user)
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]

    resp = await client.post("/api/auth/setup", json={
        "password": "secret123",
        "domaine": "psychologie",
    })
    assert resp.status_code == 201

    if original_auth is not None:
        app.dependency_overrides[get_current_user] = original_auth

    resp = await client.post("/api/config/rag-install", json={"version": "1.0.0"})
    assert resp.status_code == 200


def _mock_verify_ticket_success():
    return patch(
        "routers.dossiers._verify_ticket",
        new_callable=AsyncMock,
        return_value={"valid": True, "message": "Ticket valide"},
    )


async def _create_dossier(client: AsyncClient, ticket_id: str = "T-STEP0") -> int:
    """Helper: create a dossier and return its id."""
    with _mock_verify_ticket_success():
        resp = await client.post(
            "/api/dossiers",
            json={"nom": "Dossier Step0", "ticket_id": ticket_id},
        )
    assert resp.status_code == 201
    return resp.json()["id"]


def _mock_ocr_success(text: str = "Texte brut extrait par OCR"):
    """Mock httpx call to OCR service returning success."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"text": text, "pages": 1, "confidence": 0.95}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    return patch("routers.steps.httpx.AsyncClient", return_value=mock_client)


def _mock_llm_success(markdown: str = "# Réquisition\n\n## Questions du Tribunal\n\n1. Question 1"):
    """Mock LLM structurer_markdown."""
    return patch(
        "routers.steps.LLMService.structurer_markdown",
        new_callable=AsyncMock,
        return_value=markdown,
    )


# ---------------------------------------------------------------------------
# POST /api/dossiers/{id}/step0/extract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step0_extract_success(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client)

    with _mock_ocr_success(), _mock_llm_success():
        resp = await client.post(
            f"/api/dossiers/{dossier_id}/step0/extract",
            files={"file": ("requisition.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert "markdown" in data
    assert "# Réquisition" in data["markdown"]
    assert data["pdf_path"].endswith("requisition.pdf")
    assert data["md_path"].endswith("requisition.md")


@pytest.mark.asyncio
async def test_step0_extract_non_pdf_rejected(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client)

    resp = await client.post(
        f"/api/dossiers/{dossier_id}/step0/extract",
        files={"file": ("document.txt", b"some text", "text/plain")},
    )
    assert resp.status_code == 400
    assert "PDF" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_step0_extract_empty_pdf_rejected(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client)

    resp = await client.post(
        f"/api/dossiers/{dossier_id}/step0/extract",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert resp.status_code == 400
    assert "vide" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_step0_extract_ocr_unavailable(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client)

    import httpx as httpx_mod
    with patch(
        "routers.steps.httpx.AsyncClient",
        side_effect=lambda **kwargs: _raise_connect_error(),
    ):
        # Use a simpler approach: mock the entire httpx call chain
        pass

    # Mock OCR connect error
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx_mod.ConnectError("Connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("routers.steps.httpx.AsyncClient", return_value=mock_client):
        resp = await client.post(
            f"/api/dossiers/{dossier_id}/step0/extract",
            files={"file": ("req.pdf", b"%PDF-1.4 content", "application/pdf")},
        )

    assert resp.status_code == 503
    assert "OCR" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_step0_extract_creates_step_files(client: AsyncClient):
    """After extraction, step0 should have 2 files and statut 'réalisé'."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client)

    with _mock_ocr_success(), _mock_llm_success():
        resp = await client.post(
            f"/api/dossiers/{dossier_id}/step0/extract",
            files={"file": ("requisition.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
    assert resp.status_code == 201

    # Check step detail
    step_resp = await client.get(f"/api/dossiers/{dossier_id}/steps/0")
    assert step_resp.status_code == 200
    step_data = step_resp.json()
    assert step_data["statut"] == "réalisé"
    assert len(step_data["files"]) == 2
    filenames = {f["filename"] for f in step_data["files"]}
    assert filenames == {"requisition.pdf", "requisition.md"}


# ---------------------------------------------------------------------------
# GET /api/dossiers/{id}/step0/markdown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step0_get_markdown_success(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client)

    expected_md = "# Test Markdown\n\nContenu structuré"
    with _mock_ocr_success(), _mock_llm_success(expected_md):
        await client.post(
            f"/api/dossiers/{dossier_id}/step0/extract",
            files={"file": ("req.pdf", b"%PDF-1.4 data", "application/pdf")},
        )

    resp = await client.get(f"/api/dossiers/{dossier_id}/step0/markdown")
    assert resp.status_code == 200
    assert resp.json()["markdown"] == expected_md


@pytest.mark.asyncio
async def test_step0_get_markdown_not_extracted(client: AsyncClient):
    """Should return 404 if extraction hasn't been done yet."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client)

    resp = await client.get(f"/api/dossiers/{dossier_id}/step0/markdown")
    assert resp.status_code == 404
    assert "extraction" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# PUT /api/dossiers/{id}/step0/markdown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step0_update_markdown_success(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client)

    with _mock_ocr_success(), _mock_llm_success():
        await client.post(
            f"/api/dossiers/{dossier_id}/step0/extract",
            files={"file": ("req.pdf", b"%PDF-1.4 data", "application/pdf")},
        )

    new_content = "# Modifié\n\nContenu mis à jour par l'expert"
    resp = await client.put(
        f"/api/dossiers/{dossier_id}/step0/markdown",
        json={"content": new_content},
    )
    assert resp.status_code == 200
    assert "mis à jour" in resp.json()["message"].lower()

    # Verify the content was actually updated
    get_resp = await client.get(f"/api/dossiers/{dossier_id}/step0/markdown")
    assert get_resp.json()["markdown"] == new_content


@pytest.mark.asyncio
async def test_step0_update_markdown_not_extracted(client: AsyncClient):
    """Should return 404 if extraction hasn't been done yet."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client)

    resp = await client.put(
        f"/api/dossiers/{dossier_id}/step0/markdown",
        json={"content": "test"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Step1 helpers
# ---------------------------------------------------------------------------


async def _execute_and_validate_step0(client: AsyncClient, dossier_id: int):
    """Helper: execute step0 and validate it so step1 becomes accessible."""
    with _mock_ocr_success(), _mock_llm_success():
        resp = await client.post(
            f"/api/dossiers/{dossier_id}/step0/extract",
            files={"file": ("requisition.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
    assert resp.status_code == 201

    # Validate step0 by directly calling the workflow engine through the DB
    # (no step0/validate route exists yet — use the step1/validate pattern)
    from services.workflow_engine import workflow_engine as _wf

    # Get a fresh DB session via the overridden dependency
    override_fn = app.dependency_overrides[get_db]
    async for db in override_fn():
        await _wf.validate_step(dossier_id, 0, db)
        await db.commit()


def _mock_rag_search(tpe_content: str = "Section 1: Identification\nSection 2: Anamnèse",
                     corpus_content: str = "Contexte domaine psychologie"):
    """Mock RAGService.search to return fake documents."""
    from services.rag_service import Document

    async def _fake_search(self, query, collection, limit=5):
        if "config_" in collection:
            return [Document(content=tpe_content, score=0.9)]
        return [Document(content=corpus_content, score=0.85)]

    return patch("routers.steps.RAGService.search", _fake_search)


def _mock_llm_qmec(qmec: str = "# QMEC\n\n## Section 1\n\n- Question 1\n- Question 2"):
    """Mock LLM generer_qmec."""
    return patch(
        "routers.steps.LLMService.generer_qmec",
        new_callable=AsyncMock,
        return_value=qmec,
    )


# ---------------------------------------------------------------------------
# POST /api/dossiers/{id}/step1/execute
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step1_execute_success(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP1-EXEC")
    await _execute_and_validate_step0(client, dossier_id)

    with _mock_rag_search(), _mock_llm_qmec():
        resp = await client.post(f"/api/dossiers/{dossier_id}/step1/execute")

    assert resp.status_code == 201
    data = resp.json()
    assert "qmec" in data
    assert "# QMEC" in data["qmec"]


@pytest.mark.asyncio
async def test_step1_execute_creates_step_file(client: AsyncClient):
    """After execution, step1 should have a qmec.md file and statut 'réalisé'."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP1-FILE")
    await _execute_and_validate_step0(client, dossier_id)

    with _mock_rag_search(), _mock_llm_qmec():
        resp = await client.post(f"/api/dossiers/{dossier_id}/step1/execute")
    assert resp.status_code == 201

    step_resp = await client.get(f"/api/dossiers/{dossier_id}/steps/1")
    assert step_resp.status_code == 200
    step_data = step_resp.json()
    assert step_data["statut"] == "réalisé"
    assert any(f["filename"] == "qmec.md" for f in step_data["files"])


@pytest.mark.asyncio
async def test_step1_execute_blocked_without_step0_validated(client: AsyncClient):
    """Step1 should be blocked if step0 is not validated."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP1-BLOCK")

    with _mock_rag_search(), _mock_llm_qmec():
        resp = await client.post(f"/api/dossiers/{dossier_id}/step1/execute")

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_step1_execute_llm_unavailable(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP1-LLM")
    await _execute_and_validate_step0(client, dossier_id)

    with _mock_rag_search(), patch(
        "routers.steps.LLMService.generer_qmec",
        new_callable=AsyncMock,
        side_effect=Exception("LLM timeout"),
    ):
        resp = await client.post(f"/api/dossiers/{dossier_id}/step1/execute")

    assert resp.status_code == 503
    assert "LLM" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET /api/dossiers/{id}/step1/download
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step1_download_success(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP1-DL")
    await _execute_and_validate_step0(client, dossier_id)

    expected_qmec = "# QMEC Download Test"
    with _mock_rag_search(), _mock_llm_qmec(expected_qmec):
        await client.post(f"/api/dossiers/{dossier_id}/step1/execute")

    resp = await client.get(f"/api/dossiers/{dossier_id}/step1/download")
    assert resp.status_code == 200
    assert expected_qmec in resp.text


@pytest.mark.asyncio
async def test_step1_download_not_executed(client: AsyncClient):
    """Should return 404 if step1 hasn't been executed yet."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP1-DL404")
    await _execute_and_validate_step0(client, dossier_id)

    resp = await client.get(f"/api/dossiers/{dossier_id}/step1/download")
    assert resp.status_code == 404
    assert "QMEC" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_step1_download_blocked_without_step0(client: AsyncClient):
    """Download should be blocked if step0 is not validated."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP1-DLBLK")

    resp = await client.get(f"/api/dossiers/{dossier_id}/step1/download")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/dossiers/{id}/step1/validate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step1_validate_success(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP1-VAL")
    await _execute_and_validate_step0(client, dossier_id)

    with _mock_rag_search(), _mock_llm_qmec():
        await client.post(f"/api/dossiers/{dossier_id}/step1/execute")

    resp = await client.post(f"/api/dossiers/{dossier_id}/step1/validate")
    assert resp.status_code == 200
    assert "validé" in resp.json()["message"].lower()

    # Verify step is now validated
    step_resp = await client.get(f"/api/dossiers/{dossier_id}/steps/1")
    assert step_resp.json()["statut"] == "validé"


@pytest.mark.asyncio
async def test_step1_validate_without_execute(client: AsyncClient):
    """Validation should fail if step1 hasn't been executed."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP1-VALNX")
    await _execute_and_validate_step0(client, dossier_id)

    resp = await client.post(f"/api/dossiers/{dossier_id}/step1/validate")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Step2 helpers
# ---------------------------------------------------------------------------


async def _execute_and_validate_step1(client: AsyncClient, dossier_id: int):
    """Helper: execute step0+step1 and validate both so step2 becomes accessible."""
    await _execute_and_validate_step0(client, dossier_id)

    with _mock_rag_search(), _mock_llm_qmec():
        resp = await client.post(f"/api/dossiers/{dossier_id}/step1/execute")
    assert resp.status_code == 201

    from services.workflow_engine import workflow_engine as _wf

    override_fn = app.dependency_overrides[get_db]
    async for db in override_fn():
        await _wf.validate_step(dossier_id, 1, db)
        await db.commit()


# ---------------------------------------------------------------------------
# POST /api/dossiers/{id}/step2/upload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step2_upload_success(client: AsyncClient):
    """Upload of NE + REB .docx files should succeed when step1 is validated."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP2-UP")
    await _execute_and_validate_step1(client, dossier_id)

    resp = await client.post(
        f"/api/dossiers/{dossier_id}/step2/upload",
        files={
            "ne": ("ne.docx", b"PK\x03\x04 fake docx ne", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            "reb": ("reb.docx", b"PK\x03\x04 fake docx reb", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["filenames"] == ["ne.docx", "reb.docx"]
    assert "succès" in data["message"].lower()


@pytest.mark.asyncio
async def test_step2_upload_rejects_non_docx(client: AsyncClient):
    """Non-.docx files should be rejected with 400."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP2-NODOCX")
    await _execute_and_validate_step1(client, dossier_id)

    resp = await client.post(
        f"/api/dossiers/{dossier_id}/step2/upload",
        files={
            "ne": ("ne.pdf", b"fake pdf content", "application/pdf"),
            "reb": ("reb.docx", b"PK\x03\x04 fake docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        },
    )
    assert resp.status_code == 400
    assert ".docx" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_step2_upload_blocked_without_step1_validated(client: AsyncClient):
    """Step2 upload should be blocked if step1 is not validated."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP2-BLOCK")

    resp = await client.post(
        f"/api/dossiers/{dossier_id}/step2/upload",
        files={
            "ne": ("ne.docx", b"PK\x03\x04 fake", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            "reb": ("reb.docx", b"PK\x03\x04 fake", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        },
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/dossiers/{id}/step2/validate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step2_validate_success(client: AsyncClient):
    """Validation should succeed after upload."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP2-VAL")
    await _execute_and_validate_step1(client, dossier_id)

    # Upload first
    await client.post(
        f"/api/dossiers/{dossier_id}/step2/upload",
        files={
            "ne": ("ne.docx", b"PK\x03\x04 fake ne", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            "reb": ("reb.docx", b"PK\x03\x04 fake reb", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        },
    )

    resp = await client.post(f"/api/dossiers/{dossier_id}/step2/validate")
    assert resp.status_code == 200
    assert "validé" in resp.json()["message"].lower()

    # Verify step is now validated
    step_resp = await client.get(f"/api/dossiers/{dossier_id}/steps/2")
    assert step_resp.json()["statut"] == "validé"


@pytest.mark.asyncio
async def test_step2_validate_without_upload(client: AsyncClient):
    """Validation should fail if step2 hasn't been executed (no upload)."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP2-VALNX")
    await _execute_and_validate_step1(client, dossier_id)

    resp = await client.post(f"/api/dossiers/{dossier_id}/step2/validate")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Step3 helpers
# ---------------------------------------------------------------------------


async def _execute_and_validate_step2(client: AsyncClient, dossier_id: int):
    """Helper: execute step0+step1+step2 and validate all so step3 becomes accessible."""
    await _execute_and_validate_step1(client, dossier_id)

    # Upload NE + REB for step2
    await client.post(
        f"/api/dossiers/{dossier_id}/step2/upload",
        files={
            "ne": ("ne.docx", b"PK\x03\x04 fake docx ne content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            "reb": ("reb.docx", b"PK\x03\x04 fake docx reb content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        },
    )

    from services.workflow_engine import workflow_engine as _wf

    override_fn = app.dependency_overrides[get_db]
    async for db in override_fn():
        await _wf.validate_step(dossier_id, 2, db)
        await db.commit()


def _mock_llm_ref(ref: str = "# Rapport d'Expertise Final\n\nContenu du REF généré"):
    """Mock LLM generer_ref."""
    return patch(
        "routers.steps.LLMService.generer_ref",
        new_callable=AsyncMock,
        return_value=ref,
    )


def _mock_llm_raux_p1(raux_p1: str = "## Contestations\n\n1. Point faible identifié"):
    """Mock LLM generer_raux_p1."""
    return patch(
        "routers.steps.LLMService.generer_raux_p1",
        new_callable=AsyncMock,
        return_value=raux_p1,
    )


def _mock_llm_raux_p2(raux_p2: str = "## REF Révisé\n\nContenu révisé du REF"):
    """Mock LLM generer_raux_p2."""
    return patch(
        "routers.steps.LLMService.generer_raux_p2",
        new_callable=AsyncMock,
        return_value=raux_p2,
    )


def _mock_rag_search_step3(template_content: str = "Template rapport structure",
                           corpus_content: str = "Corpus domaine psychologie"):
    """Mock RAGService.search for step3 (template + corpus)."""
    from services.rag_service import Document

    async def _fake_search(self, query, collection, limit=5):
        if "config_" in collection:
            return [Document(content=template_content, score=0.9)]
        return [Document(content=corpus_content, score=0.85)]

    return patch("routers.steps.RAGService.search", _fake_search)


# ---------------------------------------------------------------------------
# POST /api/dossiers/{id}/step3/execute
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step3_execute_success(client: AsyncClient):
    """Step3 execute should generate REF and RAUX when step2 is validated."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP3-EXEC")
    await _execute_and_validate_step2(client, dossier_id)

    with _mock_rag_search_step3(), _mock_llm_ref(), _mock_llm_raux_p1(), _mock_llm_raux_p2():
        resp = await client.post(f"/api/dossiers/{dossier_id}/step3/execute")

    assert resp.status_code == 201
    data = resp.json()
    assert "ref" in data
    assert "raux" in data
    assert "Rapport d'Expertise Final" in data["ref"]
    assert "Partie 1" in data["raux"]
    assert "Partie 2" in data["raux"]

    # Verify step is now "réalisé"
    step_resp = await client.get(f"/api/dossiers/{dossier_id}/steps/3")
    assert step_resp.status_code == 200
    step_data = step_resp.json()
    assert step_data["statut"] == "réalisé"
    filenames = {f["filename"] for f in step_data["files"]}
    assert "ref.md" in filenames
    assert "raux.md" in filenames


# ---------------------------------------------------------------------------
# GET /api/dossiers/{id}/step3/download/{doc_type}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step3_download_ref(client: AsyncClient):
    """Download REF after step3 execution."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP3-DLREF")
    await _execute_and_validate_step2(client, dossier_id)

    expected_ref = "# REF Download Test"
    with _mock_rag_search_step3(), _mock_llm_ref(expected_ref), _mock_llm_raux_p1(), _mock_llm_raux_p2():
        await client.post(f"/api/dossiers/{dossier_id}/step3/execute")

    resp = await client.get(f"/api/dossiers/{dossier_id}/step3/download/ref")
    assert resp.status_code == 200
    assert expected_ref in resp.text


@pytest.mark.asyncio
async def test_step3_download_raux(client: AsyncClient):
    """Download RAUX after step3 execution."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP3-DLRAUX")
    await _execute_and_validate_step2(client, dossier_id)

    with _mock_rag_search_step3(), _mock_llm_ref(), _mock_llm_raux_p1(), _mock_llm_raux_p2():
        await client.post(f"/api/dossiers/{dossier_id}/step3/execute")

    resp = await client.get(f"/api/dossiers/{dossier_id}/step3/download/raux")
    assert resp.status_code == 200
    assert "Partie 1" in resp.text


@pytest.mark.asyncio
async def test_step3_download_not_executed(client: AsyncClient):
    """Should return 404 if step3 hasn't been executed yet."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP3-DL404")
    await _execute_and_validate_step2(client, dossier_id)

    resp = await client.get(f"/api/dossiers/{dossier_id}/step3/download/ref")
    assert resp.status_code == 404
    assert "REF" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /api/dossiers/{id}/step3/validate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step3_validate_success(client: AsyncClient, tmp_path):
    """Validation should succeed and create an archive ZIP."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP3-VAL")
    await _execute_and_validate_step2(client, dossier_id)

    with _mock_rag_search_step3(), _mock_llm_ref(), _mock_llm_raux_p1(), _mock_llm_raux_p2():
        await client.post(f"/api/dossiers/{dossier_id}/step3/execute")

    resp = await client.post(f"/api/dossiers/{dossier_id}/step3/validate")
    assert resp.status_code == 200
    assert "archivé" in resp.json()["message"].lower()

    # Verify step is now validated
    step_resp = await client.get(f"/api/dossiers/{dossier_id}/steps/3")
    assert step_resp.json()["statut"] == "validé"

    # Verify archive.zip was created
    import zipfile
    archive_path = tmp_path / "dossiers" / str(dossier_id) / "archive.zip"
    assert archive_path.exists()
    with zipfile.ZipFile(archive_path, "r") as zf:
        names = zf.namelist()
        # Should contain files from step0, step2, step3
        assert any("requisition" in n for n in names)
        assert any("ref.md" in n for n in names)
        assert any("raux.md" in n for n in names)


# ---------------------------------------------------------------------------
# Step3 blocked without step2 validated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step3_execute_blocked_without_step2_validated(client: AsyncClient):
    """Step3 should be blocked if step2 is not validated."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP3-BLOCK")

    with _mock_rag_search_step3(), _mock_llm_ref(), _mock_llm_raux_p1(), _mock_llm_raux_p2():
        resp = await client.post(f"/api/dossiers/{dossier_id}/step3/execute")

    assert resp.status_code == 403
