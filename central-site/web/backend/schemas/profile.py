"""Schémas Pydantic pour la gestion du profil expert."""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


# --- Regex patterns ---
# SIRET : exactement 14 chiffres
SIRET_PATTERN = re.compile(r"^\d{14}$")


def validate_siret(value: str) -> str:
    """Valide qu'un SIRET contient exactement 14 chiffres."""
    if not SIRET_PATTERN.match(value):
        raise ValueError("Le SIRET doit contenir exactement 14 chiffres")
    return value


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
    # Champs facturation
    entreprise: Optional[str] = None
    company_address: Optional[str] = None
    billing_email: Optional[str] = None
    siret: Optional[str] = None

    model_config = {"from_attributes": True}


class ProfileUpdateRequest(BaseModel):
    """Champs modifiables du profil expert."""

    nom: Optional[str] = None
    prenom: Optional[str] = None
    adresse: Optional[str] = None
    domaine: Optional[str] = None
    accept_newsletter: Optional[bool] = None
    # Champs facturation
    entreprise: Optional[str] = None
    company_address: Optional[str] = None
    billing_email: Optional[EmailStr] = None
    siret: Optional[str] = None

    @field_validator("nom", "prenom", "adresse", "domaine")
    @classmethod
    def not_blank_if_provided(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Ce champ ne peut pas être vide")
        return v.strip() if v else v

    @field_validator("siret")
    @classmethod
    def validate_siret_field(cls, v: Optional[str]) -> Optional[str]:
        """Valide le format SIRET si fourni."""
        if v is not None and v.strip():
            return validate_siret(v.strip())
        return v


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
