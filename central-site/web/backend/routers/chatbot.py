"""Router ChatBot Site Central — assistant documentaire (utilisateurs connectés)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from models.expert import Expert
from routers.profile import get_current_expert
from services.llm_service import LLMError, LLMService
from services.rag_service import RAGError, RAGService

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Message de l'utilisateur")
    history: list[dict] = Field(
        default_factory=list,
        description="Historique de conversation [{role, content}, ...]",
    )


class ChatMessageResponse(BaseModel):
    response: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    body: ChatMessageRequest,
    current: tuple[Expert, str] = Depends(get_current_expert),
) -> ChatMessageResponse:
    """Envoie un message au chatbot et retourne la réponse.

    Le chatbot utilise le RAG (docs du site) pour contextualiser ses réponses.
    Accès réservé aux utilisateurs connectés.
    """
    # 1. Rechercher le contexte RAG
    rag = RAGService()
    contexte_parts: list[str] = []
    try:
        docs = await rag.search(query=body.message, limit=5)
        for doc in docs:
            contexte_parts.append(doc.content)
    except RAGError:
        logger.warning("Recherche RAG indisponible")

    contexte_rag = "\n\n".join(contexte_parts) if contexte_parts else ""

    # 2. Construire les messages
    messages: list[dict[str, str]] = []
    for msg in body.history[-10:]:  # Limiter l'historique à 10 messages
        if msg.get("role") in ("user", "assistant") and msg.get("content"):
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": body.message})

    # 3. Appeler le LLM
    llm = LLMService()
    try:
        assistant_response = await llm.chatbot(messages, contexte_rag)
    except LLMError as e:
        logger.error("Erreur LLM chatbot : %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Assistant temporairement indisponible. Veuillez réessayer.",
        )

    return ChatMessageResponse(response=assistant_response)
