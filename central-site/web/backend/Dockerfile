FROM python:3.11-slim

WORKDIR /app

# Token GitHub pour cloner les dépendances privées (passé via --build-arg)
ARG GITHUB_TOKEN=""

# Installer les dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Configurer git pour utiliser le token GitHub (si fourni)
RUN if [ -n "$GITHUB_TOKEN" ]; then \
      git config --global url."https://${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"; \
    fi

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Nettoyer le token de la config git
RUN git config --global --unset-all url."https://${GITHUB_TOKEN}@github.com/".insteadOf 2>/dev/null || true

# Copier le code backend
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
