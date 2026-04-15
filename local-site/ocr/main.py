"""
Judi-Expert — Service OCR (judi-ocr)

Service Python autonome exposant une API REST pour la conversion PDF-scan → texte brut.
Utilise Tesseract OCR pour les PDF-scan et PyMuPDF pour les PDF texte.
Port : 8001
"""

import io
import logging
import tempfile
from pathlib import Path

import fitz  # PyMuPDF
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Judi-Expert OCR Service",
    description="Service OCR pour l'extraction de texte depuis des PDF (scan ou texte)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seuil minimum de caractères par page pour considérer un PDF comme "texte extractible"
TEXT_PDF_CHAR_THRESHOLD = 30


def _is_text_pdf(pdf_bytes: bytes) -> bool:
    """Détecte si un PDF contient du texte extractible ou s'il s'agit d'un scan image."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            text = page.get_text().strip()
            if len(text) >= TEXT_PDF_CHAR_THRESHOLD:
                doc.close()
                return True
        doc.close()
        return False
    except Exception:
        return False


def _extract_text_pymupdf(pdf_bytes: bytes) -> tuple[str, int]:
    """Extrait le texte d'un PDF texte via PyMuPDF. Retourne (texte, nb_pages)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_text = []
    for page in doc:
        pages_text.append(page.get_text())
    num_pages = len(pages_text)
    doc.close()
    return "\n\n".join(pages_text), num_pages


def _extract_text_tesseract(pdf_bytes: bytes) -> tuple[str, int, float]:
    """Extrait le texte d'un PDF-scan via Tesseract OCR.

    Retourne (texte, nb_pages, confidence_moyenne).
    """
    import pytesseract
    from pdf2image import convert_from_bytes

    images = convert_from_bytes(pdf_bytes)
    pages_text = []
    confidences = []

    for img in images:
        # Extraction OCR avec données détaillées pour le score de confiance
        data = pytesseract.image_to_data(img, lang="fra", output_type=pytesseract.Output.DICT)
        page_text = pytesseract.image_to_string(img, lang="fra")
        pages_text.append(page_text)

        # Calcul de la confiance moyenne pour cette page
        page_confs = [
            int(c) for c in data["conf"] if str(c).lstrip("-").isdigit() and int(c) >= 0
        ]
        if page_confs:
            confidences.append(sum(page_confs) / len(page_confs))

    num_pages = len(images)
    text = "\n\n".join(pages_text)
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    return text, num_pages, avg_confidence


@app.post("/api/ocr/extract")
async def extract_text(file: UploadFile = File(...)):
    """Extrait le texte d'un fichier PDF (scan ou texte).

    Accepte un PDF en multipart/form-data.
    Retourne le texte extrait, le nombre de pages et le score de confiance.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Le fichier doit être au format PDF.")

    try:
        pdf_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur de lecture du fichier : {e}")

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Le fichier PDF est vide.")

    # Vérifier que c'est un PDF valide
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        doc.close()
    except Exception:
        raise HTTPException(status_code=400, detail="Le fichier PDF est corrompu ou invalide.")

    try:
        if _is_text_pdf(pdf_bytes):
            text, num_pages = _extract_text_pymupdf(pdf_bytes)
            confidence = 1.0  # Confiance maximale pour l'extraction directe
        else:
            text, num_pages, confidence = _extract_text_tesseract(pdf_bytes)
            confidence = round(confidence / 100.0, 4)  # Normaliser entre 0 et 1
    except Exception as e:
        logger.exception("Erreur lors de l'extraction du texte")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'extraction du texte : {e}",
        )

    return {
        "text": text,
        "pages": num_pages,
        "confidence": confidence,
    }


@app.get("/api/health", tags=["health"])
async def health_check():
    """Endpoint de vérification de santé du service OCR."""
    return {"status": "ok", "service": "judi-ocr"}
