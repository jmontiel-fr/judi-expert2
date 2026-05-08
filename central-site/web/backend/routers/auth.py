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
            # Générer des tokens factices pour le mode dev (inclut l'email encodé)
            import base64 as _b64
            email_b64 = _b64.urlsafe_b64encode(request.email.encode()).decode()
            dev_token = f"dev-token-{uuid.uuid4()}_{email_b64}"
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

    except cognito_service.NewPasswordRequiredError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="NEW_PASSWORD_REQUIRED",
            headers={"X-Cognito-Session": e.session},
        )

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "UserNotConfirmedException":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="USER_NOT_CONFIRMED",
            )
        # Message uniforme — ne révèle pas si c'est l'email ou le mot de passe
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=UNIFORM_LOGIN_ERROR,
        )


class NewPasswordRequest(BaseModel):
    email: str
    new_password: str
    session: str


@router.post("/new-password", response_model=AuthResponse)
async def new_password(request: NewPasswordRequest):
    """Changement de mot de passe obligatoire (première connexion admin).

    Répond au challenge NEW_PASSWORD_REQUIRED de Cognito.
    """
    try:
        auth_result = cognito_service.respond_to_new_password_challenge(
            email=request.email,
            new_password=request.new_password,
            session=request.session,
        )
        return AuthResponse(
            access_token=auth_result["AccessToken"],
            id_token=auth_result["IdToken"],
            refresh_token=auth_result["RefreshToken"],
        )
    except ClientError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de changer le mot de passe. Veuillez réessayer.",
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


class ConfirmSignUpRequest(BaseModel):
    email: str
    code: str


@router.post("/confirm")
async def confirm_sign_up(request: ConfirmSignUpRequest):
    """Confirme l'inscription avec le code reçu par email."""
    if IS_DEV:
        return {"message": "Compte confirmé (mode dev)"}

    try:
        cognito_service.confirm_sign_up(
            email=request.email,
            confirmation_code=request.code,
        )
        return {"message": "Compte confirmé avec succès. Vous pouvez maintenant vous connecter."}
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "CodeMismatchException":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Code de confirmation invalide.",
            )
        if error_code == "ExpiredCodeException":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Code expiré. Demandez un nouveau code.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erreur lors de la confirmation. Veuillez réessayer.",
        )


class ResendCodeRequest(BaseModel):
    email: str


@router.post("/resend-code")
async def resend_code(request: ResendCodeRequest):
    """Renvoie le code de confirmation par email."""
    if IS_DEV:
        return {"message": "Code renvoyé (mode dev)"}

    try:
        cognito_service.resend_confirmation_code(email=request.email)
    except ClientError:
        pass  # Ne pas révéler si l'email existe

    return {"message": "Si un compte existe avec cet email, un nouveau code a été envoyé."}
