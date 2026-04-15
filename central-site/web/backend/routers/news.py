"""Router des news — Site Central."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.expert import Expert
from models.news import News, NewsRead
from routers.admin import get_admin_expert
from routers.profile import get_current_expert
from schemas.news import NewsCreate, NewsListItem, NewsResponse, NewsUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Public / User endpoints
# ---------------------------------------------------------------------------


async def _get_optional_expert_id(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[int]:
    """Tente d'extraire l'expert_id si un token Bearer est fourni."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        expert, _ = await get_current_expert(authorization=authorization, db=db)
        return expert.id
    except Exception:
        return None


@router.get("", response_model=list[NewsListItem])
async def list_news(
    db: AsyncSession = Depends(get_db),
    expert_id: Optional[int] = Depends(_get_optional_expert_id),
):
    """Liste les news visibles, triées par date décroissante."""
    result = await db.execute(
        select(News).where(News.visible == True).order_by(News.created_at.desc())
    )
    news_list = result.scalars().all()

    # Récupérer les IDs lus par l'expert
    read_ids: set[int] = set()
    if expert_id:
        reads = await db.execute(
            select(NewsRead.news_id).where(NewsRead.expert_id == expert_id)
        )
        read_ids = {r[0] for r in reads.all()}

    return [
        NewsListItem(
            id=n.id,
            titre=n.titre,
            visible=n.visible,
            created_at=n.created_at,
            is_read=n.id in read_ids,
        )
        for n in news_list
    ]


@router.get("/{news_id}", response_model=NewsResponse)
async def get_news(
    news_id: int,
    db: AsyncSession = Depends(get_db),
    expert_id: Optional[int] = Depends(_get_optional_expert_id),
):
    """Récupère une news par son ID et marque comme lue."""
    result = await db.execute(select(News).where(News.id == news_id))
    news = result.scalar_one_or_none()
    if not news or not news.visible:
        raise HTTPException(status_code=404, detail="News introuvable")

    # Marquer comme lue
    if expert_id:
        existing = await db.execute(
            select(NewsRead).where(
                NewsRead.news_id == news_id, NewsRead.expert_id == expert_id
            )
        )
        if not existing.scalar_one_or_none():
            db.add(NewsRead(news_id=news_id, expert_id=expert_id))
            await db.commit()

    return news
