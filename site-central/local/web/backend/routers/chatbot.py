"""Router ChatBot — envoi de messages et historique de conversation.

Valide : Exigences 11.1, 11.2, 11.3
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.chat_message import ChatMessage
from models.local_config import LocalConfig
from routers.auth import get_current_user
from services.llm_service import LLMError, LLMService
from services.rag_service import RAGError, RAGService

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Message de l'utilisateur")
    session_id: int = Field(default=1, description="Identifiant de session")


class ChatMessageResponse(BaseModel):
    response: str


class ChatHistoryItem(BaseModel):
    role: str
    content: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    body: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(get_current_user),
) -> ChatMessageResponse:
    """Envoie un message au ChatBot et retourne la réponse de l'assistant."""
    # 1. Récupérer le domaine configuré
    result = await db.execute(select(LocalConfig).limit(1))
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration initiale non effectuée",
        )
    domaine = config.domaine

    # 2. Rechercher le contexte RAG
    rag = RAGService()
    contexte_parts: list[str] = []
    try:
        corpus_docs = await rag.search(
            query=body.message, collection=f"corpus_{domaine}", limit=5,
        )
        for doc in corpus_docs:
            contexte_parts.append(doc.content)
    except RAGError:
        logger.warning("Recherche RAG corpus_%s indisponible", domaine)

    try:
        system_docs = await rag.search(
            query=body.message, collection="system_docs", limit=3,
        )
        for doc in system_docs:
            contexte_parts.append(doc.content)
    except RAGError:
        logger.warning("Recherche RAG system_docs indisponible")

    contexte_rag = "\n\n".join(contexte_parts) if contexte_parts else ""

    # 3. Construire l'historique de conversation
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == body.session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    history_rows = history_result.scalars().all()

    messages: list[dict[str, str]] = []
    for row in history_rows:
        messages.append({"role": row.role, "content": row.content})
    messages.append({"role": "user", "content": body.message})

    # 4. Appeler le LLM
    llm = LLMService()
    try:
        assistant_response = await llm.chatbot(messages, contexte_rag)
    except LLMError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Assistant temporairement indisponible",
        )

    # 5. Stocker les messages
    user_msg = ChatMessage(
        session_id=body.session_id, role="user", content=body.message,
    )
    assistant_msg = ChatMessage(
        session_id=body.session_id, role="assistant", content=assistant_response,
    )
    db.add(user_msg)
    db.add(assistant_msg)
    await db.commit()

    return ChatMessageResponse(response=assistant_response)


@router.get("/history", response_model=list[ChatHistoryItem])
async def get_history(
    session_id: int = Query(default=1, description="Identifiant de session"),
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(get_current_user),
) -> list[ChatHistoryItem]:
    """Retourne l'historique de conversation pour une session donnée."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    rows = result.scalars().all()

    return [
        ChatHistoryItem(role=row.role, content=row.content, created_at=row.created_at)
        for row in rows
    ]
