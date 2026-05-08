"""Router de téléchargement de l'Application Locale — Site Central."""

import os
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.app_version import AppVersion
from schemas.corpus import DownloadResponse
from services.version_reader import read_version_file

router = APIRouter()

ECR_REGISTRY = os.environ.get("ECR_REGISTRY", "")
IS_DEV = os.environ.get("APP_ENV", "production") == "development"

# Fallback : lire la version depuis le fichier VERSION si aucune version publiée en base
_VERSION_FILE = Path(os.environ.get("VERSION_FILE", "/app/VERSION"))
try:
    _file_version_info = read_version_file(_VERSION_FILE)
    DEFAULT_VERSION = _file_version_info.version
except (FileNotFoundError, ValueError):
    DEFAULT_VERSION = "0.1.0"


@router.get("/app", response_model=DownloadResponse)
async def download_app(db: AsyncSession = Depends(get_db)):
    """Retourne les informations de téléchargement du package Application Locale."""
    # Query the latest published version from the database
    result = await db.execute(
        select(AppVersion).order_by(desc(AppVersion.published_at)).limit(1)
    )
    latest_version = result.scalar_one_or_none()

    version = latest_version.version if latest_version else DEFAULT_VERSION

    if IS_DEV:
        return DownloadResponse(
            download_url="/api/downloads/app/file",
            version=f"{version}-dev",
            description="Installateur Windows Judi-Expert (.exe). En mode développement, l'installateur n'est pas disponible. Utilisez les scripts locaux pour lancer l'application (voir instructions ci-dessous).",
            file_size="~500 Mo",
        )

    # Use download_url from AppVersion if available, otherwise build default URL
    if latest_version and latest_version.download_url:
        download_url = latest_version.download_url
    else:
        filename = f"judi-expert-local-{version}.exe"
        download_url = (
            f"https://{ECR_REGISTRY}/judi-expert/{filename}"
            if ECR_REGISTRY
            else f"https://downloads.judi-expert.fr/{filename}"
        )

    return DownloadResponse(
        download_url=download_url,
        version=version,
        description=f"Installateur Windows Judi-Expert V{version} (.exe) — installe automatiquement Docker, les images et l'application locale sur votre PC. Double-cliquez pour lancer l'installation.",
        file_size="~500 Mo",
    )


@router.get("/app/file")
async def download_app_file():
    """Sert le fichier installateur .exe (ou les instructions en mode dev si absent)."""
    # Chercher le .exe dans le répertoire de sortie du packaging
    output_dir = Path("/data/app_locale_package/output")
    if output_dir.exists():
        exe_files = list(output_dir.glob("*.exe"))
        if exe_files:
            exe_path = exe_files[0]  # Prendre le premier .exe trouvé
            return FileResponse(
                path=str(exe_path),
                filename=exe_path.name,
                media_type="application/octet-stream",
            )

    # Fallback : instructions texte si le .exe n'a pas encore été généré
    readme_path = Path("/tmp/judi-expert-install-readme.txt")
    readme_path.write_text(
        "=== Judi-Expert — Installateur non encore généré ===\n\n"
        "L'installateur .exe n'a pas encore été compilé.\n"
        "Pour le générer, exécutez depuis la racine du projet :\n\n"
        "  1. cd local-site/scripts && ./build.sh\n"
        "  2. cd ../central-site/app_locale_package && ./package.sh\n\n"
        "Le fichier .exe sera produit dans :\n"
        "  central-site/app_locale_package/output/\n\n"
        "Prérequis : NSIS installé (https://nsis.sourceforge.io)\n",
        encoding="utf-8",
    )
    return FileResponse(
        path=str(readme_path),
        filename="judi-expert-install-instructions.txt",
        media_type="text/plain",
    )
