#!/bin/bash
# Judi-Expert — Ollama Entrypoint Script
# Starts the Ollama server, ensures the pinned model is present,
# and optionally checks for updates.
#
# Environment variables:
#   LLM_MODEL          — pinned model tag (default: mistral:7b-instruct-v0.3-q4_0)
#   LLM_AUTO_UPDATE    — "true" to auto-pull latest version on restart (default: false)

set -e

MODEL="${LLM_MODEL:-mistral:7b-instruct-v0.3-q4_0}"
AUTO_UPDATE="${LLM_AUTO_UPDATE:-false}"

# ── Start Ollama server in the background ─────────────────
ollama serve &
OLLAMA_PID=$!

echo "Waiting for Ollama server to start..."
until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
    sleep 1
done
echo "Ollama server is ready."

# ── Ensure the pinned model is available ──────────────────
MODEL_FAMILY="${MODEL%%:*}"

if ollama list | grep -q "$MODEL_FAMILY"; then
    echo "Model ${MODEL} is already available."

    # Optional: check for updates on restart
    if [ "$AUTO_UPDATE" = "true" ]; then
        echo "Auto-update enabled — pulling latest ${MODEL}..."
        ollama pull "${MODEL}" || echo "WARNING: update check failed, using cached model."
    fi
else
    echo "Model ${MODEL} not found. Downloading (this may take 15-30 min on first startup)..."
    ollama pull "${MODEL}"
    echo "Model ${MODEL} downloaded successfully."
fi

# ── Report available models ───────────────────────────────
echo "Available models:"
ollama list

# Keep the container running by waiting on the Ollama server process
wait $OLLAMA_PID
