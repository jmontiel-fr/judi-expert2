"""Schémas Pydantic pour les news."""

from datetime import datetime

from pydantic import BaseModel, Field


class NewsCreate(BaseModel):
    titre: str = Field(..., min_length=1, max_length=255)
    contenu: str = Field(..., min_length=1)


class NewsUpdate(BaseModel):
    titre: str | None = None
    contenu: str | None = None


class NewsResponse(BaseModel):
    id: int
    titre: str
    contenu: str
    visible: bool
    created_at: datetime
    updated_at: datetime


class NewsListItem(BaseModel):
    id: int
    titre: str
    visible: bool
    created_at: datetime
    is_read: bool = False
