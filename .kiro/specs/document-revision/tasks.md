# Implementation Plan: Document Revision

## Overview

Implémentation de la fonctionnalité de révision documentaire permettant l'upload d'un fichier (.docx, .txt, .md) ou la saisie de texte copié-collé, sa correction automatique par le LLM (Mistral 7B via Ollama), et la restitution du résultat : fichier .docx avec track changes natifs, ou texte corrigé affiché dans une zone de sortie. Le backend utilise FastAPI avec manipulation XML directe (lxml) pour les marques de révision OOXML. Le frontend ajoute une page dédiée avec deux modes d'entrée (fichier / texte), progression, et zone de sortie.

## Tasks

- [x] 1. Set up backend data models and exceptions
  - [x] 1.1 Create data models and custom exceptions for the revision feature
    - Create `local-site/web/backend/services/revision_models.py` with dataclasses: `ParsedDocument`, `ParagraphInfo`, `RunInfo`, `ParagraphCorrection`, `DiffOperation`
    - Create custom exceptions: `RevisionError`, `DocumentParseError`, `ChunkProcessingError`
    - Add `TextRevisionRequest` and `TextRevisionResponse` Pydantic models
    - Add type annotations and Google-style docstrings
    - _Requirements: 3.1, 3.2, 7.2_

- [x] 2. Implement Document Parser
  - [x] 2.1 Implement the DocumentParser service
    - Create `local-site/web/backend/services/document_parser.py`
    - Implement `parse(file_bytes: bytes, file_ext: str) -> ParsedDocument | str` method
    - For `.docx`: use python-docx + lxml, extract paragraphs with runs, preserving XML element references and formatting properties (w:rPr). Handle tables by iterating over cells. Preserve headers, footers, and images without modification. Validate that input is a valid .docx (ZIP with `word/document.xml`).
    - For `.txt`: read as UTF-8 plain text, raise `DocumentParseError` if not valid UTF-8
    - For `.md`: read as UTF-8 Markdown text, preserve Markdown structure
    - Raise `DocumentParseError` for invalid files
    - _Requirements: 2.2, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 7.2, 7.5_

  - [x] 2.2 Write property test: paragraph count preservation
    - **Property 1: Préservation du nombre de paragraphes**
    - Create `tests/property/test_prop_revision_parser.py`
    - Use Hypothesis `docx_documents` strategy to generate valid .docx files
    - Verify that parsing preserves the exact number of paragraphs
    - **Validates: Requirements 3.1, 5.4**

  - [x] 2.3 Write property test: invalid file rejection
    - **Property 6: Rejet des fichiers invalides**
    - Add to `tests/property/test_prop_revision_parser.py`
    - Generate arbitrary byte sequences that are not valid .docx files
    - Verify `DocumentParseError` is raised for non-ZIP and ZIP-without-document.xml inputs
    - Test non-UTF-8 byte sequences for .txt/.md → `DocumentParseError`
    - **Validates: Requirements 2.2, 7.2, 7.5**

  - [x] 2.4 Write property test: parsing idempotence
    - **Property 7: Idempotence du parsing sans correction**
    - Add to `tests/property/test_prop_revision_parser.py`
    - Verify that parse → serialize without corrections produces identical textual content
    - **Validates: Requirements 3.1, 3.4**

- [x] 3. Implement Track Changes Generator
  - [x] 3.1 Implement the TrackChangesGenerator service
    - Create `local-site/web/backend/services/track_changes_generator.py`
    - Implement `generate(parsed_doc, corrections) -> bytes` method
    - Use `difflib.SequenceMatcher` for word-level diff between original and corrected text
    - Generate OOXML `w:ins` and `w:del` elements with proper attributes (`w:id`, `w:author="Judi-Expert"`, `w:date`)
    - Preserve original run formatting (w:rPr) on both insertions and deletions
    - Ensure unique `w:id` values across the document
    - Repackage modified XML into a valid .docx ZIP archive
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 3.2 Write property test: run formatting preservation
    - **Property 2: Préservation du formatage des runs**
    - Create `tests/property/test_prop_revision_track_changes.py`
    - Generate paragraphs with varied formatting (bold, italic, underline, font size, color)
    - Verify formatting properties are preserved on both w:del and w:ins elements
    - **Validates: Requirements 3.2, 5.4**

  - [x] 3.3 Write property test: revision element validity
    - **Property 3: Validité structurelle des éléments de révision**
    - Add to `tests/property/test_prop_revision_track_changes.py`
    - For any pair (original, corrected) where they differ, verify w:del and w:ins have required attributes and unique w:id values
    - **Validates: Requirements 5.2, 5.5**

  - [x] 3.4 Write property test: textual content round-trip
    - **Property 4: Round-trip du contenu textuel**
    - Add to `tests/property/test_prop_revision_track_changes.py`
    - Verify that extracting "accepted" text (keep insertions, remove deletions) equals corrected text
    - Verify that extracting "rejected" text (keep deletions, remove insertions) equals original text
    - **Validates: Requirements 5.2, 5.5**

  - [x] 3.5 Write unit tests for TrackChangesGenerator
    - Create `tests/unit/test_track_changes_generator.py`
    - Test simple word replacement, insertion, deletion cases
    - Test XML structure correctness of generated w:ins/w:del elements
    - Test that unchanged paragraphs are not modified
    - _Requirements: 5.2, 5.4, 5.5_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Revision Service (orchestration)
  - [x] 5.1 Implement the RevisionService with chunking and LLM integration
    - Create `local-site/web/backend/services/revision_service.py`
    - Implement `RevisionService` class with dependency on existing `LLMService`
    - Implement `revise_document(file_bytes: bytes, file_ext: str) -> bytes | str` orchestrating:
      - `.docx`: parse → chunk → LLM → track changes → output bytes
      - `.txt`/`.md`: read text → chunk → LLM → output corrected text
    - Implement `revise_text(text: str) -> str` for copié-collé mode: chunk → LLM → output
    - Implement `_build_chunks(paragraphs)` with adaptive chunking respecting ~60% of context window
    - Define `PROMPT_REVISION` system prompt for legal document correction
    - Handle LLM timeout with 1 retry per chunk, fallback to original text on failure
    - Use `tempfile` and context manager for temporary file cleanup
    - _Requirements: 2b.2, 4.1, 4.2, 4.3, 4.4, 4.5, 7.1, 7.4, 7.5, 8.1, 8.2, 8.3_

  - [x] 5.2 Write property test: chunk size limit
    - **Property 5: Respect de la limite de taille des chunks**
    - Create `tests/property/test_prop_revision_chunking.py`
    - Generate documents with varying paragraph counts and lengths
    - Verify each chunk's estimated token count does not exceed 60% of ctx_max
    - **Validates: Requirements 7.4**

  - [x] 5.3 Write unit tests for RevisionService
    - Create `tests/unit/test_revision_service.py`
    - Test prompt construction and paragraph separation
    - Test chunking respects limits and doesn't split paragraphs
    - Test LLM timeout → fallback behavior (mock LLM)
    - Test corrupted file → clear error
    - Test text revision (revise_text) with mock LLM
    - Test .txt/.md file revision returns corrected text string
    - Test non-UTF-8 .txt file → DocumentParseError
    - _Requirements: 4.1, 7.1, 7.4, 7.5_

- [x] 6. Implement Revision Router (API endpoints)
  - [x] 6.1 Create the revision router with upload and text endpoints
    - Create `local-site/web/backend/routers/revision.py`
    - Implement `POST /upload` endpoint accepting multipart/form-data
      - Validate file extension (.docx, .txt, .md) → HTTP 400
      - Validate file size (≤ 20 MB) → HTTP 413
      - For .docx: call `RevisionService.revise_document()` and return `FileResponse` with filename `fichier-revu.docx`
      - For .txt/.md: call `RevisionService.revise_document()` and return `TextRevisionResponse` JSON
    - Implement `POST /text` endpoint accepting JSON body
      - Validate text non-empty → HTTP 400
      - Validate text ≤ 100 000 characters → HTTP 400
      - Call `RevisionService.revise_text()` and return `TextRevisionResponse` JSON
    - Map exceptions: `DocumentParseError` → 400, `LLMTimeoutError`/`LLMConnectionError` → 503
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2b.1, 2b.2, 2b.3, 2b.4, 5.3, 5b.1, 7.1, 7.2, 7.5_

  - [x] 6.2 Register the revision router in the FastAPI app
    - Add router import and `app.include_router(revision.router, prefix="/api/revision", tags=["revision"])` in `local-site/web/backend/main.py`
    - _Requirements: 1.1_

  - [x] 6.3 Write unit tests for the revision router
    - Create `tests/unit/test_revision_router.py`
    - Test rejection of non-.docx/.txt/.md files (HTTP 400)
    - Test rejection of files > 20 MB (HTTP 413)
    - Test successful .docx upload with mocked RevisionService → FileResponse
    - Test successful .txt upload with mocked RevisionService → JSON response
    - Test successful text submission → JSON response
    - Test empty text submission → HTTP 400
    - Test text > 100k chars → HTTP 400
    - Test LLM unavailable → HTTP 503
    - _Requirements: 2.1, 2.2, 2.4, 2b.3, 2b.4, 7.1, 7.2_

- [x] 7. Checkpoint - Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement Frontend - Revision Page and Components
  - [x] 8.1 Add revision API client functions
    - Add `revisionApi.uploadFile(file: File)` to `local-site/web/frontend/src/lib/api.ts`
      - For .docx: POST multipart, responseType blob, 30-min timeout
      - For .txt/.md: POST multipart, expect JSON response
    - Add `revisionApi.submitText(text: string)` → POST JSON, expect JSON response
    - Handle error responses
    - _Requirements: 2.3, 2b.2, 6.1, 6.2_

  - [x] 8.2 Create the Revision page with dual input modes and output zone
    - Create `local-site/web/frontend/src/app/revision/page.tsx`
    - Implement state machine: "idle" → "uploading" → "processing" → "done" | "error"
    - Create `InputTabs` component: toggle between "Fichier" and "Texte" modes
    - Create `UploadCard` component: file input accepting .docx, .txt, .md, drag-and-drop support
    - Create `TextInputCard` component: textarea for pasting/typing text, submit button
    - Create `ProgressCard` component: spinner/progress indicator during processing
    - Create `DownloadCard` component: download button for .docx output, reset button
    - Create `OutputZone` component: read-only textarea displaying corrected text, "Copier" button, optional download button for .txt/.md
    - Create `ErrorCard` component: error message display with retry button
    - Ensure accessibility (ARIA labels, keyboard navigation, focus management)
    - _Requirements: 1.2, 1.4, 2.1, 2b.1, 5b.1, 5b.2, 5b.3, 5b.4, 5b.5, 6.1, 6.2, 6.3, 6.4, 7.3_

  - [x] 8.3 Add "Révision" navigation link in the header menu
    - Modify the header/navigation component to add a "Révision" link pointing to `/revision`
    - Ensure the link is accessible independently from any active expertise dossier
    - _Requirements: 1.1, 1.3, 8.1_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (7 properties total)
- Unit tests validate specific examples and edge cases
- No database migrations needed — this feature uses temporary files only
- The existing `LLMService` (`services/llm_service.py`) is reused; no new LLM integration needed
- Frontend components should follow the existing functional component + hooks pattern
- Track changes (w:ins/w:del) are only generated for .docx files; .txt/.md and text input return plain corrected text

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "3.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "3.2", "3.3", "3.4", "3.5"] },
    { "id": 3, "tasks": ["5.1"] },
    { "id": 4, "tasks": ["5.2", "5.3", "6.1"] },
    { "id": 5, "tasks": ["6.2", "6.3"] },
    { "id": 6, "tasks": ["8.1", "8.3"] },
    { "id": 7, "tasks": ["8.2"] }
  ]
}
```
