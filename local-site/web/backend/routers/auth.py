"""Router d'authentification locale — login via Site Central."""

import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from database import get_db
from models.local_config import LocalConfig
from services.site_central_client import SiteCentralClient, SiteCentralError

# ---------------------------------------------------------------------------
# JWT configuration (from env vars)
# ---------------------------------------------------------------------------
JWT_SECRET = os.environ.get("JWT_SECRET", "CHANGEZ_MOI_secret_jwt_local")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES = int(os.environ.get("JWT_EXPIRATION_MINUTES", "1440"))

# ---------------------------------------------------------------------------
# Security scheme
# ---------------------------------------------------------------------------
bearer_scheme = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    domaine: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Dependency — validate JWT from Authorization header
# ---------------------------------------------------------------------------


def _decode_token(token: str) -> dict:
    """Decode and validate a JWT token, returning the payload."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide",
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    token: str | None = Query(None),
) -> dict:
    """Validate the JWT token from Authorization header or query parameter.

    Supports both ``Authorization: Bearer <token>`` (for API calls) and
    ``?token=<token>`` (for direct browser downloads/views).
    """
    raw_token: str | None = None
    if credentials and credentials.credentials:
        raw_token = credentials.credentials
    elif token:
        raw_token = token

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification manquant",
        )

    return _decode_token(raw_token)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Connexion locale — vérifie les credentials auprès du Site Central.

    1. Envoie email + password au Site Central pour vérification
    2. Si OK → stocke/met à jour l'email en local + génère un JWT local
    3. Si KO → retourne l'erreur du Site Central
    """
    # Vérifier les credentials auprès du Site Central
    client = SiteCentralClient()
    try:
        resp = await client.post("/api/auth/login", json={
            "email": body.email,
            "password": body.password,
            "captcha_token": "local-app-bypass",
        })
    except SiteCentralError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.message,
        )

    if resp.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    if resp.status_code != 200:
        detail = "Erreur lors de la vérification auprès du Site Central"
        try:
            detail = resp.json().get("detail", detail)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )

    # Credentials valides — stocker/mettre à jour l'email en local
    result = await db.execute(select(LocalConfig).limit(1))
    config = result.scalar_one_or_none()

    if config is None:
        # Première connexion : créer la config locale
        config = LocalConfig(
            password_hash="",  # pas utilisé, auth via site central
            domaine=os.environ.get("DOMAINE", "psychologie"),
            email=body.email,
            is_configured=True,
        )
        db.add(config)
    else:
        config.email = body.email

    await db.commit()
    await db.refresh(config)

    # Générer un JWT local
    token = _create_access_token({
        "sub": body.email,
        "email": body.email,
        "domaine": config.domaine,
    })

    return LoginResponse(
        access_token=token,
        email=body.email,
        domaine=config.domaine,
    )


@router.get("/info")
async def auth_info(db: AsyncSession = Depends(get_db)):
    """Retourne les infos publiques de la config locale (email, domaine).

    Endpoint sans authentification, utilisé par la page de connexion.
    """
    result = await db.execute(select(LocalConfig).limit(1))
    config = result.scalar_one_or_none()
    if config is None:
        return {"configured": False, "email": None, "domaine": None}
    return {
        "configured": True,
        "email": getattr(config, "email", None),
        "domaine": config.domaine,
    }
