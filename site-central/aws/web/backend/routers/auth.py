"""Router d'authentification du Site Central — Cognito + reCAPTCHA."""

import logging
import os
import uuid

import bcrypt as _bcrypt
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.expert import Expert
from schemas.auth import AuthResponse, LoginRequest, LogoutRequest, RegisterRequest
from services import captcha_service, cognito_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Message d'erreur uniforme pour la connexion (Exigence 14.3)
UNIFORM_LOGIN_ERROR = "Identifiants invalides"

# Mode développement : bypass Cognito
IS_DEV = os.environ.get("APP_ENV", "production") == "development"


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Inscription d'un nouvel expert via Cognito.

    Valide les champs obligatoires et les cases à cocher,
    puis crée le compte dans Cognito et en base de données.
    """
    try:
        if IS_DEV:
            # Mode développement : bypass Cognito, inscription directe en BD
            # Vérifier si l'email existe déjà
            existing = await db.execute(
                select(Expert).where(Expert.email == request.email)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Un compte avec cet email existe déjà",
                )

            cognito_sub = f"dev-{uuid.uuid4()}"
            expert = Expert(
                cognito_sub=cognito_sub,
                email=request.email,
                nom=request.nom,
                prenom=request.prenom,
                adresse=request.adresse,
                ville=request.ville,
                code_postal=request.code_postal,
                telephone=request.telephone,
                domaine=request.domaine,
                accept_newsletter=request.accept_newsletter,
            )
            # Stocker le hash du mot de passe dans cognito_sub pour le login dev
            pw_hash = _bcrypt.hashpw(request.password.encode(), _bcrypt.gensalt()).decode()
            expert.cognito_sub = f"dev-{uuid.uuid4()}|{pw_hash}"
            db.add(expert)
            await db.commit()

            return {
                "message": "Inscription réussie",
                "cognito_sub": expert.cognito_sub.split("|")[0],
            }

        # Mode production : inscription via Cognito
        cognito_response = cognito_service.register_user(
            email=request.email,
            password=request.password,
            attributes={
                "nom": request.nom,
                "prenom": request.prenom,
                "adresse": request.adresse,
                "domaine": request.domaine,
            },
        )
        cognito_sub = cognito_response["UserSub"]

        # Enregistrement en base de données locale
        expert = Expert(
            cognito_sub=cognito_sub,
            email=request.email,
            nom=request.nom,
            prenom=request.prenom,
            adresse=request.adresse,
            ville=request.ville,
            code_postal=request.code_postal,
            telephone=request.telephone,
            domaine=request.domaine,
            accept_newsletter=request.accept_newsletter,
        )
        db.add(expert)
        await db.commit()

        return {
            "message": "Inscription réussie",
            "cognito_sub": cognito_sub,
        }

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "UsernameExistsException":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un compte avec cet email existe déjà",
            )
        logger.error("Erreur Cognito lors de l'inscription: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'inscription",
        )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Connexion d'un expert via Cognito avec validation Captcha.

    Retourne les tokens Cognito en cas de succès.
    Message d'erreur uniforme en cas d'échec (Exigence 14.3).
    """
    # Vérification du captcha Google V2 (bypass en mode dev)
    if not IS_DEV:
        captcha_valid = await captcha_service.verify_captcha(request.captcha_token)
        if not captcha_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Captcha invalide",
            )

    try:
        if IS_DEV:
            # Mode développement : login direct en BD
            result = await db.execute(
                select(Expert).where(Expert.email == request.email, Expert.is_deleted == False)
            )
            expert = result.scalar_one_or_none()
            if not expert:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=UNIFORM_LOGIN_ERROR,
                )
            # Vérifier le mot de passe hashé stocké dans cognito_sub
            parts = expert.cognito_sub.split("|", 1)
            if len(parts) < 2 or not _bcrypt.checkpw(request.password.encode(), parts[1].encode()):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=UNIFORM_LOGIN_ERROR,
                )
            # Générer des tokens factices pour le mode dev
            dev_token = f"dev-token-{uuid.uuid4()}"
            return AuthResponse(
                access_token=dev_token,
                id_token=dev_token,
                refresh_token=dev_token,
            )

        auth_result = cognito_service.login_user(
            email=request.email,
            password=request.password,
        )
        return AuthResponse(
            access_token=auth_result["AccessToken"],
            id_token=auth_result["IdToken"],
            refresh_token=auth_result["RefreshToken"],
        )

    except ClientError:
        # Message uniforme — ne révèle pas si c'est l'email ou le mot de passe
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=UNIFORM_LOGIN_ERROR,
        )


@router.post("/logout")
async def logout(request: LogoutRequest):
    """Déconnexion globale — invalide tous les tokens de l'utilisateur."""
    try:
        cognito_service.logout_user(request.access_token)
        return {"message": "Déconnexion réussie"}

    except ClientError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erreur lors de la déconnexion",
        )


class ForgotPasswordRequest(BaseModel):
    email: str


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Demande de réinitialisation de mot de passe.

    Retourne toujours un succès pour ne pas révéler si l'email existe.
    En mode dev, log simplement la demande.
    En production, déclenche le flux Cognito ForgotPassword.
    """
    if IS_DEV:
        logger.info("Demande de réinitialisation de mot de passe pour: %s (mode dev — pas d'email envoyé)", request.email)
        return {"message": "Si un compte existe avec cet email, un lien de réinitialisation a été envoyé."}

    try:
        cognito_service.forgot_password(email=request.email)
    except ClientError:
        pass  # Ne pas révéler si l'email existe

    return {"message": "Si un compte existe avec cet email, un lien de réinitialisation a été envoyé."}
