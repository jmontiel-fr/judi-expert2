"""
Judi-Expert — Application Locale Backend (FastAPI)

Point d'entrée principal de l'API backend de l'Application Locale.
Sert l'API REST sur le port 8000 à l'intérieur du conteneur judi-web.
"""

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from database import async_session_factory, init_db
from models.local_config import LocalConfig
from services.hardware_service import HardwareDetector, ProfileSelector
from services.llm_service import ActiveProfile

logger = logging.getLogger(__name__)

# Appliquer les migrations Alembic au démarrage (synchrone, avant FastAPI)
try:
    import subprocess
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0:
        logging.getLogger(__name__).info("Migrations Alembic appliquées")
    else:
        logging.getLogger(__name__).warning("Migrations Alembic : %s", result.stderr.strip())
except Exception as exc:
    logging.getLogger(__name__).warning("Migrations Alembic non appliquées : %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise la base de données et détecte le matériel au démarrage."""
    await init_db()

    # --- Hardware detection and profile selection ---
    try:
        # 1. Detect hardware
        detector = HardwareDetector()
        hardware_info = detector.detect()
        logger.info(
            "Hardware detected: cpu=%s, freq=%.2f GHz, cores=%d, ram=%.1f GB, gpu=%s",
            hardware_info.cpu_model,
            hardware_info.cpu_freq_ghz,
            hardware_info.cpu_cores,
            hardware_info.ram_total_gb,
            hardware_info.gpu_name or "None",
        )

        # 2. Read override from DB
        override: str | None = None
        local_config: LocalConfig | None = None
        try:
            async with async_session_factory() as session:
                result = await session.execute(select(LocalConfig).limit(1))
                local_config = result.scalar_one_or_none()
                if local_config:
                    override = local_config.performance_profile_override
        except Exception as db_read_exc:
            logger.warning(
                "Failed to read performance override from DB: %s. "
                "Using auto-detection without override.",
                db_read_exc,
            )

        # 3. Select profile
        selector = ProfileSelector()
        active_profile = selector.get_active_profile(hardware_info, override)
        logger.info(
            "Performance profile selected: %s (override=%s)",
            active_profile.name,
            override or "auto",
        )

        # 4. Store hardware info in DB
        hardware_json = json.dumps({
            "cpu_model": hardware_info.cpu_model,
            "cpu_freq_ghz": hardware_info.cpu_freq_ghz,
            "cpu_cores": hardware_info.cpu_cores,
            "ram_total_gb": hardware_info.ram_total_gb,
            "gpu_name": hardware_info.gpu_name,
            "gpu_vram_gb": hardware_info.gpu_vram_gb,
        })
        try:
            async with async_session_factory() as session:
                if local_config:
                    # Re-fetch within this session to avoid detached instance
                    result = await session.execute(select(LocalConfig).limit(1))
                    config_row = result.scalar_one_or_none()
                    if config_row:
                        config_row.detected_hardware_json = hardware_json
                        session.add(config_row)
                        await session.commit()
        except Exception as db_write_exc:
            logger.warning(
                "Failed to persist detected hardware to DB: %s",
                db_write_exc,
            )

        # 5. Apply profile to ActiveProfile singleton
        ActiveProfile.set(active_profile, hardware_info)

    except Exception as hw_exc:
        logger.error(
            "Hardware detection failed: %s. "
            "LLM service will use environment/default fallbacks.",
            hw_exc,
        )

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
from routers import auth, chatbot, config, dossiers, revision, step_files, steps, tickets, version

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(dossiers.router, prefix="/api/dossiers", tags=["dossiers"])
app.include_router(steps.router, prefix="/api/dossiers", tags=["steps"])
app.include_router(step_files.router, prefix="/api/dossiers", tags=["step_files"])
app.include_router(chatbot.router, prefix="/api/chatbot", tags=["chatbot"])
app.include_router(tickets.router, prefix="/api/tickets", tags=["tickets"])
app.include_router(revision.router, prefix="/api/revision", tags=["revision"])
app.include_router(version.router, prefix="/api", tags=["version"])


@app.get("/api/health", tags=["health"])
async def health_check():
    """Endpoint de vérification de santé du backend."""
    return {"status": "ok", "service": "judi-expert-local"}
