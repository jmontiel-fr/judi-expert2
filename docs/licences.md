# Inventaire des Dépendances et Licences

**Judi-Expert — ITechSource**
**Dernière mise à jour : 1er janvier 2026**

Ce document recense l'ensemble des dépendances utilisées dans le projet Judi-Expert, conformément à l'Exigence 27 (conformité open-source et gratuité des composants). Tous les composants listés sont sous licence open-source ou gratuite compatible avec un usage commercial.

---

## Backend Python — Application Locale

| Nom | Version | Licence | URL |
|---|---|---|---|
| FastAPI | 0.115.6 | MIT | https://github.com/tiangolo/fastapi |
| Uvicorn | 0.34.0 | BSD-3-Clause | https://github.com/encode/uvicorn |
| SQLAlchemy | 2.0.36 | MIT | https://github.com/sqlalchemy/sqlalchemy |
| Alembic | 1.14.1 | MIT | https://github.com/sqlalchemy/alembic |
| python-docx | 1.1.2 | MIT | https://github.com/python-openxml/python-docx |
| docxtpl | 0.18.0 | LGPL-2.1 | https://github.com/elapouya/python-docx-template |
| pytesseract | 0.3.13 | Apache-2.0 | https://github.com/madmaze/pytesseract |
| qdrant-client | 1.12.1 | Apache-2.0 | https://github.com/qdrant/qdrant-client |
| FastEmbed | 0.4.2 | Apache-2.0 | https://github.com/qdrant/fastembed |
| httpx | 0.28.1 | BSD-3-Clause | https://github.com/encode/httpx |
| passlib | 1.7.4 | BSD-3-Clause | https://github.com/gvalkov/passlib |
| python-jose | 3.3.0 | MIT | https://github.com/mpdavis/python-jose |
| aiosqlite | 0.20.0 | MIT | https://github.com/omnilib/aiosqlite |

## Backend Python — Service OCR (judi-ocr)

| Nom | Version | Licence | URL |
|---|---|---|---|
| FastAPI | 0.115.6 | MIT | https://github.com/tiangolo/fastapi |
| Uvicorn | 0.34.0 | BSD-3-Clause | https://github.com/encode/uvicorn |
| pytesseract | 0.3.13 | Apache-2.0 | https://github.com/madmaze/pytesseract |
| pdf2image | 1.17.0 | MIT | https://github.com/Belval/pdf2image |
| PyMuPDF | 1.24.14 | AGPL-3.0 / Commercial | https://github.com/pymupdf/PyMuPDF |
| Pillow | 11.1.0 | HPND (Historical Permission Notice and Disclaimer) | https://github.com/python-pillow/Pillow |
| python-multipart | 0.0.18 | Apache-2.0 | https://github.com/andrew-d/python-multipart |

## Backend Python — Site Central

| Nom | Version | Licence | URL |
|---|---|---|---|
| FastAPI | 0.115.6 | MIT | https://github.com/tiangolo/fastapi |
| Uvicorn | 0.34.0 | BSD-3-Clause | https://github.com/encode/uvicorn |
| SQLAlchemy | 2.0.36 | MIT | https://github.com/sqlalchemy/sqlalchemy |
| Alembic | 1.14.1 | MIT | https://github.com/sqlalchemy/alembic |
| Stripe (Python) | 11.4.1 | MIT | https://github.com/stripe/stripe-python |
| boto3 | 1.35.81 | Apache-2.0 | https://github.com/boto/boto3 |
| httpx | 0.28.1 | BSD-3-Clause | https://github.com/encode/httpx |
| psycopg2-binary | 2.9.10 | LGPL-3.0 | https://github.com/psycopg/psycopg2 |
| asyncpg | 0.30.0 | Apache-2.0 | https://github.com/MagicStack/asyncpg |
| python-jose | 3.3.0 | MIT | https://github.com/mpdavis/python-jose |
| Pydantic | 2.10.3 | MIT | https://github.com/pydantic/pydantic |

## Frontend Node.js — Application Locale

| Nom | Version | Licence | URL |
|---|---|---|---|
| Next.js | ^14.2.21 | MIT | https://github.com/vercel/next.js |
| React | ^18.3.1 | MIT | https://github.com/facebook/react |
| React DOM | ^18.3.1 | MIT | https://github.com/facebook/react |
| Axios | ^1.7.9 | MIT | https://github.com/axios/axios |
| TypeScript | ^5.7.3 | Apache-2.0 | https://github.com/microsoft/TypeScript |

## Frontend Node.js — Site Central

| Nom | Version | Licence | URL |
|---|---|---|---|
| Next.js | ^14.2.21 | MIT | https://github.com/vercel/next.js |
| React | ^18.3.1 | MIT | https://github.com/facebook/react |
| React DOM | ^18.3.1 | MIT | https://github.com/facebook/react |
| Axios | ^1.7.9 | MIT | https://github.com/axios/axios |
| AWS Amplify | ^6.3.8 | Apache-2.0 | https://github.com/aws-amplify/amplify-js |
| @stripe/stripe-js | ^4.1.0 | MIT | https://github.com/stripe/stripe-js |
| TypeScript | ^5.7.3 | Apache-2.0 | https://github.com/microsoft/TypeScript |

## Infrastructure et outils système

| Nom | Version | Licence | URL |
|---|---|---|---|
| Docker | — | Apache-2.0 | https://github.com/moby/moby |
| Docker Compose | — | Apache-2.0 | https://github.com/docker/compose |
| Terraform | — | BSL 1.1 (gratuit pour usage commercial) | https://github.com/hashicorp/terraform |
| Ollama | — | MIT | https://github.com/ollama/ollama |
| Qdrant | — | Apache-2.0 | https://github.com/qdrant/qdrant |
| Tesseract OCR | — | Apache-2.0 | https://github.com/tesseract-ocr/tesseract |
| Poppler | — | GPL-2.0 | https://poppler.freedesktop.org/ |

## Modèle LLM

| Nom | Version | Licence | URL |
|---|---|---|---|
| Mistral 7B Instruct | v0.3 | Apache-2.0 | https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3 |

## Tests

| Nom | Version | Licence | URL |
|---|---|---|---|
| pytest | — | MIT | https://github.com/pytest-dev/pytest |
| Hypothesis | — | MPL-2.0 | https://github.com/HypothesisWorks/hypothesis |
| pytest-asyncio | — | Apache-2.0 | https://github.com/pytest-dev/pytest-asyncio |

---

## Notes sur les licences

- **MIT, BSD-3-Clause, Apache-2.0** : licences permissives, pleinement compatibles avec un usage commercial.
- **LGPL-2.1 (docxtpl), LGPL-3.0 (psycopg2-binary)** : licences copyleft faibles, compatibles avec un usage commercial tant que la bibliothèque est utilisée en tant que dépendance (non modifiée et non intégrée statiquement).
- **AGPL-3.0 (PyMuPDF)** : licence copyleft forte. PyMuPDF est utilisé comme service isolé dans le conteneur OCR. Une licence commerciale est disponible si nécessaire.
- **MPL-2.0 (Hypothesis)** : licence copyleft faible, compatible avec un usage commercial. Utilisée uniquement pour les tests.
- **BSL 1.1 (Terraform)** : Business Source License, gratuit pour un usage non concurrent avec les produits HashiCorp.
- **GPL-2.0 (Poppler)** : utilisé comme outil système dans le conteneur OCR, non lié au code applicatif.
- **HPND (Pillow)** : licence permissive historique, compatible avec un usage commercial.

Conformément à l'Exigence 27, tous les composants utilisés sont sous licence open-source ou gratuite compatible avec un usage commercial.
