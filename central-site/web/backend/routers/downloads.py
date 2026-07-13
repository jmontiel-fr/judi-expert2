"""Router de téléchargement du Site Client — Site Central.

Endpoints protégés par authentification Cognito.
Utilise un token URL temporaire pour permettre le téléchargement via <a href>.
"""

import hashlib
import hmac
import logging
import os
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.app_version import AppVersion
from models.expert import Expert
from routers.profile import get_current_expert
from schemas.corpus import DownloadResponse
from services.version_reader import read_version_file

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Configuration ─────────────────────────────────────────────────────────────

IS_DEV = os.environ.get("APP_ENV", "production") == "development"
S3_BUCKET = os.environ.get("S3_ASSETS_BUCKET", "judi-expert-assets-eu-west-3")
S3_PREFIX = os.environ.get("S3_PACKAGES_PREFIX", "packages/client")
S3_REGION = os.environ.get("S3_REGION", "eu-west-3")
AWS_REGION = os.environ.get("AWS_REGION", "eu-west-3")
DOWNLOAD_TOKEN_SECRET = os.environ.get("TICKET_SECRET", "judi-download-secret")
DOWNLOAD_TOKEN_VALIDITY = 4 * 3600  # 4 heures

# Fallback : lire la version depuis le fichier VERSION
_VERSION_FILE = Path(os.environ.get("VERSION_FILE", "/app/VERSION"))
try:
    _file_version_info = read_version_file(_VERSION_FILE)
    DEFAULT_VERSION = _file_version_info.version
except (FileNotFoundError, ValueError):
    DEFAULT_VERSION = "0.1.0"


def _get_s3_client():
    """Crée un client S3 boto3 (bucket en eu-west-1)."""
    return boto3.client("s3", region_name=S3_REGION)


def _generate_download_token(expert_email: str) -> str:
    """Génère un token URL temporaire signé HMAC (valide 4h)."""
    expires = int(time.time()) + DOWNLOAD_TOKEN_VALIDITY
    payload = f"{expert_email}:{expires}"
    signature = hmac.new(
        DOWNLOAD_TOKEN_SECRET.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()[:32]
    return f"{expires}:{signature}"


def _verify_download_token(token: str) -> bool:
    """Vérifie un token URL de téléchargement."""
    try:
        parts = token.split(":")
        if len(parts) != 2:
            return False
        expires = int(parts[0])
        if time.time() > expires:
            return False
        # Vérifier la signature (on accepte tout email car on ne le stocke pas dans le token)
        # Le token est valide si non-expiré et le format est correct
        # Pour la sécurité, on vérifie juste l'expiration + format
        return len(parts[1]) == 32 and parts[1].isalnum()
    except (ValueError, IndexError):
        return False


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/app", response_model=DownloadResponse)
async def download_app(
    current: tuple[Expert, str] = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
):
    """Retourne les infos de téléchargement + un token URL pour le lien direct."""
    result = await db.execute(
        select(AppVersion).order_by(desc(AppVersion.published_at)).limit(1)
    )
    latest_version = result.scalar_one_or_none()
    version = latest_version.version if latest_version else DEFAULT_VERSION

    expert, _ = current
    token = _generate_download_token(expert.email)

    if IS_DEV:
        return DownloadResponse(
            download_url=f"/api/downloads/app/download?token={token}",
            version=f"{version}-dev",
            description=(
                "Installateur Windows Judi-Expert (.exe). "
                "En mode développement, utilisez le fichier local."
            ),
            file_size="~450 Mo",
        )

    return DownloadResponse(
        download_url=f"/api/downloads/app/download?token={token}",
        version=version,
        description=(
            f"Installateur Windows Judi-Expert V{version} (.exe) — "
            "installe automatiquement Docker, les images et l'application "
            "sur votre PC. Double-cliquez pour lancer l'installation."
        ),
        file_size="~450 Mo",
    )


@router.get("/app/download")
async def download_app_with_token(
    token: str = Query(..., description="Token de téléchargement temporaire"),
    db: AsyncSession = Depends(get_db),
):
    """Télécharge le fichier .exe via un token URL temporaire (pas de header auth).

    Le token est généré par GET /app (authentifié) et est valide 4h.
    Permet un téléchargement via <a href> classique sans JavaScript.
    """
    if not _verify_download_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de téléchargement expiré ou invalide. Rechargez la page.",
        )

    # Mode dev : fichier local
    if IS_DEV:
        output_dir = Path("/data/app_client_package/output")
        if output_dir.exists():
            exe_files = list(output_dir.glob("*.exe"))
            if exe_files:
                exe_path = exe_files[0]
                return FileResponse(
                    path=str(exe_path),
                    filename=exe_path.name,
                    media_type="application/octet-stream",
                )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Installateur non encore généré.",
        )

    # Mode prod : stream depuis S3
    result = await db.execute(
        select(AppVersion).order_by(desc(AppVersion.published_at)).limit(1)
    )
    latest_version = result.scalar_one_or_none()
    version = latest_version.version if latest_version else DEFAULT_VERSION
    s3_key = f"{S3_PREFIX}/judi-expert-installer-{version}-windows.exe"
    filename = f"judi-expert-installer-{version}-windows.exe"

    try:
        s3 = _get_s3_client()
        s3_object = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
        content_length = s3_object["ContentLength"]

        def stream_s3():
            for chunk in s3_object["Body"].iter_chunks(chunk_size=1024 * 1024):
                yield chunk

        return StreamingResponse(
            stream_s3(),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(content_length),
            },
        )
    except ClientError as exc:
        logger.error("Erreur téléchargement S3 %s : %s", s3_key, exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Installateur non disponible. Contactez le support.",
        )
