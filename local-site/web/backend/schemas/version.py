"""Schémas Pydantic pour la gestion des versions (Application Locale)."""

from typing import Optional

from pydantic import BaseModel


class LocalVersionResponse(BaseModel):
    """Réponse de l'endpoint GET /api/version (Application Locale)."""

    current_version: str
    current_date: str
    update_available: bool
    latest_version: Optional[str] = None
    download_url: Optional[str] = None
    mandatory: Optional[bool] = None
    release_notes: Optional[str] = None


class UpdateStatusResponse(BaseModel):
    """Réponse de l'endpoint GET /api/version/update (progression)."""

    status: str  # "idle" | "downloading" | "installing" | "restarting" | "completed" | "error"
    progress: int  # 0-100
    step: Optional[str] = None
    error_message: Optional[str] = None


class LlmUpdateStatusResponse(BaseModel):
    """Réponse de l'endpoint GET /api/llm/update-status."""

    status: str  # "idle" | "downloading" | "ready" | "error"
    progress: int  # 0-100
    current_model: Optional[str] = None
    error_message: Optional[str] = None
