#!/bin/bash
# Judi-Expert — Ollama Entrypoint Script
# Starts the Ollama server, ensures the pinned model is present,
# checks for model updates in the background, and writes update status.
#
# Environment variables:
#   LLM_MODEL          — pinned model tag (default: mistral:7b-instruct-v0.3-q4_0)
#   LLM_AUTO_UPDATE    — "true" to auto-pull latest version on restart (default: false)

set -e

MODEL="${LLM_MODEL:-mistral:7b-instruct-v0.3-q4_0}"
AUTO_UPDATE="${LLM_AUTO_UPDATE:-false}"
STATUS_FILE="/root/.ollama/update-status.json"

# ── Helper: write update status JSON ─────────────────────
# Writes the LLM update status to a JSON file that the backend reads
# to report progress to the frontend.
#
# Arguments:
#   $1 - status: idle | downloading | ready | error
#   $2 - progress: 0-100
#   $3 - model: model tag string
#   $4 - started_at: ISO timestamp or empty
#   $5 - error: error message or empty
write_status() {
    local status="$1"
    local progress="$2"
    local model="$3"
    local started_at="$4"
    local error="$5"

    # Format error field as JSON null or quoted string
    local error_json="null"
    if [ -n "$error" ]; then
        # Escape double quotes and backslashes in error message
        local escaped_error
        escaped_error=$(printf '%s' "$error" | sed 's/\\/\\\\/g; s/"/\\"/g')
        error_json="\"${escaped_error}\""
    fi

    # Format started_at field as JSON null or quoted string
    local started_at_json="null"
    if [ -n "$started_at" ]; then
        started_at_json="\"${started_at}\""
    fi

    cat > "$STATUS_FILE" <<EOF
{
  "status": "${status}",
  "progress": ${progress},
  "model": "${model}",
  "started_at": ${started_at_json},
  "error": ${error_json}
}
EOF
}

# ── Helper: get local model digest ───────────────────────
# Retrieves the digest of the currently installed model via Ollama API.
# Returns empty string if model not found or API unavailable.
get_local_digest() {
    curl -sf http://localhost:11434/api/show -d "{\"name\": \"${MODEL}\"}" 2>/dev/null \
        | grep -o '"digest":"[^"]*"' | head -1 | cut -d'"' -f4
}

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

    # Optional: check for updates on restart (legacy behavior)
    if [ "$AUTO_UPDATE" = "true" ]; then
        echo "Auto-update enabled — pulling latest ${MODEL}..."
        ollama pull "${MODEL}" || echo "WARNING: update check failed, using cached model."
    fi
else
    echo "Model ${MODEL} not found. Downloading (this may take 15-30 min on first startup)..."
    ollama pull "${MODEL}"
    echo "Model ${MODEL} downloaded successfully."
fi

# ── Background model version check and update ─────────────
# Compares the local model digest with the remote registry digest.
# If a newer version is available, downloads it in the background
# without interrupting the running Ollama server.
# Writes status to /root/.ollama/update-status.json for the backend to read.

check_and_update_model() {
    echo "[LLM Update] Checking for model updates..."

    # Get the local model digest before any pull
    local local_digest
    local_digest=$(get_local_digest)

    if [ -z "$local_digest" ]; then
        echo "[LLM Update] WARNING: Could not retrieve local model digest. Skipping update check."
        write_status "idle" 0 "$MODEL" "" ""
        return
    fi

    echo "[LLM Update] Local digest: ${local_digest:0:16}..."

    # Pull the model to check for updates.
    # Ollama pull is idempotent — if the model is up to date, it returns quickly.
    # We capture output to detect whether a download actually occurred.
    local started_at
    started_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    write_status "downloading" 0 "$MODEL" "$started_at" ""

    # Run ollama pull and capture output + exit code
    local pull_log="/tmp/ollama-pull-update.log"
    ollama pull "${MODEL}" > "$pull_log" 2>&1 &
    local pull_pid=$!

    # Monitor pull progress while it runs
    local progress=0
    while kill -0 "$pull_pid" 2>/dev/null; do
        if [ -f "$pull_log" ]; then
            # Ollama outputs progress lines like "pulling abc123... 45% ▕██░░░░░░░░▏"
            local last_pct
            last_pct=$(grep -oP '\d+(?=%)' "$pull_log" 2>/dev/null | tail -1)
            if [ -n "$last_pct" ]; then
                progress=$last_pct
            fi
        fi
        write_status "downloading" "$progress" "$MODEL" "$started_at" ""
        sleep 5
    done

    # Wait for pull to finish and get exit code
    wait "$pull_pid"
    local pull_exit_code=$?

    if [ $pull_exit_code -ne 0 ]; then
        # Pull failed — write error status and continue with current model
        local error_msg
        error_msg=$(tail -5 "$pull_log" 2>/dev/null | tr '\n' ' ' | sed 's/[[:space:]]*$//')
        echo "[LLM Update] ERROR: Failed to pull model: ${error_msg}"
        write_status "error" 0 "$MODEL" "$started_at" "$error_msg"
        rm -f "$pull_log"
        return
    fi

    # Pull succeeded — check if the digest actually changed
    local new_digest
    new_digest=$(get_local_digest)

    if [ -z "$new_digest" ]; then
        echo "[LLM Update] WARNING: Could not verify new digest after pull."
        write_status "idle" 0 "$MODEL" "" ""
        rm -f "$pull_log"
        return
    fi

    if [ "$local_digest" != "$new_digest" ]; then
        # Digest changed — a new version was downloaded
        echo "[LLM Update] New model version downloaded (${new_digest:0:16}...)."
        echo "[LLM Update] New version will be active on next container restart."
        write_status "ready" 100 "$MODEL" "$started_at" ""
    else
        # Digest unchanged — model is already up to date
        echo "[LLM Update] Model is up to date. No update needed."
        write_status "idle" 0 "$MODEL" "" ""
    fi

    rm -f "$pull_log"
}

# Run the update check in background so it does NOT block the Ollama server
check_and_update_model &

# ── Report available models ───────────────────────────────
echo "Available models:"
ollama list

# Keep the container running by waiting on the Ollama server process
wait $OLLAMA_PID
