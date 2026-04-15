#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────
# build.sh — Build all local Docker images for Judi-Expert
# Builds: judi-web-backend, judi-web-frontend, judi-ocr
# Note: judi-llm (ollama/ollama:latest) and judi-rag
#       (qdrant/qdrant:latest) use official images — no
#       build needed.
# Exigences : 30.1, 30.3
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Judi-Expert — Build des images Docker locales${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

# ── judi-ocr ───────────────────────────────────────────
echo -e "${YELLOW}[1/3]${NC} Build de ${GREEN}judi-ocr${NC} (Tesseract + pdf2image)..."
docker build -t judi-ocr "$PROJECT_DIR/ocr"
echo -e "${GREEN}  ✔ judi-ocr built successfully${NC}"
echo ""

# ── judi-web-backend ───────────────────────────────────
echo -e "${YELLOW}[2/3]${NC} Build de ${GREEN}judi-web-backend${NC} (FastAPI + SQLite)..."
docker build -t judi-web-backend "$PROJECT_DIR/web/backend"
echo -e "${GREEN}  ✔ judi-web-backend built successfully${NC}"
echo ""

# ── judi-web-frontend ─────────────────────────────────
echo -e "${YELLOW}[3/3]${NC} Build de ${GREEN}judi-web-frontend${NC} (Next.js PWA)..."
docker build -t judi-web-frontend "$PROJECT_DIR/web/frontend"
echo -e "${GREEN}  ✔ judi-web-frontend built successfully${NC}"
echo ""

echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✔ Toutes les images ont été construites${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Note :${NC} judi-llm (ollama/ollama:latest) et judi-rag (qdrant/qdrant:latest)"
echo -e "       utilisent des images officielles — aucun build nécessaire."
