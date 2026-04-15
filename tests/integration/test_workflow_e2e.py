"""Tests d'intégration — Flux complet Step0 → Step3 avec données psychologie.

Teste le workflow d'expertise de bout en bout via l'API FastAPI de
l'Application Locale, avec services externes mockés (LLM, OCR, RAG,
Site Central).

Valide : Exigences 2.1, 10.1
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Path setup — Application Locale backend
# ---------------------------------------------------------------------------

_local_backend = str(
    Path(__file__).resolve().parents[2]
    / "local-site" / "web" / "backend"
)
sys.path.insert(0, _local_backend)

from models import Base  # noqa: E402
from database import get_db  # noqa: E402
from main import app  # noqa: E402
from routers.auth import get_current_user  # noqa: E402

pytestmark = pytest.mark.integration


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
    """AsyncClient avec BD in-memory, auth mockée et répertoire temporaire."""

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    async def _override_auth():
        return {"sub": "local_admin", "domaine": "psychologie"}

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_auth

    with patch("routers.steps.DATA_DIR", str(tmp_path)):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _mock_verify_ticket_success():
    return patch(
        "routers.dossiers._verify_ticket",
        new_callable=AsyncMock,
        return_value={"valid": True, "message": "Ticket valide"},
    )


def _mock_ocr_success(text: str = "Texte brut extrait de la réquisition du tribunal"):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"text": text, "pages": 3, "confidence": 0.92}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    return patch("routers.steps.httpx.AsyncClient", return_value=mock_client)


def _mock_llm_structurer():
    md = (
        "# Réquisition — Expertise Psychologique\n\n"
        "## Destinataire\nDr. Expert Psychologue\n\n"
        "## Questions du Tribunal\n\n"
        "1. Évaluer l'état psychologique du sujet\n"
        "2. Déterminer l'impact du traumatisme\n"
        "3. Proposer des recommandations thérapeutiques\n"
    )
    return patch(
        "routers.steps.LLMService.structurer_markdown",
        new_callable=AsyncMock,
        return_value=md,
    )


def _mock_llm_qmec():
    qmec = (
        "# QMEC — Plan d'Entretien\n\n"
        "## Section 1 : Identification\n- Nom, prénom, date de naissance\n\n"
        "## Section 2 : Anamnèse\n- Antécédents médicaux\n- Contexte familial\n\n"
        "## Section 3 : Examen clinique\n- Observation comportementale\n- Tests psychométriques\n"
    )
    return patch(
        "routers.steps.LLMService.generer_qmec",
        new_callable=AsyncMock,
        return_value=qmec,
    )


def _mock_rag_search():
    from services.rag_service import Document

    async def _fake_search(self, query, collection, limit=5):
        if "config_" in collection:
            return [Document(
                content="TPE Psychologie: Identification, Anamnèse, Examen clinique",
                score=0.9,
            )]
        return [Document(
            content="Corpus psychologie: Guide méthodologique expertise judiciaire",
            score=0.85,
        )]

    return patch("routers.steps.RAGService.search", _fake_search)


def _mock_llm_ref():
    ref = (
        "# Rapport d'Expertise Final\n\n"
        "## Objet\nExpertise psychologique ordonnée par le tribunal\n\n"
        "## Réponses aux Questions du Tribunal\n\n"
        "### Q1 : État psychologique\nLe sujet présente un état anxio-dépressif.\n\n"
        "### Q2 : Impact du traumatisme\nImpact significatif sur le fonctionnement quotidien.\n\n"
        "### Q3 : Recommandations\nSuivi psychothérapeutique recommandé.\n"
    )
    return patch(
        "routers.steps.LLMService.generer_ref",
        new_callable=AsyncMock,
        return_value=ref,
    )


def _mock_llm_raux_p1():
    return patch(
        "routers.steps.LLMService.generer_raux_p1",
        new_callable=AsyncMock,
        return_value="## Contestations possibles\n\n1. Méthodologie des tests\n2. Durée d'évaluation",
    )


def _mock_llm_raux_p2():
    return patch(
        "routers.steps.LLMService.generer_raux_p2",
        new_callable=AsyncMock,
        return_value="## REF Révisé\n\nVersion révisée tenant compte des contestations",
    )


async def _setup_config(client: AsyncClient):
    """Crée la configuration initiale (mot de passe + domaine + RAG)."""
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


# ---------------------------------------------------------------------------
# Test E2E : Flux complet Step0 → Step3
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_workflow_step0_to_step3(client: AsyncClient):
    """Flux complet d'expertise : setup → login → dossier → Step0 → Step3.

    Vérifie le workflow séquentiel avec données exemples psychologie.
    """
    # ── Setup : configuration initiale ──
    await _setup_config(client)

    # ── Login : authentification (déjà mockée via fixture) ──
    # Le client a déjà un token via l'override get_current_user

    # ── Créer un dossier avec ticket valide ──
    with _mock_verify_ticket_success():
        resp = await client.post("/api/dossiers", json={
            "nom": "Expertise Psychologie — Cas Test E2E",
            "ticket_id": "T-E2E-PSYCHO-001",
        })
    assert resp.status_code == 201
    dossier = resp.json()
    dossier_id = dossier["id"]
    assert dossier["domaine"] == "psychologie"
    assert dossier["statut"] == "actif"
    assert len(dossier["steps"]) == 4
    assert all(s["statut"] == "initial" for s in dossier["steps"])

    # ── Step0 : Extraction OCR ──
    with _mock_ocr_success(), _mock_llm_structurer():
        resp = await client.post(
            f"/api/dossiers/{dossier_id}/step0/extract",
            files={"file": ("requisition_psy.pdf", b"%PDF-1.4 fake scan", "application/pdf")},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert "Réquisition" in data["markdown"]
    assert "Questions du Tribunal" in data["markdown"]

    # Vérifier que le markdown est récupérable
    resp = await client.get(f"/api/dossiers/{dossier_id}/step0/markdown")
    assert resp.status_code == 200
    assert "Réquisition" in resp.json()["markdown"]

    # Modifier le markdown (édition par l'expert)
    edited_md = resp.json()["markdown"] + "\n\n## Note de l'expert\nAjout manuel."
    resp = await client.put(
        f"/api/dossiers/{dossier_id}/step0/markdown",
        json={"content": edited_md},
    )
    assert resp.status_code == 200

    # Vérifier que step0 est "réalisé"
    resp = await client.get(f"/api/dossiers/{dossier_id}/steps/0")
    assert resp.json()["statut"] == "réalisé"

    # Valider Step0 via le workflow engine
    from services.workflow_engine import workflow_engine as _wf

    override_fn = app.dependency_overrides[get_db]
    async for db in override_fn():
        await _wf.validate_step(dossier_id, 0, db)
        await db.commit()

    # Vérifier que step0 est "validé"
    resp = await client.get(f"/api/dossiers/{dossier_id}/steps/0")
    assert resp.json()["statut"] == "validé"

    # ── Step1 : Génération PEMEC (QMEC) ──
    with _mock_rag_search(), _mock_llm_qmec():
        resp = await client.post(f"/api/dossiers/{dossier_id}/step1/execute")
    assert resp.status_code == 201
    assert "QMEC" in resp.json()["qmec"]
    assert "Identification" in resp.json()["qmec"]

    # Télécharger le QMEC
    resp = await client.get(f"/api/dossiers/{dossier_id}/step1/download")
    assert resp.status_code == 200
    assert "QMEC" in resp.text

    # Valider Step1
    resp = await client.post(f"/api/dossiers/{dossier_id}/step1/validate")
    assert resp.status_code == 200

    resp = await client.get(f"/api/dossiers/{dossier_id}/steps/1")
    assert resp.json()["statut"] == "validé"

    # ── Step2 : Upload NE + REB ──
    ne_content = b"PK\x03\x04 Notes d'entretien psychologie"
    reb_content = b"PK\x03\x04 Rapport d'expertise brut psychologie"

    resp = await client.post(
        f"/api/dossiers/{dossier_id}/step2/upload",
        files={
            "ne": ("NE_psychologie.docx", ne_content,
                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            "reb": ("REB_psychologie.docx", reb_content,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        },
    )
    assert resp.status_code == 201
    # Le backend normalise les noms en "ne.docx" et "reb.docx"
    assert resp.json()["filenames"] == ["ne.docx", "reb.docx"]

    # Valider Step2
    resp = await client.post(f"/api/dossiers/{dossier_id}/step2/validate")
    assert resp.status_code == 200

    resp = await client.get(f"/api/dossiers/{dossier_id}/steps/2")
    assert resp.json()["statut"] == "validé"

    # ── Step3 : Génération REF + RAUX ──
    with _mock_rag_search(), _mock_llm_ref(), _mock_llm_raux_p1(), _mock_llm_raux_p2():
        resp = await client.post(f"/api/dossiers/{dossier_id}/step3/execute")
    assert resp.status_code == 201
    data = resp.json()
    assert "Rapport d'Expertise Final" in data["ref"]
    assert "Partie 1" in data["raux"]
    assert "Partie 2" in data["raux"]

    # Télécharger REF et RAUX
    resp = await client.get(f"/api/dossiers/{dossier_id}/step3/download/ref")
    assert resp.status_code == 200
    assert "Rapport d'Expertise Final" in resp.text

    resp = await client.get(f"/api/dossiers/{dossier_id}/step3/download/raux")
    assert resp.status_code == 200
    assert "Contestations" in resp.text

    # Valider Step3 (verrouille le dossier + archive)
    resp = await client.post(f"/api/dossiers/{dossier_id}/step3/validate")
    assert resp.status_code == 200
    assert "archivé" in resp.json()["message"].lower()

    # ── Vérifications finales ──

    # Le dossier est archivé
    resp = await client.get(f"/api/dossiers/{dossier_id}")
    dossier_final = resp.json()
    assert dossier_final["statut"] == "archive"

    # Toutes les étapes sont "validé"
    for step in dossier_final["steps"]:
        assert step["statut"] == "validé", (
            f"Step {step['step_number']} devrait être 'validé', "
            f"mais est '{step['statut']}'"
        )


# ---------------------------------------------------------------------------
# Test : Workflow séquentiel — impossible de sauter des étapes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cannot_skip_steps(client: AsyncClient):
    """Vérifie qu'on ne peut pas exécuter une étape sans valider la précédente."""
    await _setup_config(client)

    with _mock_verify_ticket_success():
        resp = await client.post("/api/dossiers", json={
            "nom": "Dossier Skip Test",
            "ticket_id": "T-E2E-SKIP-001",
        })
    dossier_id = resp.json()["id"]

    # Tenter d'exécuter Step1 sans avoir fait Step0 → 403
    with _mock_rag_search(), _mock_llm_qmec():
        resp = await client.post(f"/api/dossiers/{dossier_id}/step1/execute")
    assert resp.status_code == 403

    # Tenter d'uploader Step2 sans avoir fait Step0+Step1 → 403
    resp = await client.post(
        f"/api/dossiers/{dossier_id}/step2/upload",
        files={
            "ne": ("ne.docx", b"PK\x03\x04 fake", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            "reb": ("reb.docx", b"PK\x03\x04 fake", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        },
    )
    assert resp.status_code == 403

    # Tenter d'exécuter Step3 sans avoir fait les étapes précédentes → 403
    with _mock_rag_search(), _mock_llm_ref(), _mock_llm_raux_p1(), _mock_llm_raux_p2():
        resp = await client.post(f"/api/dossiers/{dossier_id}/step3/execute")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Test : Impossible de modifier une étape validée
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cannot_modify_validated_step(client: AsyncClient):
    """Vérifie qu'une étape validée est immuable."""
    await _setup_config(client)

    with _mock_verify_ticket_success():
        resp = await client.post("/api/dossiers", json={
            "nom": "Dossier Immutable Test",
            "ticket_id": "T-E2E-IMMUT-001",
        })
    dossier_id = resp.json()["id"]

    # Exécuter et valider Step0
    with _mock_ocr_success(), _mock_llm_structurer():
        await client.post(
            f"/api/dossiers/{dossier_id}/step0/extract",
            files={"file": ("req.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )

    from services.workflow_engine import workflow_engine as _wf

    override_fn = app.dependency_overrides[get_db]
    async for db in override_fn():
        await _wf.validate_step(dossier_id, 0, db)
        await db.commit()

    # Tenter de ré-exécuter Step0 → 403
    with _mock_ocr_success(), _mock_llm_structurer():
        resp = await client.post(
            f"/api/dossiers/{dossier_id}/step0/extract",
            files={"file": ("req2.pdf", b"%PDF-1.4 fake2", "application/pdf")},
        )
    assert resp.status_code == 403

    # Tenter de modifier le markdown de Step0 → 403
    resp = await client.put(
        f"/api/dossiers/{dossier_id}/step0/markdown",
        json={"content": "Tentative de modification"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Test : Dossier archivé — aucune modification possible
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_archived_dossier_is_locked(client: AsyncClient):
    """Après archivage (Step3 validé), aucune modification n'est possible."""
    await _setup_config(client)

    with _mock_verify_ticket_success():
        resp = await client.post("/api/dossiers", json={
            "nom": "Dossier Archive Lock Test",
            "ticket_id": "T-E2E-LOCK-001",
        })
    dossier_id = resp.json()["id"]

    # Exécuter tout le workflow rapidement
    with _mock_ocr_success(), _mock_llm_structurer():
        await client.post(
            f"/api/dossiers/{dossier_id}/step0/extract",
            files={"file": ("req.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )

    from services.workflow_engine import workflow_engine as _wf

    override_fn = app.dependency_overrides[get_db]
    async for db in override_fn():
        await _wf.validate_step(dossier_id, 0, db)
        await db.commit()

    with _mock_rag_search(), _mock_llm_qmec():
        await client.post(f"/api/dossiers/{dossier_id}/step1/execute")

    resp = await client.post(f"/api/dossiers/{dossier_id}/step1/validate")
    assert resp.status_code == 200

    await client.post(
        f"/api/dossiers/{dossier_id}/step2/upload",
        files={
            "ne": ("ne.docx", b"PK\x03\x04 fake ne", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            "reb": ("reb.docx", b"PK\x03\x04 fake reb", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        },
    )
    resp = await client.post(f"/api/dossiers/{dossier_id}/step2/validate")
    assert resp.status_code == 200

    with _mock_rag_search(), _mock_llm_ref(), _mock_llm_raux_p1(), _mock_llm_raux_p2():
        await client.post(f"/api/dossiers/{dossier_id}/step3/execute")

    resp = await client.post(f"/api/dossiers/{dossier_id}/step3/validate")
    assert resp.status_code == 200

    # Vérifier que le dossier est archivé
    resp = await client.get(f"/api/dossiers/{dossier_id}")
    assert resp.json()["statut"] == "archive"

    # Tenter de ré-exécuter Step0 sur un dossier archivé → 403
    with _mock_ocr_success(), _mock_llm_structurer():
        resp = await client.post(
            f"/api/dossiers/{dossier_id}/step0/extract",
            files={"file": ("req.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Test : Création de dossier avec ticket invalide
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_dossier_invalid_ticket(client: AsyncClient):
    """La création de dossier échoue avec un ticket invalide."""
    await _setup_config(client)

    with patch(
        "routers.dossiers._verify_ticket",
        new_callable=AsyncMock,
        return_value={"valid": False, "message": "Ticket invalide"},
    ):
        resp = await client.post("/api/dossiers", json={
            "nom": "Dossier Ticket Invalide",
            "ticket_id": "T-INVALID-001",
        })
    assert resp.status_code == 400
    assert "invalide" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test : Ticket déjà utilisé
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_dossier_duplicate_ticket(client: AsyncClient):
    """Un ticket déjà utilisé ne peut pas créer un second dossier."""
    await _setup_config(client)

    ticket_code = "T-E2E-DUP-001"

    with _mock_verify_ticket_success():
        resp = await client.post("/api/dossiers", json={
            "nom": "Premier Dossier",
            "ticket_id": ticket_code,
        })
    assert resp.status_code == 201

    # Tenter de créer un second dossier avec le même ticket → 409
    with _mock_verify_ticket_success():
        resp = await client.post("/api/dossiers", json={
            "nom": "Second Dossier",
            "ticket_id": ticket_code,
        })
    assert resp.status_code == 409
