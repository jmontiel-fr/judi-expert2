"""
Judi-Expert — Site Central Backend (FastAPI)

Point d'entrée principal de l'API backend du Site Central.
Déployé sur AWS ECS Fargate, sert l'API REST sur le port 8000.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db

app = FastAPI(
    title="Judi-Expert Site Central API",
    description="API backend du Site Central Judi-Expert — gestion des experts, tickets, paiements et administration",
    version="0.1.0",
)


@app.on_event("startup")
async def startup():
    """Crée les tables si elles n'existent pas (mode dev)."""
    await init_db()

# CORS — autorise le frontend Next.js à communiquer avec l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        # Ajouter le domaine de production CloudFront ici
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

app.include_router(corpus_router, prefix="/api/corpus", tags=["corpus"])
app.include_router(downloads_router, prefix="/api/downloads", tags=["downloads"])
app.include_router(contact_router, prefix="/api/contact", tags=["contact"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])


@app.get("/api/health", tags=["health"])
async def health_check():
    """Endpoint de vérification de santé du backend."""
    return {"status": "ok", "service": "judi-expert-site-central"}
