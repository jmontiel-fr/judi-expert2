"""Schémas Pydantic pour les corpus et téléchargements."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CorpusVersionResponse(BaseModel):
    """Détails d'une version de corpus."""

    id: int
    version: str
    description: str
    ecr_image_uri: str
    published_at: datetime

    model_config = {"from_attributes": True}


class CorpusResponse(BaseModel):
    """Informations d'un domaine avec ses versions de corpus."""

    nom: str
    repertoire: str
    actif: bool
    versions: list[CorpusVersionResponse] = []


class DownloadResponse(BaseModel):
    """Informations de téléchargement de l'Application Locale."""

    download_url: str
    version: str
    description: str
    file_size: Optional[str] = None


class ContenuItemResponse(BaseModel):
    """Un élément du contenu.yaml."""

    nom: str
    description: str
    type: str
    date_ajout: str
    download_url: Optional[str] = None
    downloaded: bool = False


class UrlItemResponse(BaseModel):
    """Une URL du urls.yaml."""

    nom: str
    url: str
    description: str
    type: str
    date_ajout: str


class AddUrlRequest(BaseModel):
    """Requête d'ajout d'une URL."""

    nom: str = Field(..., min_length=1)
    url: str = Field(..., pattern=r"^https?://")
    description: str
    type: str = Field(..., pattern=r"^(pdf_externe|site_web)$")
