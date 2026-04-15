"""Router d'administration — Site Central."""

import logging
import os
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.expert import Expert
from models.news import News
from models.ticket import Ticket
from routers.profile import get_current_expert
from schemas.news import NewsCreate, NewsListItem, NewsResponse, NewsUpdate
from schemas.admin import ExpertListResponse, MonthStats, TicketStatsResponse

logger = logging.getLogger(__name__)

router = APIRouter()

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@judi-expert.fr")


async def get_admin_expert(
    current: tuple[Expert, str] = Depends(get_current_expert),
) -> Expert:
    """Vérifie que l'expert connecté est l'administrateur."""
    expert, _ = current
    if expert.email != ADMIN_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé à l'administrateur",
        )
    return expert


@router.get("/experts", response_model=list[ExpertListResponse])
async def list_experts(
    _admin: Expert = Depends(get_admin_expert),
    db: AsyncSession = Depends(get_db),
):
    """Liste tous les experts inscrits (admin uniquement)."""
    result = await db.execute(
        select(Expert).where(Expert.is_deleted == False).order_by(Expert.created_at.desc())
    )
    experts = result.scalars().all()
    return experts


@router.get("/stats/tickets", response_model=TicketStatsResponse)
async def ticket_stats(
    domaine: str = Query("Tous"),
    _admin: Expert = Depends(get_admin_expert),
    db: AsyncSession = Depends(get_db),
):
    """Statistiques des tickets avec filtre par domaine (admin uniquement)."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Base query filter
    base_filter = []
    if domaine != "Tous":
        base_filter.append(Ticket.domaine == domaine)

    # Today stats
    today_query = select(
        func.count(Ticket.id),
        func.coalesce(func.sum(Ticket.montant), Decimal("0")),
    ).where(Ticket.created_at >= today_start, *base_filter)
    today_result = await db.execute(today_query)
    today_row = today_result.one()
    today_count = today_row[0]
    today_amount = today_row[1]

    # Current month stats
    month_query = select(
        func.count(Ticket.id),
        func.coalesce(func.sum(Ticket.montant), Decimal("0")),
    ).where(Ticket.created_at >= month_start, *base_filter)
    month_result = await db.execute(month_query)
    month_row = month_result.one()
    month_count = month_row[0]
    month_amount = month_row[1]

    # Past months stats (before current month)
    past_query = select(
        extract("year", Ticket.created_at).label("year"),
        extract("month", Ticket.created_at).label("month"),
        func.count(Ticket.id),
        func.coalesce(func.sum(Ticket.montant), Decimal("0")),
    ).where(
        Ticket.created_at < month_start,
        *base_filter,
    ).group_by(
        extract("year", Ticket.created_at),
        extract("month", Ticket.created_at),
    ).order_by(
        extract("year", Ticket.created_at).desc(),
        extract("month", Ticket.created_at).desc(),
    )
    past_result = await db.execute(past_query)
    past_months = [
        MonthStats(
            month=f"{int(row[0])}-{int(row[1]):02d}",
            count=row[2],
            amount=row[3],
        )
        for row in past_result.all()
    ]

    return TicketStatsResponse(
        today_count=today_count,
        today_amount=today_amount,
        month_count=month_count,
        month_amount=month_amount,
        past_months=past_months,
    )


# ---------------------------------------------------------------------------
# Admin — News management
# ---------------------------------------------------------------------------


@router.get("/news", response_model=list[NewsListItem])
async def admin_list_news(
    _admin: Expert = Depends(get_admin_expert),
    db: AsyncSession = Depends(get_db),
):
    """Liste toutes les news (visibles et non visibles) — admin uniquement."""
    result = await db.execute(
        select(News).order_by(News.created_at.desc())
    )
    return [
        NewsListItem(
            id=n.id,
            titre=n.titre,
            visible=n.visible,
            created_at=n.created_at,
            is_read=False,
        )
        for n in result.scalars().all()
    ]


@router.post("/news", response_model=NewsResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_news(
    request: NewsCreate,
    _admin: Expert = Depends(get_admin_expert),
    db: AsyncSession = Depends(get_db),
):
    """Crée une nouvelle news — admin uniquement."""
    news = News(titre=request.titre, contenu=request.contenu, visible=False)
    db.add(news)
    await db.commit()
    await db.refresh(news)
    return news


@router.get("/news/{news_id}", response_model=NewsResponse)
async def admin_get_news(
    news_id: int,
    _admin: Expert = Depends(get_admin_expert),
    db: AsyncSession = Depends(get_db),
):
    """Récupère une news par ID — admin uniquement."""
    result = await db.execute(select(News).where(News.id == news_id))
    news = result.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail="News introuvable")
    return news


@router.put("/news/{news_id}", response_model=NewsResponse)
async def admin_update_news(
    news_id: int,
    request: NewsUpdate,
    _admin: Expert = Depends(get_admin_expert),
    db: AsyncSession = Depends(get_db),
):
    """Met à jour une news — admin uniquement."""
    result = await db.execute(select(News).where(News.id == news_id))
    news = result.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail="News introuvable")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(news, field, value)
    await db.commit()
    await db.refresh(news)
    return news


@router.put("/news/{news_id}/visibility", response_model=NewsResponse)
async def admin_toggle_visibility(
    news_id: int,
    _admin: Expert = Depends(get_admin_expert),
    db: AsyncSession = Depends(get_db),
):
    """Bascule la visibilité d'une news — admin uniquement."""
    result = await db.execute(select(News).where(News.id == news_id))
    news = result.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail="News introuvable")

    news.visible = not news.visible
    await db.commit()
    await db.refresh(news)
    return news


@router.delete("/news/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_news(
    news_id: int,
    _admin: Expert = Depends(get_admin_expert),
    db: AsyncSession = Depends(get_db),
):
    """Supprime une news — admin uniquement."""
    result = await db.execute(select(News).where(News.id == news_id))
    news = result.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail="News introuvable")

    await db.delete(news)
    await db.commit()
