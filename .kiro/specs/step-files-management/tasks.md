# Implementation Plan: Gestion des Fichiers par Étape

## Overview

Implémentation incrémentale de la gestion unifiée des fichiers par étape : extension du modèle StepFile, création du service fichier et du router API, puis intégration du composant frontend FileList dans les pages Dossier et Étape. Chaque tâche construit sur la précédente et se termine par un câblage complet backend → frontend.

## Tasks

- [x] 1. Extend StepFile model and create Alembic migration
  - [x] 1.1 Add versioning fields to StepFile model
    - Add `is_modified: Mapped[bool]` (default=False), `original_file_path: Mapped[Optional[str]]` (nullable), and `updated_at: Mapped[Optional[datetime]]` (nullable) to `local-site/web/backend/models/step_file.py`
    - Import `Optional` from typing and add necessary SQLAlchemy imports
    - _Requirements: 6.1, 6.2_
  - [x] 1.2 Create Alembic migration for new fields
    - Run `alembic revision --autogenerate -m "add_step_file_versioning_fields"` in `local-site/web/backend`
    - Migration adds columns `is_modified` (Boolean, server_default="0"), `original_file_path` (String(500), nullable), `updated_at` (DateTime, nullable) to `step_files` table
    - _Requirements: 6.1, 6.2_
  - [x] 1.3 Update StepFileItem schema in dossiers.py and api.ts
    - Add `is_modified: bool`, `original_file_path: str | None`, `updated_at: datetime | None` to `StepFileItem` Pydantic model in `local-site/web/backend/routers/dossiers.py`
    - Add `is_modified: boolean`, `original_file_path: string | null`, `updated_at: string | null` to `StepFileItem` TypeScript interface in `local-site/web/frontend/src/lib/api.ts`
    - _Requirements: 6.1, 6.2, 6.4_

- [x] 2. Implement FileService backend service
  - [x] 2.1 Create `file_service.py` in `local-site/web/backend/services/`
    - Implement `FileService` class with three methods:
    - `format_file_size(size_bytes: int) -> str` — formats bytes to human-readable units (o, Ko, Mo, Go), value between 0 and 1024 for non-terminal units
    - `get_content_type(filename: str) -> str` — returns MIME type for known extensions (.md, .pdf, .docx, .zip) or `application/octet-stream` for unknown
    - `replace_file(step_file: StepFile, new_content: bytes, step_dir: str) -> None` — renames original to `{name}_original.{ext}` (if not already done), writes new content under original name, updates StepFile fields (`is_modified`, `original_file_path`, `file_size`, `updated_at`)
    - _Requirements: 1.2, 3.3, 4.2, 4.3, 4.4_
  - [x] 2.2 Write property test for file size formatting (Property 1)
    - **Property 1: File size formatting produces valid human-readable output**
    - Create `tests/property/test_prop_file_size_formatting.py`
    - Use Hypothesis to generate non-negative integers (0 to 10 Go), verify output contains numeric value + valid unit from {o, Ko, Mo, Go}, numeric value < 1024 for non-terminal units
    - **Validates: Requirements 1.2**
  - [x] 2.3 Write property test for content-type mapping (Property 2)
    - **Property 2: Content-Type mapping is correct for known extensions**
    - Create `tests/property/test_prop_content_type_mapping.py`
    - Use Hypothesis to generate filenames with known extensions (.md, .pdf, .docx, .zip) and unknown extensions, verify correct MIME type returned
    - **Validates: Requirements 3.3**

- [x] 3. Implement step_files API router
  - [x] 3.1 Create `step_files.py` router in `local-site/web/backend/routers/`
    - Define Pydantic schemas: `StepFileResponse` and `StepFileReplaceResponse`
    - Create router with prefix `/{dossier_id}/steps/{step_number}/files`
    - Implement `GET /{file_id}/download` — query StepFile by id, verify file exists on disk, return `FileResponse` with `Content-Disposition: attachment; filename="{filename}"` and correct Content-Type
    - Implement `GET /{file_id}/view` — same as download but with `Content-Disposition: inline`
    - Implement `POST /{file_id}/replace` — accept `UploadFile`, validate step not locked via `workflow_engine.require_step_not_validated()`, validate extension matches original, validate file not empty, call `FileService.replace_file()`, update DB, return `StepFileReplaceResponse`
    - Handle all error cases from the design (404 file not found, 403 locked step, 400 extension mismatch, 400 empty file)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 2.5_
  - [x] 3.2 Register step_files router in main.py
    - Import `step_files` router in `local-site/web/backend/main.py`
    - Mount with `app.include_router(step_files.router, prefix="/api/dossiers", tags=["step_files"])`
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 4. Checkpoint — Backend API complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Add resolve_file_path to WorkflowEngine
  - [x] 5.1 Implement `resolve_file_path` method in WorkflowEngine
    - Add `async def resolve_file_path(self, dossier_id: int, step_number: int, filename: str, db: AsyncSession) -> str` to `local-site/web/backend/services/workflow_engine.py`
    - Query StepFile by step and filename, return `step_file.file_path` (which always points to the active file — modified or original)
    - Raise 404 if StepFile not found
    - _Requirements: 5.1, 5.2, 5.3_
  - [x] 5.2 Write property test for file replacement round-trip (Property 3)
    - **Property 3: File replacement round-trip preserves original and updates record**
    - Create `tests/property/test_prop_file_replacement.py`
    - Use Hypothesis to generate valid file content and matching extensions, verify after replace: original file exists with `_original` suffix, new file exists under original name, StepFile has `is_modified=True`, correct `file_size`, and valid `original_file_path`
    - **Validates: Requirements 4.2, 4.3, 4.4**
  - [x] 5.3 Write property test for extension mismatch rejection (Property 4)
    - **Property 4: Extension mismatch rejection**
    - Add to `tests/property/test_prop_file_replacement.py`
    - Use Hypothesis to generate StepFile with extension E1 and upload with E2 where E1 ≠ E2, verify HTTP 400 returned and StepFile + disk unchanged
    - **Validates: Requirements 4.6**
  - [x] 5.4 Write property test for active file path resolution (Property 5)
    - **Property 5: Active file path resolution**
    - Create `tests/property/test_prop_file_resolution.py`
    - Use Hypothesis to generate StepFile records with `is_modified` True/False, verify `resolve_file_path` returns `file_path` and the file exists on disk
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [x] 6. Implement FileList frontend component
  - [x] 6.1 Add stepFilesApi functions to `api.ts`
    - Add to `local-site/web/frontend/src/lib/api.ts`:
    - `getDownloadUrl(dossierId, stepNumber, fileId): string` — returns URL for download endpoint
    - `getViewUrl(dossierId, stepNumber, fileId): string` — returns URL for view endpoint
    - `replaceFile(dossierId, stepNumber, fileId, file: File): Promise<StepFileReplaceResponse>` — POST multipart to replace endpoint
    - Define `StepFileReplaceResponse` interface
    - _Requirements: 7.1, 7.2, 7.3_
  - [x] 6.2 Create FileList component
    - Create `local-site/web/frontend/src/components/FileList.tsx` and `FileList.module.css`
    - Props: `dossierId`, `stepNumber`, `files: StepFileItem[]`, `isLocked`, `showReplaceButton`, `onFileReplaced` callback
    - Display for each file: filename, file_type, formatted size, created_at date
    - Show badge « Modifié par l'expert » when `is_modified` is true, with `updated_at` date
    - Show « Aucun fichier produit » when files array is empty
    - Buttons: « Ouvrir » (Markdown → inline preview, PDF/DOCX → new tab via view URL), « Télécharger » (download URL), « Remplacer » (conditional on `showReplaceButton && !isLocked`)
    - Handle file-not-found errors with inline error message « Fichier introuvable »
    - File input for replace validates extension matches original before upload
    - Error display via `role="alert"` banner
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 4.1, 4.5, 4.6, 6.3, 6.4_

- [x] 7. Integrate FileList into Dossier and Step pages
  - [x] 7.1 Integrate FileList into Page Dossier
    - Update `local-site/web/frontend/src/app/dossier/[id]/page.tsx`
    - In each Section_Étape, render `<FileList>` with `showReplaceButton={false}` and `isLocked` based on step statut
    - Pass step files from the dossier detail API response
    - _Requirements: 1.1, 1.2, 1.3_
  - [x] 7.2 Integrate FileList into Page Étape
    - Update `local-site/web/frontend/src/app/dossier/[id]/step/[n]/page.tsx`
    - Render `<FileList>` with `showReplaceButton={true}` and `isLocked={step.statut === "validé"}`
    - Wire `onFileReplaced` callback to refresh step data after successful replacement
    - _Requirements: 1.4, 4.1, 4.5_

- [x] 8. Checkpoint — Frontend integration complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Endpoint property tests and unit tests
  - [x] 9.1 Write property test for download endpoint (Property 6)
    - **Property 6: Download endpoint returns attachment disposition with original filename**
    - Create `tests/property/test_prop_file_endpoints.py`
    - Use Hypothesis to generate valid StepFile records, verify download response has `Content-Disposition: attachment; filename="{filename}"` and body matches file on disk
    - **Validates: Requirements 3.2, 7.1**
  - [x] 9.2 Write property test for view endpoint (Property 7)
    - **Property 7: View endpoint returns inline disposition**
    - Add to `tests/property/test_prop_file_endpoints.py`
    - Use Hypothesis to generate valid StepFile records, verify view response has `Content-Disposition: inline` and correct Content-Type
    - **Validates: Requirements 7.2**
  - [x] 9.3 Write property test for replace rejection on validated steps (Property 8)
    - **Property 8: Replace is rejected on validated steps**
    - Add to `tests/property/test_prop_file_endpoints.py`
    - Use Hypothesis to generate steps with statut "validé" and valid replacement files, verify HTTP 403 with message "Étape verrouillée — modification impossible" and StepFile + disk unchanged
    - **Validates: Requirements 7.4, 7.5, 4.5**
  - [x] 9.4 Write unit tests for step_files router
    - Create `tests/unit/test_step_files_router.py`
    - Test: download returns 404 when file missing on disk
    - Test: view returns 404 when file missing on disk
    - Test: replace returns 403 when step is validated
    - Test: replace returns 400 when extension mismatch
    - Test: replace returns 400 when uploaded file is empty
    - Test: StepFile defaults `is_modified=False` and `original_file_path=None`
    - _Requirements: 2.5, 3.4, 4.5, 4.6, 7.4, 7.5_

- [x] 10. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate the 8 universal correctness properties from the design
- Unit tests validate specific error cases and edge conditions
- The backend uses Python (FastAPI + SQLAlchemy), the frontend uses TypeScript (Next.js + React)
