"""Schémas Pydantic pour l'authentification du Site Central."""

from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    """Formulaire d'inscription — champs obligatoires + cases à cocher."""

    email: EmailStr
    password: str
    nom: str
    prenom: str
    adresse: str
    ville: str
    code_postal: str
    telephone: str
    domaine: str
    accept_mentions_legales: bool
    accept_cgu: bool
    accept_protection_donnees: bool
    accept_newsletter: bool = False

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        return v

    @field_validator("nom", "prenom", "adresse", "ville", "code_postal", "telephone", "domaine")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Ce champ est obligatoire")
        return v.strip()

    @field_validator("accept_mentions_legales", "accept_cgu", "accept_protection_donnees")
    @classmethod
    def must_be_accepted(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Cette case doit être cochée pour s'inscrire")
        return v


class LoginRequest(BaseModel):
    """Formulaire de connexion — email + mot de passe + captcha."""

    email: EmailStr
    password: str
    captcha_token: str

    @field_validator("captcha_token")
    @classmethod
    def captcha_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Le captcha est obligatoire")
        return v.strip()


class AuthResponse(BaseModel):
    """Réponse d'authentification avec tokens Cognito."""

    access_token: str
    id_token: str
    refresh_token: str


class LogoutRequest(BaseModel):
    """Requête de déconnexion."""

    access_token: str
