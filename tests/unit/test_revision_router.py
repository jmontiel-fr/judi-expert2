"""Tests unitaires pour le router de révision documentaire.

Teste les endpoints POST /api/revision/upload et POST /api/revision/text :
- Validation des extensions de fichier (rejet des formats non supportés)
- Validation de la taille des fichiers (rejet > 20 MB)
- Upload .docx réussi avec RevisionService mocké → FileResponse
- Upload .txt réussi avec RevisionService mocké → JSON response
- Soumission de texte réussie → JSON response
- Soumission de texte vide → HTTP 400
- Soumission de texte > 100k caractères → HTTP 400
- LLM indisponible → HTTP 503

Valide : Exigences 2.1, 2.2, 2.4, 2b.3, 2b.4, 7.1, 7.2
"""

import io
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from docx import Document as DocxDocument
from httpx import ASGITransport, AsyncClient

# Backend sur le path
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / "client-site" / "web" / "backend"),
)

from main import app
from services.llm_service import LLMConnectionError, LLMTimeoutError
from services.revision_service import RevisionResult


def _docx_with_text(text: str) -> bytes:
    doc = DocxDocument()
    doc.add_paragraph(text)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def _revision_result(text: str) -> RevisionResult:
    return RevisionResult(corrected_text=text, corrections=[], verbatim_count=0)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    """Client HTTP asynchrone pour tester l'application FastAPI."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Tests : Rejet des fichiers non supportés (HTTP 400)
# ---------------------------------------------------------------------------


class TestFileExtensionValidation:
    """Vérifie le rejet des fichiers avec extension non supportée."""

    @pytest.mark.asyncio
    async def test_pdf_file_rejected(self, client: AsyncClient):
        """Un fichier .pdf est rejeté avec HTTP 400."""
        resp = await client.post(
            "/api/revision/upload",
            files={"file": ("document.pdf", b"fake pdf content", "application/pdf")},
        )
        assert resp.status_code == 400
        assert "non supporté" in resp.json()["detail"].lower() or "format" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_xlsx_file_rejected(self, client: AsyncClient):
        """Un fichier .xlsx est rejeté avec HTTP 400."""
        resp = await client.post(
            "/api/revision/upload",
            files={"file": ("data.xlsx", b"fake xlsx content", "application/vnd.ms-excel")},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_jpg_file_rejected(self, client: AsyncClient):
        """Un fichier .jpg est rejeté avec HTTP 400."""
        resp = await client.post(
            "/api/revision/upload",
            files={"file": ("image.jpg", b"fake jpg content", "image/jpeg")},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Tests : Rejet des fichiers > 20 MB (HTTP 413)
# ---------------------------------------------------------------------------


class TestFileSizeValidation:
    """Vérifie le rejet des fichiers dépassant 20 MB."""

    @pytest.mark.asyncio
    async def test_file_over_20mb_rejected(self, client: AsyncClient):
        """Un fichier > 20 MB est rejeté avec HTTP 413."""
        # Créer un contenu de 21 MB
        large_content = b"x" * (21 * 1024 * 1024)
        resp = await client.post(
            "/api/revision/upload",
            files={"file": ("large.txt", large_content, "text/plain")},
        )
        assert resp.status_code == 413
        assert "20 MB" in resp.json()["detail"] or "taille" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests : Upload .docx réussi → FileResponse
# ---------------------------------------------------------------------------


class TestDocxUploadSuccess:
    """Vérifie qu'un upload .docx valide retourne une réponse JSON."""

    @pytest.mark.asyncio
    @patch("routers.revision._get_revision_service")
    async def test_docx_upload_returns_file_response(
        self, mock_get_service, client: AsyncClient
    ):
        """Un .docx valide retourne le texte corrigé en JSON."""
        mock_service = AsyncMock()
        mock_service.revise = AsyncMock(return_value=_revision_result("Texte corrigé."))
        mock_get_service.return_value = mock_service

        resp = await client.post(
            "/api/revision/upload",
            files={
                "file": (
                    "rapport.docx",
                    _docx_with_text("Texte original avec fotes."),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["corrected_text"] == "Texte corrigé."
        assert data["filename"] == "fichier-revu.txt"
        mock_service.revise.assert_called_once()


# ---------------------------------------------------------------------------
# Tests : Upload .txt réussi → JSON response
# ---------------------------------------------------------------------------


class TestTxtUploadSuccess:
    """Vérifie qu'un upload .txt valide retourne une réponse JSON."""

    @pytest.mark.asyncio
    @patch("routers.revision._get_revision_service")
    async def test_txt_upload_returns_json_response(
        self, mock_get_service, client: AsyncClient
    ):
        """Un .txt valide retourne du JSON avec corrected_text et filename."""
        mock_service = AsyncMock()
        mock_service.revise = AsyncMock(return_value=_revision_result("Texte corrigé par le LLM."))
        mock_get_service.return_value = mock_service

        resp = await client.post(
            "/api/revision/upload",
            files={"file": ("notes.txt", b"Texte original avec fotes.", "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["corrected_text"] == "Texte corrigé par le LLM."
        assert data["filename"] == "fichier-revu.txt"

    @pytest.mark.asyncio
    @patch("routers.revision._get_revision_service")
    async def test_md_upload_returns_json_response(
        self, mock_get_service, client: AsyncClient
    ):
        """Un .md valide retourne du JSON avec corrected_text et filename."""
        mock_service = AsyncMock()
        mock_service.revise = AsyncMock(return_value=_revision_result("# Titre corrigé"))
        mock_get_service.return_value = mock_service

        resp = await client.post(
            "/api/revision/upload",
            files={"file": ("readme.md", b"# Titre original", "text/markdown")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["corrected_text"] == "# Titre corrigé"
        assert data["filename"] == "fichier-revu.md"


# ---------------------------------------------------------------------------
# Tests : Soumission de texte réussie → JSON response
# ---------------------------------------------------------------------------


class TestTextSubmissionSuccess:
    """Vérifie qu'une soumission de texte valide retourne du JSON."""

    @pytest.mark.asyncio
    @patch("routers.revision._get_revision_service")
    async def test_text_submission_returns_corrected_text(
        self, mock_get_service, client: AsyncClient
    ):
        """Un texte valide retourne du JSON avec corrected_text."""
        mock_service = AsyncMock()
        mock_service.revise = AsyncMock(return_value=_revision_result("Texte corrigé."))
        mock_get_service.return_value = mock_service

        resp = await client.post(
            "/api/revision/text",
            json={"text": "Texte avec des fotes d'ortographe."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["corrected_text"] == "Texte corrigé."


# ---------------------------------------------------------------------------
# Tests : Soumission de texte vide → HTTP 400
# ---------------------------------------------------------------------------


class TestEmptyTextRejection:
    """Vérifie le rejet d'un texte vide."""

    @pytest.mark.asyncio
    async def test_empty_text_rejected(self, client: AsyncClient):
        """Un texte vide est rejeté avec HTTP 400."""
        resp = await client.post(
            "/api/revision/text",
            json={"text": ""},
        )
        assert resp.status_code == 400
        assert "vide" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_whitespace_only_text_rejected(self, client: AsyncClient):
        """Un texte ne contenant que des espaces est rejeté avec HTTP 400."""
        resp = await client.post(
            "/api/revision/text",
            json={"text": "   \n\t  "},
        )
        assert resp.status_code == 400
        assert "vide" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests : Texte > 100k caractères → HTTP 400
# ---------------------------------------------------------------------------


class TestTextTooLongRejection:
    """Vérifie le rejet d'un texte dépassant 100 000 caractères."""

    @pytest.mark.asyncio
    async def test_text_over_100k_chars_rejected(self, client: AsyncClient):
        """Un texte > 100 000 caractères est rejeté avec HTTP 400."""
        long_text = "A" * 100_001
        resp = await client.post(
            "/api/revision/text",
            json={"text": long_text},
        )
        assert resp.status_code == 400
        assert "100" in resp.json()["detail"] or "limite" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests : LLM indisponible → HTTP 503
# ---------------------------------------------------------------------------


class TestLLMUnavailable:
    """Vérifie que l'indisponibilité du LLM retourne HTTP 503."""

    @pytest.mark.asyncio
    @patch("routers.revision._get_revision_service")
    async def test_llm_timeout_on_upload_returns_503(
        self, mock_get_service, client: AsyncClient
    ):
        """Un timeout LLM lors de l'upload retourne HTTP 503."""
        mock_service = AsyncMock()
        mock_service.revise = AsyncMock(side_effect=LLMTimeoutError("LLM timeout"))
        mock_get_service.return_value = mock_service

        resp = await client.post(
            "/api/revision/upload",
            files={"file": ("doc.txt", b"Contenu valide.", "text/plain")},
        )
        assert resp.status_code == 503
        assert "indisponible" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    @patch("routers.revision._get_revision_service")
    async def test_llm_connection_error_on_upload_returns_503(
        self, mock_get_service, client: AsyncClient
    ):
        """Une erreur de connexion LLM lors de l'upload retourne HTTP 503."""
        mock_service = AsyncMock()
        mock_service.revise = AsyncMock(side_effect=LLMConnectionError("Connection refused"))
        mock_get_service.return_value = mock_service

        resp = await client.post(
            "/api/revision/upload",
            files={"file": ("doc.txt", b"Contenu valide.", "text/plain")},
        )
        assert resp.status_code == 503
        assert "indisponible" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    @patch("routers.revision._get_revision_service")
    async def test_llm_timeout_on_text_returns_503(
        self, mock_get_service, client: AsyncClient
    ):
        """Un timeout LLM lors de la soumission de texte retourne HTTP 503."""
        mock_service = AsyncMock()
        mock_service.revise = AsyncMock(side_effect=LLMTimeoutError("LLM timeout"))
        mock_get_service.return_value = mock_service

        resp = await client.post(
            "/api/revision/text",
            json={"text": "Texte valide à corriger."},
        )
        assert resp.status_code == 503
        assert "indisponible" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    @patch("routers.revision._get_revision_service")
    async def test_llm_connection_error_on_text_returns_503(
        self, mock_get_service, client: AsyncClient
    ):
        """Une erreur de connexion LLM sur texte retourne HTTP 503."""
        mock_service = AsyncMock()
        mock_service.revise = AsyncMock(side_effect=LLMConnectionError("Connection refused"))
        mock_get_service.return_value = mock_service

        resp = await client.post(
            "/api/revision/text",
            json={"text": "Texte valide à corriger."},
        )
        assert resp.status_code == 503
        assert "indisponible" in resp.json()["detail"].lower()
