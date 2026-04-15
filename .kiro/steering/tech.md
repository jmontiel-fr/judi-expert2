# Judi-Expert — Tech Stack & Commands

## Backend (Python)

- **Framework**: FastAPI 0.115.x + Uvicorn
- **ORM**: SQLAlchemy 2.0 (Mapped types) + Alembic migrations
- **Local DB**: SQLite (via aiosqlite)
- **Central DB**: PostgreSQL (via asyncpg / psycopg2-binary)
- **Auth (local)**: passlib (bcrypt) + python-jose (JWT, HS256)
- **Auth (central)**: AWS Cognito + python-jose
- **Payments**: Stripe SDK 11.x
- **HTTP client**: httpx
- **Doc generation**: docxtpl (Jinja2 templates for .docx)
- **OCR**: pytesseract + pdf2image + PyMuPDF
- **RAG**: Qdrant client + FastEmbed (sentence-transformers/all-MiniLM-L6-v2)
- **LLM runtime**: Ollama (Mistral 7B Instruct v0.3)
- **AWS SDK**: boto3

## Frontend (TypeScript)

- **Framework**: Next.js 14 (App Router) + React 18
- **HTTP client**: axios
- **AWS auth (central only)**: aws-amplify 6.x
- **Payments (central only)**: @stripe/stripe-js
- **Style**: functional components with hooks, no class components

## Infrastructure

- **Containerization**: Docker + Docker Compose (local), ECS Fargate + ECR (AWS)
- **IaC**: Terraform
- **AWS services**: ECS, RDS, Cognito, S3, ECR, CloudFront, ALB, EventBridge, Lambda, SES, CloudWatch, Route 53, Secrets Manager

## Python Conventions

- PEP 8, formatted with `black` (88 char line), imports sorted with `isort`
- Type annotations required, checked with `mypy`
- Google-style docstrings for public functions
- Naming: `snake_case` (vars/functions), `PascalCase` (classes), `UPPER_SNAKE_CASE` (constants)

## TypeScript Conventions

- ESLint (Next.js config) + Prettier
- Naming: `camelCase` (vars/functions), `PascalCase` (components/files)

## Git Conventions

- Commit format: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- Messages in French or English

## Testing

- **Framework**: pytest
- **Property-based testing**: Hypothesis (tests in `tests/property/`)
- **Test categories**: unit, property, integration, smoke

### Common Commands

```bash
# --- Application Locale (Docker) ---
cd local-site
./scripts/build.sh          # Build Docker images
./scripts/start.sh          # Start containers
./scripts/stop.sh           # Stop containers
./scripts/restart.sh        # Restart containers
# App available at http://localhost:3000 (web), http://localhost:8000 (api)

# --- Site Central (Docker Compose dev) ---
docker compose -f central-site/docker-compose.dev.yml up -d --build
# Available at http://localhost:3001

# --- Tests ---
pytest tests/unit/ -v                  # Unit tests
pytest tests/property/ -v              # Property-based tests (Hypothesis)
pytest tests/integration/ -v           # Integration tests
pytest tests/smoke/ -v                 # Smoke tests

# --- Linting / Formatting (Python) ---
black local-site/ central-site/
isort local-site/ central-site/
flake8 local-site/ central-site/
mypy local-site/ central-site/

# --- Linting (Frontend) ---
cd local-site/web/frontend && npx eslint src/
cd central-site/web/frontend && npx eslint src/

# --- DB Migrations ---
cd local-site/web/backend && alembic upgrade head
cd central-site/web/backend && alembic upgrade head
# New migration: alembic revision --autogenerate -m "description"

# --- AWS Deployment ---
cd central-site/scripts
./build.sh && ./push-ecr.sh && ./deploy.sh

# --- Packaging installer (.exe) ---
bash central-site/app_locale_package/package.sh windows
```
