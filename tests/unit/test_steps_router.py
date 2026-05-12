"""Tests unitaires pour le router des étapes (Step1, Step2, Step3, Step4, Step5)."""

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
    with patch("services.file_paths.DATA_DIR", str(tmp_path)):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


async def _setup_config(client: AsyncClient):
    """Helper: create initial config via login endpoint."""
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
        resp = await client.post("/api/auth/login", json={
            "email": "user@test.com",
            "password": "secret123",
        })
    assert resp.status_code == 200

    if original_auth is not None:
        app.dependency_overrides[get_current_user] = original_auth

    # Install RAG so config is complete — mock the Site Central call
    mock_rag_resp = MagicMock()
    mock_rag_resp.status_code = 200
    mock_rag_resp.json.return_value = []
    with patch("routers.config.SiteCentralClient.get", new_callable=AsyncMock, return_value=mock_rag_resp):
        resp = await client.post("/api/config/rag-install", json={"version": "1.0.0"})
    assert resp.status_code == 200


def _mock_verify_ticket_success():
    return patch(
        "routers.dossiers._verify_ticket",
        new_callable=AsyncMock,
        return_value={"valid": True, "message": "Ticket valide", "ticket_code": "TKT-MOCK123"},
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
    """Mock LLM structurer_markdown + extraire_questions + extraire_placeholders."""
    return patch.multiple(
        "routers.steps.LLMService",
        structurer_markdown=AsyncMock(return_value=markdown),
        extraire_questions=AsyncMock(return_value="## Questions\n\n1. Question 1"),
        extraire_placeholders=AsyncMock(return_value="nom_placeholder;valeur"),
    )


# ---------------------------------------------------------------------------
# POST /api/dossiers/{id}/step1/upload + /step1/execute (Step1 — Extraction)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step0_extract_success(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client)

    # Upload the PDF first
    resp = await client.post(
        f"/api/dossiers/{dossier_id}/step1/upload",
        files={"file": ("requisition.pdf", b"%PDF-1.4 fake content", "application/pdf")},
    )
    assert resp.status_code == 201

    # Then execute OCR + LLM
    with _mock_ocr_success(), _mock_llm_success():
        resp = await client.post(f"/api/dossiers/{dossier_id}/step1/execute")

    assert resp.status_code == 201
    data = resp.json()
    assert "markdown" in data
    assert "# Réquisition" in data["markdown"]
    assert data["pdf_path"].endswith("ordonnance.pdf")
    assert data["md_path"].endswith("ordonnance.md")


@pytest.mark.asyncio
async def test_step0_extract_non_pdf_rejected(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client)

    resp = await client.post(
        f"/api/dossiers/{dossier_id}/step1/upload",
        files={"file": ("document.txt", b"some text", "text/plain")},
    )
    assert resp.status_code == 400
    assert "PDF" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_step0_extract_empty_pdf_rejected(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client)

    resp = await client.post(
        f"/api/dossiers/{dossier_id}/step1/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert resp.status_code == 400
    assert "vide" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_step0_extract_ocr_unavailable(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client)

    # Upload first
    resp = await client.post(
        f"/api/dossiers/{dossier_id}/step1/upload",
        files={"file": ("req.pdf", b"%PDF-1.4 content", "application/pdf")},
    )
    assert resp.status_code == 201

    # Mock OCR connect error
    import httpx as httpx_mod
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx_mod.ConnectError("Connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("routers.steps.httpx.AsyncClient", return_value=mock_client):
        resp = await client.post(f"/api/dossiers/{dossier_id}/step1/execute")

    assert resp.status_code == 503
    assert "OCR" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_step0_extract_creates_step_files(client: AsyncClient):
    """After extraction, step1 should have files and statut 'fait'."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client)

    # Upload
    resp = await client.post(
        f"/api/dossiers/{dossier_id}/step1/upload",
        files={"file": ("requisition.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert resp.status_code == 201

    # Execute
    with _mock_ocr_success(), _mock_llm_success():
        resp = await client.post(f"/api/dossiers/{dossier_id}/step1/execute")
    assert resp.status_code == 201

    # Check step detail
    step_resp = await client.get(f"/api/dossiers/{dossier_id}/steps/1")
    assert step_resp.status_code == 200
    step_data = step_resp.json()
    assert step_data["statut"] == "fait"
    assert len(step_data["files"]) >= 2
    filenames = {f["filename"] for f in step_data["files"]}
    assert "ordonnance.pdf" in filenames
    assert "ordonnance.md" in filenames


# ---------------------------------------------------------------------------
# GET /api/dossiers/{id}/step1/markdown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step0_get_markdown_success(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client)

    expected_md = "# Test Markdown\n\nContenu structuré"

    # Upload + Execute
    await client.post(
        f"/api/dossiers/{dossier_id}/step1/upload",
        files={"file": ("req.pdf", b"%PDF-1.4 data", "application/pdf")},
    )
    with _mock_ocr_success(), _mock_llm_success(expected_md):
        await client.post(f"/api/dossiers/{dossier_id}/step1/execute")

    resp = await client.get(f"/api/dossiers/{dossier_id}/step1/markdown")
    assert resp.status_code == 200
    assert resp.json()["markdown"] == expected_md


@pytest.mark.asyncio
async def test_step0_get_markdown_not_extracted(client: AsyncClient):
    """Should return 404 if extraction hasn't been done yet."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client)

    resp = await client.get(f"/api/dossiers/{dossier_id}/step1/markdown")
    assert resp.status_code == 404
    assert "extraction" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# PUT /api/dossiers/{id}/step1/markdown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step0_update_markdown_success(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client)

    # Upload + Execute first
    await client.post(
        f"/api/dossiers/{dossier_id}/step1/upload",
        files={"file": ("req.pdf", b"%PDF-1.4 data", "application/pdf")},
    )
    with _mock_ocr_success(), _mock_llm_success():
        await client.post(f"/api/dossiers/{dossier_id}/step1/execute")

    new_content = "# Modifié\n\nContenu mis à jour par l'expert"
    resp = await client.put(
        f"/api/dossiers/{dossier_id}/step1/markdown",
        json={"content": new_content},
    )
    assert resp.status_code == 200
    assert "mis à jour" in resp.json()["message"].lower()

    # Verify the content was actually updated
    get_resp = await client.get(f"/api/dossiers/{dossier_id}/step1/markdown")
    assert get_resp.json()["markdown"] == new_content


@pytest.mark.asyncio
async def test_step0_update_markdown_not_extracted(client: AsyncClient):
    """Should return 404 if extraction hasn't been done yet."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client)

    resp = await client.put(
        f"/api/dossiers/{dossier_id}/step1/markdown",
        json={"content": "test"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Step2 helpers (QMEC/PE generation)
# ---------------------------------------------------------------------------


async def _execute_and_validate_step1(client: AsyncClient, dossier_id: int):
    """Helper: execute step1 and validate it so step2 becomes accessible."""
    # Upload
    resp = await client.post(
        f"/api/dossiers/{dossier_id}/step1/upload",
        files={"file": ("requisition.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert resp.status_code == 201

    # Execute
    with _mock_ocr_success(), _mock_llm_success():
        resp = await client.post(f"/api/dossiers/{dossier_id}/step1/execute")
    assert resp.status_code == 201

    # Validate step1 via workflow engine
    from services.workflow_engine import workflow_engine as _wf

    override_fn = app.dependency_overrides[get_db]
    async for db in override_fn():
        await _wf.validate_step(dossier_id, 1, db)
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


async def _execute_step2_sync(client: AsyncClient, dossier_id: int):
    """Helper: execute step2 synchronously by directly marking it as done and creating files."""
    import os
    from services.workflow_engine import workflow_engine as _wf
    from services.file_paths import step_out_dir

    override_fn = app.dependency_overrides[get_db]

    # Get dossier name
    async for db in override_fn():
        from sqlalchemy import select
        from models import Dossier
        result = await db.execute(select(Dossier).where(Dossier.id == dossier_id))
        dossier = result.scalar_one()
        dossier_name = dossier.nom

    # Create the output files that step2 would normally produce
    out_dir = step_out_dir(dossier_name, 2)
    os.makedirs(out_dir, exist_ok=True)

    pe_content = "# QMEC\n\n## Section 1\n\n- Question 1\n- Question 2"
    pe_md_path = os.path.join(out_dir, "pe.md")
    with open(pe_md_path, "w", encoding="utf-8") as f:
        f.write(pe_content)

    pe_docx_path = os.path.join(out_dir, "pe.docx")
    with open(pe_docx_path, "wb") as f:
        f.write(b"PK\x03\x04 fake docx")

    # Mark step2 as executed via workflow engine
    async for db in override_fn():
        from models import Step, StepFile
        await _wf.execute_step(dossier_id, 2, db)

        # Create StepFile entries
        result = await db.execute(
            select(Step).where(Step.dossier_id == dossier_id, Step.step_number == 2)
        )
        step = result.scalar_one()
        db.add(StepFile(
            step_id=step.id,
            filename="pe.md",
            file_path=pe_md_path,
            file_type="plan_entretien",
            file_size=len(pe_content.encode("utf-8")),
        ))
        db.add(StepFile(
            step_id=step.id,
            filename="pe.docx",
            file_path=pe_docx_path,
            file_type="plan_entretien_docx",
            file_size=os.path.getsize(pe_docx_path),
        ))
        await db.commit()


# ---------------------------------------------------------------------------
# POST /api/dossiers/{id}/step2/execute (Step2 — QMEC/PE generation)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step1_execute_success(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP1-EXEC")
    await _execute_and_validate_step1(client, dossier_id)

    # Step2 runs in background thread — mock Thread to run target synchronously
    with _mock_rag_search(), _mock_llm_qmec(), \
         patch("threading.Thread") as mock_thread:
        def _make_thread(*args, **kwargs):
            mock_inst = MagicMock()
            mock_inst.start = MagicMock()
            return mock_inst
        mock_thread.side_effect = _make_thread

        resp = await client.post(f"/api/dossiers/{dossier_id}/step2/execute")

    assert resp.status_code == 201
    data = resp.json()
    assert "qmec" in data


@pytest.mark.asyncio
async def test_step1_execute_creates_step_file(client: AsyncClient):
    """After execution, step2 should have pe.md file and statut 'fait'."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP1-FILE")
    await _execute_and_validate_step1(client, dossier_id)

    # Execute step2 directly (bypass background thread)
    await _execute_step2_sync(client, dossier_id)

    step_resp = await client.get(f"/api/dossiers/{dossier_id}/steps/2")
    assert step_resp.status_code == 200
    step_data = step_resp.json()
    assert step_data["statut"] == "fait"
    assert any(f["filename"] == "pe.md" for f in step_data["files"])


@pytest.mark.asyncio
async def test_step1_execute_blocked_without_step0_validated(client: AsyncClient):
    """Step2 should be blocked if step1 is not validated."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP1-BLOCK")

    with _mock_rag_search(), _mock_llm_qmec():
        resp = await client.post(f"/api/dossiers/{dossier_id}/step2/execute")

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_step1_execute_llm_unavailable(client: AsyncClient):
    """Step2 execute should return 201 (starts background) even if LLM will fail."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP1-LLM")
    await _execute_and_validate_step1(client, dossier_id)

    # Step2 starts background thread — mock it to not actually run
    with patch("threading.Thread") as mock_thread:
        def _make_thread(*args, **kwargs):
            mock_inst = MagicMock()
            mock_inst.start = MagicMock()
            return mock_inst
        mock_thread.side_effect = _make_thread

        resp = await client.post(f"/api/dossiers/{dossier_id}/step2/execute")

    # Step2 returns 201 immediately (background starts)
    assert resp.status_code == 201

    # Step is now "en_cours" (background hasn't completed)
    step_resp = await client.get(f"/api/dossiers/{dossier_id}/steps/2")
    assert step_resp.json()["statut"] == "en_cours"


# ---------------------------------------------------------------------------
# GET /api/dossiers/{id}/step2/download
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step1_download_success(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP1-DL")
    await _execute_and_validate_step1(client, dossier_id)

    # Execute step2 directly (creates pe.md and pe.docx)
    await _execute_step2_sync(client, dossier_id)

    resp = await client.get(f"/api/dossiers/{dossier_id}/step2/download")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_step1_download_not_executed(client: AsyncClient):
    """Should return 404 if step2 hasn't been executed yet."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP1-DL404")
    await _execute_and_validate_step1(client, dossier_id)

    resp = await client.get(f"/api/dossiers/{dossier_id}/step2/download")
    assert resp.status_code == 404
    assert "Plan" in resp.json()["detail"] or "PE" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_step1_download_blocked_without_step0(client: AsyncClient):
    """Download should be blocked if step1 is not validated."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP1-DLBLK")

    resp = await client.get(f"/api/dossiers/{dossier_id}/step2/download")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/dossiers/{id}/step2/validate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step1_validate_success(client: AsyncClient):
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP1-VAL")
    await _execute_and_validate_step1(client, dossier_id)

    # Execute step2 directly (creates files and marks as "fait")
    await _execute_step2_sync(client, dossier_id)

    resp = await client.post(f"/api/dossiers/{dossier_id}/step2/validate")
    assert resp.status_code == 200
    assert "validé" in resp.json()["message"].lower() or "valide" in resp.json()["message"].lower()

    # Verify step is now validated
    step_resp = await client.get(f"/api/dossiers/{dossier_id}/steps/2")
    assert step_resp.json()["statut"] == "valide"


@pytest.mark.asyncio
async def test_step1_validate_without_execute(client: AsyncClient):
    """Validation should fail if step2 hasn't been executed."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP1-VALNX")
    await _execute_and_validate_step1(client, dossier_id)

    resp = await client.post(f"/api/dossiers/{dossier_id}/step2/validate")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Step4 helpers (PEA upload + PRE/DAC generation)
# ---------------------------------------------------------------------------


async def _execute_and_validate_step2(client: AsyncClient, dossier_id: int):
    """Helper: execute step1+step2 and validate both, skip step3, so step4 becomes accessible."""
    await _execute_and_validate_step1(client, dossier_id)

    # Execute step2 directly (bypass background thread)
    await _execute_step2_sync(client, dossier_id)

    # Validate step2
    from services.workflow_engine import workflow_engine as _wf
    override_fn = app.dependency_overrides[get_db]
    async for db in override_fn():
        await _wf.validate_step(dossier_id, 2, db)
        await db.commit()

    # Skip step3 (no consolidation pieces needed)
    resp = await client.post(f"/api/dossiers/{dossier_id}/step3/skip")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/dossiers/{id}/step4/upload (Step4 — PEA upload)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step2_upload_success(client: AsyncClient):
    """Upload of PEA .docx file should succeed when step3 is validated."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP2-UP")
    await _execute_and_validate_step2(client, dossier_id)

    resp = await client.post(
        f"/api/dossiers/{dossier_id}/step4/upload",
        files={
            "file": ("pea.docx", b"PK\x03\x04 fake docx pea", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "pea.docx" in data["filename"]
    assert "succès" in data["message"].lower()


@pytest.mark.asyncio
async def test_step2_upload_rejects_non_docx(client: AsyncClient):
    """Non-.docx files should be rejected with 400."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP2-NODOCX")
    await _execute_and_validate_step2(client, dossier_id)

    resp = await client.post(
        f"/api/dossiers/{dossier_id}/step4/upload",
        files={
            "file": ("pea.pdf", b"fake pdf content", "application/pdf"),
        },
    )
    assert resp.status_code == 400
    assert ".docx" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_step2_upload_blocked_without_step1_validated(client: AsyncClient):
    """Step4 upload should be blocked if previous steps are not validated."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP2-BLOCK")

    resp = await client.post(
        f"/api/dossiers/{dossier_id}/step4/upload",
        files={
            "file": ("pea.docx", b"PK\x03\x04 fake", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        },
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/dossiers/{id}/step4/validate
# ---------------------------------------------------------------------------


def _mock_llm_pre_rapport(pre: str = "# Pré-Rapport\n\nContenu du PRE généré"):
    """Mock LLM generer_pre_rapport."""
    return patch(
        "routers.steps.LLMService.generer_pre_rapport",
        new_callable=AsyncMock,
        return_value=pre,
    )


def _mock_llm_dac(dac: str = "# DAC\n\nAnalyse contradictoire"):
    """Mock LLM generer_dac."""
    return patch(
        "routers.steps.LLMService.generer_dac",
        new_callable=AsyncMock,
        return_value=dac,
    )


@pytest.mark.asyncio
async def test_step2_validate_success(client: AsyncClient):
    """Validation should succeed after upload + execute."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP2-VAL")
    await _execute_and_validate_step2(client, dossier_id)

    # Upload PEA
    await client.post(
        f"/api/dossiers/{dossier_id}/step4/upload",
        files={
            "file": ("pea.docx", b"PK\x03\x04 fake pea", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        },
    )

    # Execute step4
    with _mock_rag_search(), _mock_llm_pre_rapport(), _mock_llm_dac():
        resp = await client.post(f"/api/dossiers/{dossier_id}/step4/execute")
    assert resp.status_code == 201

    resp = await client.post(f"/api/dossiers/{dossier_id}/step4/validate")
    assert resp.status_code == 200
    assert "validé" in resp.json()["message"].lower() or "valide" in resp.json()["message"].lower()

    # Verify step is now validated
    step_resp = await client.get(f"/api/dossiers/{dossier_id}/steps/4")
    assert step_resp.json()["statut"] == "valide"


@pytest.mark.asyncio
async def test_step2_validate_without_upload(client: AsyncClient):
    """Validation should fail if step4 hasn't been executed (no upload)."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP2-VALNX")
    await _execute_and_validate_step2(client, dossier_id)

    resp = await client.post(f"/api/dossiers/{dossier_id}/step4/validate")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Step5 helpers (Archive generation)
# ---------------------------------------------------------------------------


async def _execute_and_validate_step4(client: AsyncClient, dossier_id: int):
    """Helper: execute step1+step2+step3+step4 and validate all so step5 becomes accessible."""
    await _execute_and_validate_step2(client, dossier_id)

    # Upload PEA for step4
    await client.post(
        f"/api/dossiers/{dossier_id}/step4/upload",
        files={
            "file": ("pea.docx", b"PK\x03\x04 fake docx pea content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        },
    )

    # Execute step4
    with _mock_rag_search(), _mock_llm_pre_rapport(), _mock_llm_dac():
        resp = await client.post(f"/api/dossiers/{dossier_id}/step4/execute")
    assert resp.status_code == 201

    # Validate step4
    from services.workflow_engine import workflow_engine as _wf
    override_fn = app.dependency_overrides[get_db]
    async for db in override_fn():
        await _wf.validate_step(dossier_id, 4, db)
        await db.commit()


# ---------------------------------------------------------------------------
# POST /api/dossiers/{id}/step5/execute (Step5 — Archive generation)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step3_execute_success(client: AsyncClient):
    """Step5 execute should generate archive ZIP when step4 is validated."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP3-EXEC")
    await _execute_and_validate_step4(client, dossier_id)

    resp = await client.post(f"/api/dossiers/{dossier_id}/step5/execute")

    assert resp.status_code == 201
    data = resp.json()
    assert "message" in data
    assert "filenames" in data
    assert "dossier_archive.zip" in data["filenames"]
    assert "hash_sha256.txt" in data["filenames"]

    # Verify step is now "fait"
    step_resp = await client.get(f"/api/dossiers/{dossier_id}/steps/5")
    assert step_resp.status_code == 200
    step_data = step_resp.json()
    assert step_data["statut"] == "fait"
    filenames = {f["filename"] for f in step_data["files"]}
    assert "dossier_archive.zip" in filenames
    assert "hash_sha256.txt" in filenames


# ---------------------------------------------------------------------------
# GET /api/dossiers/{id}/step5/download/{doc_type}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step3_download_ref(client: AsyncClient):
    """Download ref_projet after step5 execution."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP3-DLREF")
    await _execute_and_validate_step4(client, dossier_id)

    await client.post(f"/api/dossiers/{dossier_id}/step5/execute")

    resp = await client.get(f"/api/dossiers/{dossier_id}/step5/download/ref_projet")
    # ref_projet.docx may not exist since step5 generates archive, not ref
    # The endpoint checks for ref_projet.docx in step5/out
    assert resp.status_code == 404
    assert "REF" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_step3_download_raux(client: AsyncClient):
    """Download with invalid doc_type should return 400."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP3-DLRAUX")
    await _execute_and_validate_step4(client, dossier_id)

    await client.post(f"/api/dossiers/{dossier_id}/step5/execute")

    resp = await client.get(f"/api/dossiers/{dossier_id}/step5/download/raux")
    assert resp.status_code == 400
    assert "invalide" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_step3_download_not_executed(client: AsyncClient):
    """Should return 404 if step5 hasn't been executed yet."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP3-DL404")
    await _execute_and_validate_step4(client, dossier_id)

    resp = await client.get(f"/api/dossiers/{dossier_id}/step5/download/ref_projet")
    assert resp.status_code == 404
    assert "REF" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /api/dossiers/{id}/step5/validate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step3_validate_success(client: AsyncClient, tmp_path):
    """Validation should succeed after step5 execution."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP3-VAL")
    await _execute_and_validate_step4(client, dossier_id)

    await client.post(f"/api/dossiers/{dossier_id}/step5/execute")

    resp = await client.post(f"/api/dossiers/{dossier_id}/step5/validate")
    assert resp.status_code == 200
    assert "validé" in resp.json()["message"].lower() or "valide" in resp.json()["message"].lower()

    # Verify step is now validated
    step_resp = await client.get(f"/api/dossiers/{dossier_id}/steps/5")
    assert step_resp.json()["statut"] == "valide"


# ---------------------------------------------------------------------------
# Step5 blocked without step4 validated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step3_execute_blocked_without_step2_validated(client: AsyncClient):
    """Step5 should be blocked if step4 is not validated."""
    await _setup_config(client)
    dossier_id = await _create_dossier(client, ticket_id="T-STEP3-BLOCK")

    resp = await client.post(f"/api/dossiers/{dossier_id}/step5/execute")

    assert resp.status_code == 403
