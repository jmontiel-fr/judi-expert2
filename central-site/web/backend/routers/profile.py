"""Router de gestion du profil expert — Site Central."""

import logging
import os

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.expert import Expert
from schemas.profile import ChangePasswordRequest, ProfileResponse, ProfileUpdateRequest
from services import cognito_service

logger = logging.getLogger(__name__)

router = APIRouter()

IS_DEV = os.environ.get("APP_ENV", "production") == "development"


async def get_current_expert(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> tuple[Expert, str]:
    """Extrait le token d'accès du header Authorization Bearer et retrouve l'expert."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'accès manquant ou invalide",
        )

    access_token = authorization[len("Bearer "):]
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'accès manquant ou invalide",
        )

    if IS_DEV and access_token.startswith("dev-token-"):
        # Mode dev : retrouver l'expert via l'email encodé dans le token
        # Format : dev-token-<uuid>_<email_base64>
        import base64 as _b64

        email = None
        underscore_idx = access_token.rfind("_")
        if underscore_idx > 0:
            try:
                email = _b64.urlsafe_b64decode(access_token[underscore_idx + 1:]).decode()
            except Exception:
                pass

        if email:
            result = await db.execute(
                select(Expert).where(Expert.email == email, Expert.is_deleted == False)
            )
        else:
            # Fallback : dernier expert inscrit
            result = await db.execute(
                select(Expert).where(Expert.is_deleted == False).order_by(Expert.id.desc())
            )
        expert = result.scalars().first()
        if expert:
            return expert, access_token
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide")

    try:
        user_info = cognito_service.get_user(access_token)
        cognito_sub = user_info["Username"]
    except ClientError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'accès manquant ou invalide",
        )

    result = await db.execute(
        select(Expert).where(Expert.cognito_sub == cognito_sub, Expert.is_deleted == False)
    )
    expert = result.scalar_one_or_none()
    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expert non trouvé",
        )

    return expert, access_token


@router.get("", response_model=ProfileResponse)
async def get_profile(
    current: tuple[Expert, str] = Depends(get_current_expert),
):
    """Récupère le profil de l'expert connecté."""
    expert, _ = current
    return expert


@router.put("", response_model=ProfileResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    current: tuple[Expert, str] = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
):
    """Met à jour le profil de l'expert connecté.

    Tous les experts sont traités en B2B dans les métadonnées Stripe.
    Les champs facturation (entreprise, company_address, billing_email, siret)
    sont optionnels. Le SIRET sera affiché comme "non attribué" s'il n'est pas renseigné.
    """
    expert, _ = current

    update_data = request.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(expert, field, value)

    await db.commit()
    await db.refresh(expert)
    return expert


@router.put("/password")
async def change_password(
    request: ChangePasswordRequest,
    current: tuple[Expert, str] = Depends(get_current_expert),
):
    """Change le mot de passe de l'expert via Cognito."""
    _, access_token = current

    try:
        cognito_service.change_password(
            access_token=access_token,
            old_password=request.old_password,
            new_password=request.new_password,
        )
        return {"message": "Mot de passe modifié avec succès"}
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "NotAuthorizedException":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ancien mot de passe incorrect",
            )
        if error_code == "InvalidPasswordException":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le nouveau mot de passe ne respecte pas les critères",
            )
        logger.error("Erreur Cognito lors du changement de mot de passe: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du changement de mot de passe",
        )


@router.delete("/delete")
async def delete_account(
    current: tuple[Expert, str] = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
):
    """Supprime le compte expert (Cognito + marquage en base)."""
    expert, access_token = current

    try:
        cognito_service.delete_user(access_token)
    except ClientError as e:
        logger.error("Erreur Cognito lors de la suppression du compte: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la suppression du compte",
        )

    expert.is_deleted = True
    await db.commit()

    return {"message": "Compte supprimé avec succès"}
