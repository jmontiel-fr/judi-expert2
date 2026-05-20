"""Schémas Pydantic pour l'authentification du Site Central."""

from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

# Domaines email interdits — domaines fictifs, réservés (RFC 2606) et jetables courants
BLOCKED_EMAIL_DOMAINS: set[str] = {
    # Domaines réservés RFC 2606
    "example.com",
    "example.org",
    "example.net",
    "example.edu",
    "test.com",
    "test.org",
    "test.net",
    "localhost",
    "invalid",
    # Domaines jetables / temporaires courants
    "mailinator.com",
    "guerrillamail.com",
    "guerrillamail.net",
    "tempmail.com",
    "throwaway.email",
    "yopmail.com",
    "yopmail.fr",
    "sharklasers.com",
    "guerrillamailblock.com",
    "grr.la",
    "dispostable.com",
    "trashmail.com",
    "trashmail.net",
    "trashmail.me",
    "10minutemail.com",
    "temp-mail.org",
    "fakeinbox.com",
    "mailnesia.com",
    "maildrop.cc",
    "discard.email",
    "mailcatch.com",
    "jetable.org",
    "nospam.ze.tc",
    "trash-mail.com",
    "mytemp.email",
    "tempail.com",
    "mohmal.com",
    "getnada.com",
    "emailondeck.com",
    "33mail.com",
    "spam4.me",
    "spamgourmet.com",
}


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
    captcha_token: str
    accept_mentions_legales: bool
    accept_cgu: bool
    accept_protection_donnees: bool
    accept_newsletter: bool = False

    @field_validator("email")
    @classmethod
    def email_domain_not_blocked(cls, v: str) -> str:
        """Rejette les emails utilisant des domaines fictifs ou jetables."""
        domain = v.rsplit("@", 1)[-1].lower()
        # Bloquer le domaine exact
        if domain in BLOCKED_EMAIL_DOMAINS:
            raise ValueError(
                "Les adresses email utilisant des domaines temporaires ou fictifs ne sont pas acceptées"
            )
        # Bloquer les sous-domaines de example.* (ex: sub.example.com)
        for blocked in ("example.com", "example.org", "example.net", "example.edu"):
            if domain.endswith(f".{blocked}"):
                raise ValueError(
                    "Les adresses email utilisant des domaines temporaires ou fictifs ne sont pas acceptées"
                )
        return v

    @field_validator("captcha_token")
    @classmethod
    def captcha_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Le captcha est obligatoire")
        return v.strip()

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
