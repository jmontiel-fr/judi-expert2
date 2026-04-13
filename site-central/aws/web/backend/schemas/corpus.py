"""Schémas Pydantic pour les corpus et téléchargements."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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
