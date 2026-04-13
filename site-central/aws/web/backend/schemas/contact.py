"""Schémas Pydantic pour le formulaire de contact."""

from pydantic import BaseModel, Field


class ContactRequest(BaseModel):
    """Requête de soumission du formulaire de contact."""

    domaine: str = Field(..., min_length=1)
    objet: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class ContactResponse(BaseModel):
    """Réponse de confirmation du formulaire de contact."""

    message: str
