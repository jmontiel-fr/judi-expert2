"""Schémas Pydantic pour la gestion du profil expert."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class ProfileResponse(BaseModel):
    """Données du profil expert."""

    id: int
    email: str
    nom: str
    prenom: str
    adresse: str
    ville: str = ""
    code_postal: str = ""
    telephone: str = ""
    domaine: str
    accept_newsletter: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProfileUpdateRequest(BaseModel):
    """Champs modifiables du profil expert."""

    nom: Optional[str] = None
    prenom: Optional[str] = None
    adresse: Optional[str] = None
    domaine: Optional[str] = None
    accept_newsletter: Optional[bool] = None

    @field_validator("nom", "prenom", "adresse", "domaine")
    @classmethod
    def not_blank_if_provided(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Ce champ ne peut pas être vide")
        return v.strip() if v else v


class ChangePasswordRequest(BaseModel):
    """Requête de changement de mot de passe."""

    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Le nouveau mot de passe doit contenir au moins 8 caractères")
        return v
