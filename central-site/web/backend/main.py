"""
Judi-Expert — Site Central Backend (FastAPI)

Point d'entrée principal de l'API backend du Site Central.
Déployé sur AWS ECS Fargate, sert l'API REST sur le port 8000.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, seed_admin
from services.version_reader import read_version_file

# --- Lecture de la version au démarrage ---
# En conteneur Docker, le fichier VERSION est monté à /app/VERSION.
# En développement local, il est 2 niveaux au-dessus de ce fichier.
_VERSION_FILE_PATH = Path(
    os.environ.get("VERSION_FILE", "/app/VERSION")
)

try:
    _version_info = read_version_file(_VERSION_FILE_PATH)
    APP_VERSION = _version_info.version
    APP_VERSION_DATE = _version_info.date
except (FileNotFoundError, ValueError) as e:
    raise SystemExit(
        f"ERREUR FATALE : Impossible de lire le fichier de version "
        f"({_VERSION_FILE_PATH}) — {e}"
    ) from e

app = FastAPI(
    title="Judi-Expert Site Central API",
    description="API backend du Site Central Judi-Expert — gestion des experts, tickets, paiements et administration",
    version="0.1.0",
)


@app.on_event("startup")
async def startup():
    """Exécute les migrations Alembic, crée les tables manquantes et seed l'admin."""
    # Exécuter les migrations Alembic automatiquement
    import subprocess
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            import logging
            logging.getLogger(__name__).info("Alembic migrations applied successfully")
        else:
            import logging
            logging.getLogger(__name__).warning("Alembic migration warning: %s", result.stderr)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Alembic migration skipped: %s", e)

    await init_db()
    await seed_admin()

# CORS — autorise le frontend Next.js à communiquer avec l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://judi-expert.fr",
        "https://www.judi-expert.fr",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
from routers.auth import router as auth_router
from routers.profile import router as profile_router
from routers.tickets import router as tickets_router
from routers.webhooks import router as webhooks_router

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(profile_router, prefix="/api/profile", tags=["profile"])
app.include_router(tickets_router, prefix="/api/tickets", tags=["tickets"])
app.include_router(webhooks_router, prefix="/api/webhooks", tags=["webhooks"])

from routers.corpus import router as corpus_router
from routers.downloads import router as downloads_router
from routers.contact import router as contact_router
from routers.admin import router as admin_router
from routers.admin_corpus import router as admin_corpus_router
from routers.news import router as news_router

app.include_router(corpus_router, prefix="/api/corpus", tags=["corpus"])
app.include_router(downloads_router, prefix="/api/downloads", tags=["downloads"])
app.include_router(contact_router, prefix="/api/contact", tags=["contact"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(admin_corpus_router, prefix="/api/admin/corpus", tags=["admin-corpus"])
app.include_router(news_router, prefix="/api/news", tags=["news"])

from routers.chatbot import router as chatbot_router
from routers.admin_chatbot import router as admin_chatbot_router
from routers.version import router as version_router
from routers.internal import router as internal_router
from routers.subscription import router as subscription_router

app.include_router(chatbot_router, prefix="/api/chatbot", tags=["chatbot"])
app.include_router(admin_chatbot_router, prefix="/api/admin/chatbot", tags=["admin-chatbot"])
app.include_router(version_router, prefix="/api", tags=["version"])
app.include_router(internal_router, prefix="/api/internal", tags=["internal"])
app.include_router(subscription_router, prefix="/api/subscription", tags=["subscription"])


@app.get("/api/health", tags=["health"])
async def health_check():
    """Endpoint de vérification de santé du backend."""
    return {
        "status": "ok",
        "service": "judi-expert-site-central",
        "version": APP_VERSION,
        "version_date": APP_VERSION_DATE,
    }
