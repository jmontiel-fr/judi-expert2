#!/bin/bash
# Judi-Expert — Ollama Entrypoint Script
# Starts the Ollama server and automatically pulls the Mistral 7B model
# if it is not already present (first startup).

set -e

# Start Ollama server in the background
ollama serve &

# Wait for the Ollama server to be ready
echo "Waiting for Ollama server to start..."
until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
    sleep 1
done
echo "Ollama server is ready."

# Pull the Mistral model if not already downloaded
MODEL="mistral:7b-instruct-v0.3"
if ! ollama list | grep -q "mistral"; then
    echo "Downloading model ${MODEL} (first startup, this may take a while)..."
    ollama pull "${MODEL}"
    echo "Model ${MODEL} downloaded successfully."
else
    echo "Model ${MODEL} is already available."
fi

# Keep the container running by waiting on the Ollama server process
wait
