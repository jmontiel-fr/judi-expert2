# Implementation Plan: Workflow Dossier Refactor

## Overview

Refactoring du workflow d'expertise Judi-Expert : renommage des étapes (App Locale + Site Central), refonte Step 2 (upload NEA → RE-Projet + RE-Projet-Auxiliaire), refonte Step 3 (NEA → REF-Projet), fermeture de dossier avec archive ZIP, affichage enrichi des fichiers par étape, prévisualisation/téléchargement/remplacement de fichiers individuels.

L'implémentation suit un ordre backend-first (constantes, modèles, services, routes) puis frontend, avec tests property-based intercalés.

## Tasks

- [x] 1. Renommage des étapes et constantes backend
  - [x] 1.1 Update STEP_NAMES in the Dossier_Page frontend
    - In `local-site/web/frontend/src/app/dossier/[id]/page.tsx`, update the `STEP_NAMES` constant: Step 0 = "Extraction", Step 1 = "Préparation entretien", Step 2 = "Mise en forme RE-Projet", Step 3 = "Génération rapport expertise"
    - _Requirements: 1.1, 1.2_
  - [x] 1.2 Update step labels in the Step_Page frontend
    - In `local-site/web/frontend/src/app/dossier/[id]/step/[n]/page.tsx`, update any STEP_NAMES or step label references to use the new names
    - _Requirements: 1.1, 1.3_
  - [x] 1.3 Add DOSSIER_FERME constant to WorkflowEngine
    - In `local-site/web/backend/services/workflow_engine.py`, add `DOSSIER_FERME = "fermé"` alongside existing `DOSSIER_ACTIF` and `DOSSIER_ARCHIVE` constants
    - Update `validate_step` for step 3: remove the automatic archiving (`dossier.statut = DOSSIER_ARCHIVE`) — the expert must now explicitly close the dossier
    - Update `execute_step` and `validate_step` to also reject operations when `dossier.statut == DOSSIER_FERME` with message "Le dossier est fermé, aucune modification n'est possible"
    - _Requirements: 5.5, 5.6_

- [x] 2. Renommage des étapes sur le Site Central
  - [x] 2.1 Update workflow section on Site Central homepage
    - In `central-site/web/frontend/src/app/page.tsx`, update the "Workflow d'expertise" section:
      - Step 2 title: "Mise en forme RE-Projet", description: "Upload du NEA (Notes d'Entretien et Analyse) et production du RE-Projet et RE-Projet-Auxiliaire par l'IA"
      - Step 3 title: "Génération rapport expertise", description: "Génération du REF-Projet (rapport d'expertise final) à partir du NEA"
    - _Requirements: 2.1, 2.2_

- [x] 3. Checkpoint — Vérifier le renommage
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Refonte du Step 2 backend — Mise en forme RE-Projet
  - [x] 4.1 Add LLM service methods for Step 2
    - In `local-site/web/backend/services/llm_service.py`, add methods to `LLMService`:
      - `async def generer_re_projet(self, nea_content: str, requisition_md: str, template: str) -> str` — generates RE-Projet from NEA, requisition markdown, and report template
      - `async def generer_re_projet_auxiliaire(self, nea_content: str, re_projet: str) -> str` — generates RE-Projet-Auxiliaire from NEA and RE-Projet
    - _Requirements: 3.4, 3.5_
  - [x] 4.2 Refactor Step 2 upload endpoint
    - In `local-site/web/backend/routers/steps.py`, rewrite `step2_upload`:
      - Accept a single .docx file (NEA), validate extension with HTTP 400 "Seul le format .docx est accepté" if not .docx
      - Save as `nea.docx` in `data/dossiers/{id}/step2/`
      - Call `llm_service.generer_re_projet()` with NEA content, requisition markdown from step0, and report template from RAG
      - Call `llm_service.generer_re_projet_auxiliaire()` with NEA content and RE-Projet
      - Save `re_projet.docx` and `re_projet_auxiliaire.docx` in `data/dossiers/{id}/step2/`
      - Create 3 StepFile entries: nea (type "nea"), re_projet (type "re_projet"), re_projet_auxiliaire (type "re_projet_auxiliaire")
      - Update `Step2UploadResponse` schema to return `filenames: list[str]`
      - Call `workflow_engine.execute_step(dossier_id, 2, db)` to mark step as "réalisé"
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_
  - [x] 4.3 Write property test for upload file extension validation
    - **Property 1: Upload file extension validation**
    - Test with Hypothesis: generate random filenames, assert only `.docx` (case-insensitive) is accepted, all others rejected with HTTP 400
    - File: `tests/property/test_prop_step2_validation.py`
    - **Validates: Requirements 3.1, 3.2**
  - [x] 4.4 Write property test for Step 2 execution post-conditions
    - **Property 2: Step 2 execution post-conditions**
    - Test with Hypothesis: after valid Step 2 execution, verify exactly 3 files on disk, exactly 3 StepFile records with correct file_types, step statut = "réalisé"
    - File: `tests/property/test_prop_step2_execution.py`
    - **Validates: Requirements 3.3, 3.6, 3.7, 3.8**

- [x] 5. Refonte du Step 3 backend — Génération rapport expertise
  - [x] 5.1 Add LLM service method for Step 3
    - In `local-site/web/backend/services/llm_service.py`, add method to `LLMService`:
      - `async def generer_ref_projet(self, nea_content: str, requisition_md: str, template: str) -> str` — generates REF-Projet from NEA
    - _Requirements: 4.3_
  - [x] 5.2 Refactor Step 3 execute endpoint
    - In `local-site/web/backend/routers/steps.py`, rewrite `step3_execute`:
      - Read `nea.docx` from `data/dossiers/{id}/step2/`, return HTTP 404 "Fichier NEA non trouvé — complétez d'abord le Step 2" if missing
      - Call `llm_service.generer_ref_projet()` with NEA content, requisition markdown from step0, and report template from RAG
      - Save `ref_projet.docx` in `data/dossiers/{id}/step3/`
      - Create 1 StepFile entry: ref_projet (type "ref_projet")
      - Update `Step3ExecuteResponse` schema to return `filenames: list[str]`
      - Call `workflow_engine.execute_step(dossier_id, 3, db)` to mark step as "réalisé"
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  - [x] 5.3 Write property test for Step 3 execution post-conditions
    - **Property 3: Step 3 execution post-conditions**
    - Test with Hypothesis: after valid Step 3 execution (NEA exists in step2/), verify `ref_projet.docx` on disk, exactly 1 StepFile record with file_type "ref_projet", step statut = "réalisé"
    - File: `tests/property/test_prop_step3_execution.py`
    - **Validates: Requirements 4.4, 4.5, 4.6**

- [x] 6. Checkpoint — Vérifier Step 2 et Step 3
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Fermeture de dossier et archive ZIP
  - [x] 7.1 Add close_dossier method to WorkflowEngine
    - In `local-site/web/backend/services/workflow_engine.py`, add `async def close_dossier(self, dossier_id: int, db: AsyncSession) -> Dossier`:
      - Verify all 4 steps have statut "validé", raise HTTP 403 "Toutes les étapes doivent être validées pour fermer le dossier" otherwise
      - Set `dossier.statut = DOSSIER_FERME`
    - Add helper methods `is_dossier_closed(dossier)` and `is_dossier_modifiable(dossier)`
    - _Requirements: 5.3, 5.4, 5.5_
  - [x] 7.2 Add close and download endpoints to dossiers router
    - In `local-site/web/backend/routers/dossiers.py`, add:
      - `POST /api/dossiers/{id}/close` — calls `workflow_engine.close_dossier()`, returns `DossierCloseResponse`
      - `GET /api/dossiers/{id}/download` — generates ZIP archive of all step directories, returns as `application/zip` with filename `dossier_{id}_archive.zip`
      - Verify dossier statut is "fermé" before allowing download, return HTTP 403 "Le dossier doit être fermé pour télécharger l'archive" otherwise
      - ZIP must preserve step directory structure (e.g., `step0/requisition.pdf`, `step2/nea.docx`)
    - Add Pydantic schemas: `DossierCloseResponse`, `FileDownloadInfo`
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5_
  - [x] 7.3 Write property test for close dossier precondition/postcondition
    - **Property 4: Close dossier precondition and postcondition**
    - Test with Hypothesis: generate all combinations of step statuses, assert close succeeds iff all 4 are "validé", dossier statut becomes "fermé" on success, unchanged on failure with HTTP 403
    - File: `tests/property/test_prop_close_dossier.py`
    - **Validates: Requirements 5.3, 5.4, 5.5**
  - [x] 7.4 Write property test for closed dossier blocks modifications
    - **Property 5: Closed dossier blocks all modifications**
    - Test with Hypothesis: for any dossier with statut "fermé", assert all modification operations (execute_step, validate_step, file replace, step upload) are rejected with HTTP 403
    - File: `tests/property/test_prop_close_dossier.py`
    - **Validates: Requirements 5.6, 9.6**
  - [x] 7.5 Write property tests for ZIP archive
    - **Property 6: ZIP archive completeness and structure**
    - Test with Hypothesis: generate random files in step directories, assert ZIP contains every file with paths matching `step{n}/{filename}`
    - **Property 7: ZIP download requires fermé status**
    - Test with Hypothesis: for any dossier with statut != "fermé", assert download returns HTTP 403
    - File: `tests/property/test_prop_zip_archive.py`
    - **Validates: Requirements 6.2, 6.3, 6.4**

- [x] 8. Endpoints fichiers individuels (download, preview, replace)
  - [x] 8.1 Add file download and preview endpoints
    - In `local-site/web/backend/routers/dossiers.py`, add:
      - `GET /api/dossiers/{id}/files/{file_id}/download` — returns file content as download response
      - `GET /api/dossiers/{id}/files/{file_id}/preview` — returns file content for inline display (Markdown/PDF inline, .docx triggers download)
    - Return HTTP 404 "Fichier non trouvé" if file does not exist
    - _Requirements: 8.1, 8.3_
  - [x] 8.2 Add file replace endpoint
    - In `local-site/web/backend/routers/dossiers.py`, add:
      - `PUT /api/dossiers/{id}/files/{file_id}/replace` — overwrites original file on disk, updates StepFile.file_size in DB
      - Return HTTP 403 "Étape verrouillée, modification impossible" if step statut is "validé"
      - Return HTTP 403 "Le dossier est fermé, aucune modification n'est possible" if dossier statut is "fermé"
    - Add Pydantic schema: `FileReplaceResponse`
    - _Requirements: 9.2, 9.3, 9.4, 9.5, 9.6_
  - [x] 8.3 Write property test for file replacement round-trip
    - **Property 9: File replacement round-trip**
    - Test with Hypothesis: generate random file content, replace via endpoint, assert file on disk matches new content and StepFile.file_size matches actual file size
    - File: `tests/property/test_prop_file_replace.py`
    - **Validates: Requirements 9.3, 9.4**
  - [x] 8.4 Write property test for validated step blocks replacement
    - **Property 10: Validated step blocks file replacement**
    - Test with Hypothesis: for any step with statut "validé", assert file replacement is rejected with HTTP 403 and original file unchanged
    - File: `tests/property/test_prop_file_replace.py`
    - **Validates: Requirements 9.5**

- [x] 9. Checkpoint — Vérifier les endpoints backend
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Frontend — Affichage des fichiers et fermeture de dossier
  - [x] 10.1 Add file size formatting utility
    - In `local-site/web/frontend/src/lib/api.ts`, add a `formatFileSize(bytes: number): string` function that formats file sizes in human-readable units (octets, Ko, Mo, Go)
    - _Requirements: 7.2_
  - [x] 10.2 Write property test for file size formatting
    - **Property 8: File size formatting**
    - Test with Hypothesis (Python-side utility mirror): for any non-negative integer, formatting produces correct unit and round-trip value within rounding tolerance
    - File: `tests/property/test_prop_file_formatting.py`
    - **Validates: Requirements 7.2**
  - [x] 10.3 Update Dossier_Page to display StepFile list per step
    - In `local-site/web/frontend/src/app/dossier/[id]/page.tsx`:
      - Fetch StepFile entries for each step from the existing `get_step_detail` endpoint
      - Display filename, file type (input/output), and formatted file size for each file
      - Display "Aucun fichier pour cette étape" when no files exist
    - Update `local-site/web/frontend/src/lib/api.ts` to add API calls for file list if needed
    - _Requirements: 7.1, 7.2, 7.3_
  - [x] 10.4 Add "Fermer le dossier" and "Télécharger le dossier" buttons
    - In `local-site/web/frontend/src/app/dossier/[id]/page.tsx`:
      - Show "Fermer le dossier" button when all 4 steps have statut "validé" and dossier statut is "actif"
      - On click, POST to `/api/dossiers/{id}/close`, refresh dossier state
      - Show "Télécharger le dossier" button when dossier statut is "fermé"
      - On click, GET `/api/dossiers/{id}/download` and trigger file download
      - Add "fermé" badge display alongside existing "actif"/"archivé" badges
      - Display dossier in read-only mode when statut is "fermé" (disable step navigation links)
    - _Requirements: 5.1, 5.2, 5.6, 5.7, 6.1_

- [x] 11. Frontend — Step pages (Step 2, Step 3, fichiers)
  - [x] 11.1 Refactor Step 2 view for single NEA upload
    - In `local-site/web/frontend/src/app/dossier/[id]/step/[n]/page.tsx`, update `Step2View`:
      - Single file upload form accepting only .docx files
      - Upload to `POST /api/dossiers/{id}/step2/upload`
      - Display loading state during LLM generation
      - Show the 3 output files (nea.docx, re_projet.docx, re_projet_auxiliaire.docx) after completion
    - _Requirements: 3.1, 3.2_
  - [x] 11.2 Refactor Step 3 view for NEA-based generation
    - In `local-site/web/frontend/src/app/dossier/[id]/step/[n]/page.tsx`, update `Step3View`:
      - "Lancer la génération" button that calls `POST /api/dossiers/{id}/step3/execute`
      - Display loading state during LLM generation
      - Show the output file (ref_projet.docx) after completion
      - Display error message if NEA not found (HTTP 404)
    - _Requirements: 4.1, 4.2_
  - [x] 11.3 Add preview, download, and replace buttons per file
    - In `local-site/web/frontend/src/app/dossier/[id]/step/[n]/page.tsx`:
      - For each StepFile displayed, add download button (calls `GET /api/dossiers/{id}/files/{file_id}/download`)
      - Add preview button: Markdown → modal/inline viewer, PDF → new tab, .docx → triggers download
      - Add "Upload version modifiée" button when step.statut = "réalisé" and dossier.statut = "actif"
      - On replace, PUT to `/api/dossiers/{id}/files/{file_id}/replace`
      - Display error messages for HTTP 403 (locked step or closed dossier)
    - _Requirements: 8.2, 8.4, 8.5, 8.6, 9.1, 9.2, 9.5, 9.6_

- [x] 12. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (Properties 1–10)
- Unit tests validate specific examples and edge cases
- LLM service is mocked in all tests except integration
- Backend uses Python (FastAPI + SQLAlchemy), frontend uses TypeScript (Next.js 14)
