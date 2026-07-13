"""Schémas Pydantic pour la gestion des versions."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class VersionResponse(BaseModel):
    """Réponse de l'endpoint GET /api/version."""

    latest_version: str
    download_url: str
    mandatory: bool
    update_type: Literal["images", "full"] = "images"
    release_notes: Optional[str] = None


class VersionCreateRequest(BaseModel):
    """Requête de publication d'une nouvelle version (admin)."""

    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    download_url: str = Field(..., min_length=1)
    mandatory: bool = True
    update_type: Literal["images", "full"] = "images"
    release_notes: Optional[str] = None


class VersionCreateResponse(BaseModel):
    """Réponse après publication d'une nouvelle version."""

    id: int
    version: str
    download_url: str
    mandatory: bool
    update_type: str
    release_notes: Optional[str]
    published_at: datetime

    model_config = {"from_attributes": True}
