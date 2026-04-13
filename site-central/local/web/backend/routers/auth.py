"""Router d'authentification locale — setup initial et login JWT."""

import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from database import get_db
from models.local_config import LocalConfig

# ---------------------------------------------------------------------------
# JWT configuration (from env vars)
# ---------------------------------------------------------------------------
JWT_SECRET = os.environ.get("JWT_SECRET", "CHANGEZ_MOI_secret_jwt_local")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES = int(os.environ.get("JWT_EXPIRATION_MINUTES", "1440"))

# ---------------------------------------------------------------------------
# Password hashing (passlib bcrypt)
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# Security scheme
# ---------------------------------------------------------------------------
bearer_scheme = HTTPBearer()

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class SetupRequest(BaseModel):
    password: str = Field(..., min_length=4, description="Mot de passe local")
    domaine: str = Field(..., min_length=1, description="Domaine d'expertise")


class SetupResponse(BaseModel):
    message: str
    domaine: str


class LoginRequest(BaseModel):
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Dependency — validate JWT from Authorization header
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Validate the JWT token and return the payload.

    Raises HTTPException 401 if the token is missing, expired or invalid.
    """
    token = credentials.credentials
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


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter()


@router.post("/setup", response_model=SetupResponse, status_code=status.HTTP_201_CREATED)
async def setup(body: SetupRequest, db: AsyncSession = Depends(get_db)):
    """Configuration initiale : mot de passe + domaine.

    Ne fonctionne que si aucune configuration n'existe encore.
    """
    result = await db.execute(select(LocalConfig).limit(1))
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La configuration initiale a déjà été effectuée",
        )

    config = LocalConfig(
        password_hash=_hash_password(body.password),
        domaine=body.domaine,
        is_configured=True,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)

    return SetupResponse(message="Configuration initiale réussie", domaine=config.domaine)


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Connexion locale — retourne un JWT si le mot de passe est correct."""
    result = await db.execute(select(LocalConfig).limit(1))
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration initiale non effectuée",
        )

    if not _verify_password(body.password, config.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mot de passe incorrect",
        )

    token = _create_access_token({"sub": "local_admin", "domaine": config.domaine})
    return LoginResponse(access_token=token)
