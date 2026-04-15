# Judi-Expert — Product Overview

Judi-Expert is an AI-assisted platform for French judicial experts (experts judiciaires). It automates repetitive tasks in the expertise process while keeping the expert in full control of conclusions and reports.

## Two-Component Architecture

- **Application Locale**: Desktop app (Docker Compose, 4 containers) installed on the expert's PC. Handles the full expertise workflow — OCR extraction, interview plan generation, document collection, and report generation. All case data stays local (GDPR/AI Act compliant).
- **Site Central**: AWS-hosted web platform managing expert registration, ticket-based payments (Stripe), RAG corpus distribution, and administration.

## Expertise Workflow (4 Steps)

| Step | Name | What Happens |
|------|------|-------------|
| Step0 | Extraction | OCR scan → structured Markdown |
| Step1 | PEMEC | Generate interview plan from court questions |
| Step2 | Upload | Expert uploads interview notes + raw report |
| Step3 | REF + RAUX | Generate final report + contestation analysis |

At every step the expert reviews, edits, and validates AI output before proceeding.

## Domain System

Five expertise domains defined in `domaines/domaines.yaml`: psychologie (active), psychiatrie, médecine légale, bâtiment, comptabilité. Each domain has its own RAG corpus under `corpus/{domaine}/`.

## Key Constraints

- All expertise data must remain on the expert's PC — never transmitted to the cloud
- Only tickets transit between local app and Site Central
- The LLM (Mistral 7B via Ollama) runs entirely locally, no internet required for inference
- Disk encryption (BitLocker/FileVault) is mandatory
- Documentation and UI are in French
