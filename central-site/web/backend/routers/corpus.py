"""Router de gestion des corpus par domaine — Site Central."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.corpus_version import CorpusVersion
from models.domaine import Domaine
from schemas.corpus import CorpusResponse, CorpusVersionResponse
from services.domaines_service import load_domaines

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[CorpusResponse])
async def list_corpus(db: AsyncSession = Depends(get_db)):
    """Liste tous les corpus par domaine.

    Lit le fichier domaines.yaml pour la liste des domaines,
    puis enrichit avec les versions de corpus depuis la base de données.
    """
    try:
        domaines_config = load_domaines()
    except FileNotFoundError:
        logger.warning("Fichier domaines.yaml introuvable")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration des domaines introuvable",
        )
    except ValueError as e:
        logger.error("Erreur de parsing domaines.yaml : %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur de configuration des domaines",
        )

    result = []
    for domaine_cfg in domaines_config:
        nom = domaine_cfg.get("nom", "")

        # Chercher les versions en DB via le modèle Domaine
        stmt = select(Domaine).where(Domaine.nom == nom)
        db_domaine = (await db.execute(stmt)).scalars().first()

        versions: list[CorpusVersionResponse] = []
        if db_domaine:
            stmt_versions = (
                select(CorpusVersion)
                .where(CorpusVersion.domaine_id == db_domaine.id)
                .order_by(CorpusVersion.published_at.desc())
            )
            db_versions = (await db.execute(stmt_versions)).scalars().all()
            versions = [
                CorpusVersionResponse.model_validate(v) for v in db_versions
            ]

        result.append(
            CorpusResponse(
                nom=nom,
                repertoire=domaine_cfg.get("repertoire", ""),
                actif=domaine_cfg.get("actif", False),
                versions=versions,
            )
        )

    return result


@router.get("/{domaine}/versions", response_model=list[CorpusVersionResponse])
async def list_versions(domaine: str, db: AsyncSession = Depends(get_db)):
    """Liste toutes les versions du module RAG d'un domaine.

    Retourne les CorpusVersion depuis la base de données pour le domaine donné.
    """
    # Vérifier que le domaine existe dans domaines.yaml
    try:
        domaines_config = load_domaines()
    except (FileNotFoundError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration des domaines introuvable",
        )

    noms_domaines = [d.get("nom") for d in domaines_config]
    if domaine not in noms_domaines:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domaine '{domaine}' introuvable",
        )

    # Chercher le domaine en DB
    stmt = select(Domaine).where(Domaine.nom == domaine)
    db_domaine = (await db.execute(stmt)).scalars().first()

    if not db_domaine:
        # Le domaine existe dans le YAML mais pas encore en DB → liste vide
        return []

    stmt_versions = (
        select(CorpusVersion)
        .where(CorpusVersion.domaine_id == db_domaine.id)
        .order_by(CorpusVersion.published_at.desc())
    )
    db_versions = (await db.execute(stmt_versions)).scalars().all()

    return [CorpusVersionResponse.model_validate(v) for v in db_versions]
