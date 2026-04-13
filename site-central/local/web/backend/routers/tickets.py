"""Router de vérification de ticket standalone.

Fournit un endpoint indépendant pour vérifier un ticket auprès du Site Central,
utilisable par le frontend sans passer par la création de dossier.

Valide : Exigences 5.2, 5.3, 5.4, 35.6, 35.7
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from routers.auth import get_current_user
from services.site_central_client import (
    SiteCentralClient,
    SiteCentralError,
    get_business_hours_message,
    is_within_business_hours,
)

logger = logging.getLogger(__name__)


class TicketVerifyRequest(BaseModel):
    ticket_code: str = Field(..., min_length=1, description="Code du ticket à vérifier")


class TicketVerifyResponse(BaseModel):
    valid: bool
    message: str


router = APIRouter()


@router.post("/verify", response_model=TicketVerifyResponse)
async def verify_ticket(
    body: TicketVerifyRequest,
    _user: dict = Depends(get_current_user),
) -> TicketVerifyResponse:
    """Vérifie un ticket auprès du Site Central.

    Utilise le client centralisé avec retry et gestion des heures ouvrables.
    """
    client = SiteCentralClient()
    try:
        resp = await client.post(
            "/api/tickets/verify",
            json={"ticket_code": body.ticket_code},
        )
    except SiteCentralError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.message,
        )

    if resp.status_code == 200:
        data = resp.json()
        # Site Central returns {success: bool, ticket_code: str, error?: str}
        if data.get("success"):
            return TicketVerifyResponse(valid=True, message="Ticket valide")
        error = data.get("error", "Ticket invalide ou déjà utilisé")
        return TicketVerifyResponse(valid=False, message=error)

    # Non-200 response
    try:
        body_json = resp.json()
        detail = body_json.get("detail", body_json.get("message", "Ticket invalide ou déjà utilisé"))
    except Exception:
        detail = "Ticket invalide ou déjà utilisé"
    return TicketVerifyResponse(valid=False, message=detail)
