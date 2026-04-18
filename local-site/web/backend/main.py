"""
Judi-Expert — Application Locale Backend (FastAPI)

Point d'entrée principal de l'API backend de l'Application Locale.
Sert l'API REST sur le port 8000 à l'intérieur du conteneur judi-web.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from database import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise la base de données au démarrage."""
    await init_db()
    yield


app = FastAPI(
    title="Judi-Expert Local API",
    description="API backend de l'Application Locale Judi-Expert",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Capture les erreurs non gérées et renvoie un detail lisible."""
    logger.exception("Erreur non gérée sur %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Erreur interne : {type(exc).__name__}: {exc}"},
    )

# CORS — autorise le frontend Next.js (port 3000) à communiquer avec l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
from routers import auth, chatbot, config, dossiers, step_files, steps, tickets

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(dossiers.router, prefix="/api/dossiers", tags=["dossiers"])
app.include_router(steps.router, prefix="/api/dossiers", tags=["steps"])
app.include_router(step_files.router, prefix="/api/dossiers", tags=["step_files"])
app.include_router(chatbot.router, prefix="/api/chatbot", tags=["chatbot"])
app.include_router(tickets.router, prefix="/api/tickets", tags=["tickets"])


@app.get("/api/health", tags=["health"])
async def health_check():
    """Endpoint de vérification de santé du backend."""
    return {"status": "ok", "service": "judi-expert-local"}
