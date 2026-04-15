# Judi-Expert — Project Structure

```
judi-expert/
├── local-site/                         # Application Locale (expert's PC)
│   ├── docker-compose.yml              # Orchestrates 4 containers
│   ├── .env                            # Local env vars (DB, service URLs, JWT)
│   ├── ollama-entrypoint.sh            # LLM auto-download script
│   ├── scripts/                        # build.sh, start.sh, stop.sh, restart.sh, prerequisites.py
│   ├── ocr/                            # judi-ocr container (Tesseract + pdf2image)
│   │   ├── main.py                     # FastAPI OCR service
│   │   └── Dockerfile
│   └── web/
│       ├── backend/                    # judi-web backend (FastAPI + SQLite)
│       │   ├── main.py                 # App entrypoint
│       │   ├── database.py             # SQLAlchemy engine + session
│       │   ├── models/                 # SQLAlchemy models (dossier, step, step_file, chat_message, local_config)
│       │   ├── routers/                # API routes (auth, dossiers, steps, chatbot, config, tickets)
│       │   ├── services/               # Business logic (llm_service, rag_service, workflow_engine, site_central_client)
│       │   ├── middleware/             # data_isolation middleware
│       │   └── alembic/                # DB migrations
│       └── frontend/                   # judi-web frontend (Next.js PWA)
│           └── src/
│               ├── app/                # Next.js App Router pages
│               ├── components/         # React components
│               └── lib/                # Utilities
│
├── central-site/                       # Site Central (AWS)
│   ├── docker-compose.dev.yml          # Dev compose for Site Central
│   ├── .env                            # AWS env vars (Cognito, Stripe, DB)
│   ├── terraform/                      # IaC (main.tf, variables.tf, outputs.tf, modules/)
│   ├── scripts/                        # build.sh, push-ecr.sh, deploy.sh, update-rag.sh, site-start/stop/status.sh
│   ├── app_locale_package/             # Installer packaging (NSIS for Windows, shell for Unix)
│   └── web/
│       ├── backend/                    # FastAPI + PostgreSQL
│       │   ├── main.py
│       │   ├── database.py
│       │   ├── models/                 # SQLAlchemy models (expert, ticket, domaine, corpus_version, contact_message)
│       │   ├── routers/                # API routes (auth, admin, tickets, corpus, profile, contact, downloads, webhooks)
│       │   ├── schemas/                # Pydantic schemas (auth, admin, tickets, corpus, profile, contact)
│       │   ├── services/               # Business logic (cognito, stripe, domaines, email, captcha)
│       │   └── alembic/                # DB migrations
│       └── frontend/                   # Next.js PWA
│           └── src/
│               ├── app/
│               ├── components/
│               ├── contexts/           # React contexts (auth via Amplify)
│               └── lib/
│
├── corpus/                             # RAG corpus per domain
│   ├── psychologie/                    # Active domain — documents/, urls/, contenu.yaml, TPE template, docx template
│   ├── psychiatrie/
│   ├── medecine_legale/
│   ├── batiment/
│   └── comptabilite/
│
├── domaines/
│   └── domaines.yaml                   # Domain registry (5 domains, only psychologie active)
│
├── prompts/
│   └── prompt1                         # LLM prompt templates
│
├── tests/                              # All tests (run from repo root with pytest)
│   ├── unit/                           # Unit tests (test_*.py per router/service/model)
│   ├── property/                       # Property-based tests (Hypothesis, test_prop_*.py)
│   ├── integration/                    # Integration tests (Docker, Stripe, e2e workflow)
│   └── smoke/                          # Smoke tests
│
└── docs/                               # Project documentation (French, Markdown)
    ├── architecture.md                 # Full system architecture
    ├── developpement.md                # Dev setup, conventions, commands
    ├── exploitation.md                 # Operations guide
    ├── methodologie.md                 # Legal/regulatory methodology
    ├── user-guide.md                   # End-user guide
    └── ...                             # CGU, mentions légales, FAQ, licences, Stripe, costs
```

## Key Patterns

- **Mirrored structure**: `local-site/web/` and `central-site/web/` share the same layout (backend with models/routers/services, frontend with src/app/components)
- **Backend layering**: `routers/` → `services/` → `models/` (routes call services, services use models)
- **AWS backend adds `schemas/`**: Pydantic request/response schemas separate from models
- **Local backend adds `middleware/`**: Data isolation middleware for multi-tenant safety
- **One model per file**: Each SQLAlchemy model lives in its own file under `models/`
- **One router per domain**: Each API domain (auth, dossiers, tickets, etc.) has its own router file
- **Tests mirror source**: Unit test files map to source files (e.g., `test_workflow_engine.py` → `services/workflow_engine.py`)
- **Property tests**: Named `test_prop_*.py`, use Hypothesis for invariant checking
