"""Router de téléchargement de l'Application Locale — Site Central."""

import os
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from schemas.corpus import DownloadResponse

router = APIRouter()

ECR_REGISTRY = os.environ.get("ECR_REGISTRY", "")
IS_DEV = os.environ.get("APP_ENV", "production") == "development"


@router.get("/app", response_model=DownloadResponse)
async def download_app():
    """Retourne les informations de téléchargement du package Application Locale."""
    if IS_DEV:
        return DownloadResponse(
            download_url="/api/downloads/app/file",
            version="0.1.0-dev",
            description="Installateur Windows Judi-Expert (.exe). En mode développement, l'installateur n'est pas disponible. Utilisez les scripts locaux pour lancer l'application (voir instructions ci-dessous).",
            file_size="~500 Mo",
        )

    return DownloadResponse(
        download_url=f"https://{ECR_REGISTRY}/judi-expert/judi-expert-installer.exe"
        if ECR_REGISTRY
        else "https://downloads.judi-expert.fr/judi-expert-installer.exe",
        version="0.1.0",
        description="Installateur Windows Judi-Expert (.exe) — installe automatiquement Docker, les images et l'application locale sur votre PC. Double-cliquez pour lancer l'installation.",
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
        "  1. cd site-central/local/scripts && ./build.sh\n"
        "  2. cd ../../aws/app_locale_package && ./package.sh\n\n"
        "Le fichier .exe sera produit dans :\n"
        "  site-central/aws/app_locale_package/output/\n\n"
        "Prérequis : NSIS installé (https://nsis.sourceforge.io)\n",
        encoding="utf-8",
    )
    return FileResponse(
        path=str(readme_path),
        filename="judi-expert-install-instructions.txt",
        media_type="text/plain",
    )
