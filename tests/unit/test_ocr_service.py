"""Tests unitaires pour le service OCR (judi-ocr).

Teste l'extraction de texte depuis des PDF-scan (image) et des PDF texte,
ainsi que la gestion des erreurs (PDF corrompu, fichier vide).

Valide : Exigences 6.2, 6.3
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz  # PyMuPDF
import pytest
from fastapi.testclient import TestClient

# Éviter le conflit avec le module main du backend web déjà en cache
_saved_main = sys.modules.pop("main", None)
_saved_path = sys.path[:]

# Ajouter le service OCR au path pour les imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "local-site" / "ocr"))

import main as _ocr_main  # noqa: E402
from main import _is_text_pdf, app as ocr_app  # noqa: E402

# Enregistrer le module OCR sous un nom unique pour le patching
_OCR_MODULE_NAME = "ocr_main_module"
sys.modules[_OCR_MODULE_NAME] = _ocr_main

# Restaurer le module main original pour ne pas casser les autres tests
sys.path[:] = _saved_path
sys.modules.pop("main", None)
if _saved_main is not None:
    sys.modules["main"] = _saved_main

app = ocr_app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers : création de PDF en mémoire
# ---------------------------------------------------------------------------

def _make_text_pdf() -> bytes:
    """Crée un PDF contenant du texte extractible via PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Ceci est un document texte de test pour Judi-Expert. " * 5)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _make_minimal_pdf() -> bytes:
    """Crée un PDF minimal sans texte (simule un scan)."""
    doc = fitz.open()
    page = doc.new_page()
    # Insérer un rectangle coloré au lieu de texte pour simuler une image scannée
    page.draw_rect(fitz.Rect(50, 50, 200, 200), color=(0, 0, 0), fill=(0.9, 0.9, 0.9))
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _make_multipage_text_pdf(num_pages: int = 3) -> bytes:
    """Crée un PDF texte multi-pages."""
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page()
        page.insert_text(
            (72, 72),
            f"Page {i + 1} contenu suffisant pour dépasser le seuil de détection texte.",
        )
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ---------------------------------------------------------------------------
# Tests de détection du type de PDF
# ---------------------------------------------------------------------------

class TestIsTextPdf:
    """Tests pour la fonction _is_text_pdf."""

    def test_text_pdf_detected(self):
        """Un PDF avec du texte extractible est détecté comme PDF texte."""
        pdf_bytes = _make_text_pdf()
        assert _is_text_pdf(pdf_bytes) is True

    def test_scan_pdf_detected(self):
        """Un PDF sans texte extractible est détecté comme scan."""
        pdf_bytes = _make_minimal_pdf()
        assert _is_text_pdf(pdf_bytes) is False

    def test_invalid_bytes_returns_false(self):
        """Des données invalides retournent False (pas un PDF texte)."""
        assert _is_text_pdf(b"not a pdf") is False

    def test_empty_bytes_returns_false(self):
        """Des données vides retournent False."""
        assert _is_text_pdf(b"") is False


# ---------------------------------------------------------------------------
# Tests d'extraction de PDF texte (via PyMuPDF)
# ---------------------------------------------------------------------------

class TestExtractTextPdf:
    """Tests pour l'extraction de texte depuis un PDF texte."""

    def test_extract_text_pdf_returns_text(self):
        """L'extraction d'un PDF texte retourne le texte, le nombre de pages et confiance 1.0."""
        pdf_bytes = _make_text_pdf()
        response = client.post(
            "/api/ocr/extract",
            files={"file": ("document.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "Ceci est un document texte" in data["text"]
        assert data["pages"] == 1
        assert data["confidence"] == 1.0

    def test_extract_text_pdf_multipage(self):
        """L'extraction d'un PDF texte multi-pages retourne le bon nombre de pages."""
        pdf_bytes = _make_multipage_text_pdf(3)
        response = client.post(
            "/api/ocr/extract",
            files={"file": ("multi.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pages"] == 3
        assert data["confidence"] == 1.0


# ---------------------------------------------------------------------------
# Tests d'extraction de PDF-scan (via Tesseract, mocké)
# ---------------------------------------------------------------------------

class TestExtractScanPdf:
    """Tests pour l'extraction de texte depuis un PDF-scan (Tesseract mocké)."""

    @patch(f"{_OCR_MODULE_NAME}._extract_text_tesseract")
    def test_extract_scan_pdf_calls_tesseract(self, mock_tesseract_extract):
        """L'extraction d'un PDF-scan appelle Tesseract et retourne le texte OCR."""
        mock_tesseract_extract.return_value = ("Texte extrait par OCR", 1, 91.67)

        pdf_bytes = _make_minimal_pdf()
        response = client.post(
            "/api/ocr/extract",
            files={"file": ("scan.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Texte extrait par OCR"
        assert data["pages"] == 1
        # Confidence is normalized: 91.67 / 100 = 0.9167
        assert 0 <= data["confidence"] <= 1.0

        mock_tesseract_extract.assert_called_once()

    @patch(f"{_OCR_MODULE_NAME}._extract_text_tesseract")
    def test_extract_scan_pdf_confidence_normalized(self, mock_tesseract_extract):
        """Le score de confiance Tesseract est normalisé entre 0 et 1."""
        mock_tesseract_extract.return_value = ("Texte", 1, 80.0)

        pdf_bytes = _make_minimal_pdf()
        response = client.post(
            "/api/ocr/extract",
            files={"file": ("scan.pdf", pdf_bytes, "application/pdf")},
        )
        data = response.json()
        # Confiance moyenne = 80.0, normalisée = 0.8
        assert data["confidence"] == 0.8


# ---------------------------------------------------------------------------
# Tests de gestion des erreurs
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Tests pour la gestion des erreurs du service OCR."""

    def test_non_pdf_file_rejected(self):
        """Un fichier non-PDF est rejeté avec une erreur 400."""
        response = client.post(
            "/api/ocr/extract",
            files={"file": ("document.txt", b"Hello world", "text/plain")},
        )
        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]

    def test_empty_file_rejected(self):
        """Un fichier PDF vide est rejeté avec une erreur 400."""
        response = client.post(
            "/api/ocr/extract",
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
        assert response.status_code == 400
        assert "vide" in response.json()["detail"]

    def test_corrupted_pdf_rejected(self):
        """Un fichier PDF corrompu est rejeté avec une erreur 400."""
        response = client.post(
            "/api/ocr/extract",
            files={"file": ("corrupt.pdf", b"not-a-real-pdf-content", "application/pdf")},
        )
        assert response.status_code == 400
        assert "corrompu" in response.json()["detail"] or "invalide" in response.json()["detail"]

    def test_no_file_returns_422(self):
        """L'absence de fichier retourne une erreur 422."""
        response = client.post("/api/ocr/extract")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test du health check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    """Test de l'endpoint de santé."""

    def test_health_check(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "judi-ocr"
