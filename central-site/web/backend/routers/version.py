"""Router de version — Site Central.

Expose les endpoints de gestion des versions de l'Application Locale :
- GET /api/version : dernière version publiée (public)
- POST /api/admin/versions : publier une nouvelle version (admin)
- GET /api/admin/versions : lister les versions publiées (admin)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.app_version import AppVersion
from models.expert import Expert
from routers.admin import get_admin_expert
from schemas.version import VersionCreateRequest, VersionCreateResponse, VersionResponse

router = APIRouter()


@router.get("/version", response_model=VersionResponse)
async def get_latest_version(db: AsyncSession = Depends(get_db)):
    """Retourne la dernière version publiée de l'Application Locale."""
    result = await db.execute(
        select(AppVersion).order_by(desc(AppVersion.published_at)).limit(1)
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune version publiée",
        )
    return VersionResponse(
        latest_version=version.version,
        download_url=version.download_url,
        mandatory=version.mandatory,
        release_notes=version.release_notes,
    )


@router.post(
    "/admin/versions",
    response_model=VersionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def publish_version(
    request: VersionCreateRequest,
    _admin: Expert = Depends(get_admin_expert),
    db: AsyncSession = Depends(get_db),
):
    """Publie une nouvelle version (admin uniquement).

    La validation du format semver est assurée par le schéma Pydantic
    (regex pattern sur le champ `version`).
    """
    new_version = AppVersion(
        version=request.version,
        download_url=request.download_url,
        mandatory=request.mandatory,
        release_notes=request.release_notes,
    )
    db.add(new_version)
    await db.commit()
    await db.refresh(new_version)
    return new_version


@router.get("/admin/versions", response_model=list[VersionCreateResponse])
async def list_versions(
    _admin: Expert = Depends(get_admin_expert),
    db: AsyncSession = Depends(get_db),
):
    """Liste toutes les versions publiées (admin uniquement)."""
    result = await db.execute(
        select(AppVersion).order_by(desc(AppVersion.published_at))
    )
    return result.scalars().all()
