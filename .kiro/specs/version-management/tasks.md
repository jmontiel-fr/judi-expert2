# Implementation Plan: Gestion des Versions

## Overview

Implement the version management system for Judi-Expert following a backend-first approach: VERSION files → shared utility → data models/migrations → services → API routers → frontend modifications → script modifications → tests. The backend uses Python (FastAPI + SQLAlchemy), the frontend uses TypeScript (Next.js 14).

## Tasks

- [ ] 1. Create VERSION files and version reader utility
  - [x] 1.1 Create `local-site/VERSION`, `central-site/VERSION` and `central-site/app_locale_package/VERSION` files
    - Each file contains 2 lines: semver version (e.g. `1.0.1`) and ISO date (e.g. `2026-05-08`)
    - `central-site/app_locale_package/VERSION` is a copy of `local-site/VERSION`
    - Display format: `V1.0.1 - 08 mai 2026`
    - _Requirements: 1.1, 11.1, 14.1, 14.2_

  - [x] 1.2 Create `local-site/web/backend/services/version_reader.py`
    - Implement `VersionInfo` frozen dataclass with `version: str` and `date: str` fields
    - Implement `read_version_file(path: Path) -> VersionInfo` that reads and parses the 2-line VERSION file
    - Implement `validate_semver(version: str) -> bool` to validate MAJOR.MINOR.PATCH format
    - Implement `compare_versions(a: str, b: str) -> int` for semver comparison
    - Implement `format_version_display(info: VersionInfo, prefix: str) -> str` to produce French-formatted display string (e.g. "App Locale V1.2.0 - 17 avril 2026")
    - Raise `FileNotFoundError` if file absent, `ValueError` if format invalid
    - _Requirements: 1.1, 1.2, 1.4, 2.5, 3.2, 5.1, 11.1, 12.1_

  - [x] 1.3 Copy `version_reader.py` to `central-site/web/backend/services/version_reader.py`
    - Same utility reused on the central site
    - _Requirements: 11.1, 11.2_

  - [x] 1.4 Write property tests for version reader (`tests/property/test_prop_version.py`)
    - **Property 1: VERSION file round-trip** — write semver + ISO date, read back, verify exact match
    - **Validates: Requirements 1.1, 11.1**

  - [x] 1.5 Write property test for semver validation
    - **Property 2: Semver validation** — accept valid MAJOR.MINOR.PATCH, reject all other strings
    - **Validates: Requirement 2.5**

  - [x] 1.6 Write property test for semver comparison ordering
    - **Property 3: Semver comparison ordering** — verify total order, transitivity, and consistency
    - **Validates: Requirement 3.2**

  - [x] 1.7 Write property test for version display formatting
    - **Property 4: Version display formatting** — verify output contains prefix, "V", exact version, "-", French-formatted date
    - **Validates: Requirements 5.1, 12.1**

- [x] 2. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Create data models and schemas
  - [x] 3.1 Add `app_version` and `llm_model_version` columns to `LocalConfig` model
    - Edit `local-site/web/backend/models/local_config.py` to add `app_version: Mapped[Optional[str]] = mapped_column(String(20))` and `llm_model_version: Mapped[Optional[str]] = mapped_column(String(100))`
    - _Requirements: 3.6, 7.4_

  - [x] 3.2 Create Alembic migration for LocalConfig changes
    - Generate migration in `local-site/web/backend/alembic/versions/` adding the two new columns
    - _Requirements: 3.6, 7.4_

  - [x] 3.3 Create `central-site/web/backend/models/app_version.py`
    - Implement `AppVersion` model with fields: `id`, `version` (String(20)), `download_url` (String(500)), `mandatory` (bool, default True), `release_notes` (Text, optional), `published_at` (datetime, default func.now())
    - Register in `central-site/web/backend/models/__init__.py`
    - _Requirements: 2.3_

  - [x] 3.4 Create Alembic migration for AppVersion table
    - Generate migration in `central-site/web/backend/alembic/versions/` creating the `app_version` table
    - _Requirements: 2.3_

  - [x] 3.5 Create `central-site/web/backend/schemas/version.py`
    - Implement `VersionResponse`, `VersionCreateRequest` (with semver regex validation), `VersionCreateResponse` Pydantic schemas
    - _Requirements: 2.1, 2.4, 2.5_

  - [x] 3.6 Create `local-site/web/backend/schemas/version.py`
    - Implement `LocalVersionResponse`, `UpdateStatusResponse`, `LlmUpdateStatusResponse` Pydantic schemas
    - _Requirements: 5.3, 4.3, 7.1_

- [ ] 4. Implement backend services
  - [x] 4.1 Create `local-site/web/backend/services/update_service.py`
    - Implement `UpdateService` class orchestrating forced update: download Docker images from URL, stop containers via Docker Compose, load new images (`docker load`), restart containers, update `LocalConfig.app_version`
    - Implement rollback logic on failure (restore previous containers)
    - Track progress with status/percentage for the frontend
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 4.2 Create `local-site/web/backend/services/llm_update_service.py`
    - Implement `LlmUpdateService` class that reads `/root/.ollama/update-status.json` from the Ollama volume
    - Return current LLM update status (idle/downloading/ready/error) and progress percentage
    - Read current model digest from Ollama API
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 4.3 Write property test for data isolation in version requests
    - **Property 5: Data isolation in version requests** — verify version check requests contain only `current_version`, no dossier/expert fields
    - **Validates: Requirements 9.1, 9.2**

- [ ] 5. Implement API routers
  - [x] 5.1 Create `local-site/web/backend/routers/version.py`
    - `GET /api/version`: Read local VERSION file, check Site Central for updates (via SiteCentralClient during business hours), return `LocalVersionResponse`
    - `POST /api/version/update`: Trigger forced update via `UpdateService`
    - `GET /api/llm/update-status`: Return LLM update status via `LlmUpdateService`
    - Register router in `local-site/web/backend/main.py`
    - _Requirements: 1.2, 3.1, 3.2, 3.3, 3.4, 3.5, 5.3, 7.1, 9.1, 9.3_

  - [x] 5.2 Create `central-site/web/backend/routers/version.py`
    - `GET /api/version`: Return latest published `AppVersion` as `VersionResponse`
    - `POST /api/admin/versions`: Create new version (admin-only), validate semver format
    - `GET /api/admin/versions`: List all published versions
    - Register router in `central-site/web/backend/main.py`
    - _Requirements: 2.1, 2.2, 2.4, 2.5_

  - [x] 5.3 Modify `central-site/web/backend/main.py` health endpoint
    - Read `central-site/VERSION` at startup and include `version` field in `/api/health` response
    - _Requirements: 11.2, 11.3, 11.4_

  - [x] 5.4 Modify `central-site/web/backend/routers/downloads.py`
    - Update `download_app()` to read latest version from `AppVersion` model instead of hardcoded strings
    - Fall back to "0.1.0" if no version published
    - Include version in installer filename
    - _Requirements: 10.1, 10.2, 10.3_

  - [x] 5.5 Write unit tests for version routers (`tests/unit/test_version_router.py`)
    - Test GET /api/version returns all required fields
    - Test POST /api/admin/versions validates semver
    - Test version check outside business hours returns no update
    - Test version check when Site Central unreachable returns graceful fallback
    - Test GET /api/llm/update-status returns required fields
    - Test GET /api/health includes version field
    - Test GET /api/downloads/app uses latest published version
    - _Requirements: 2.1, 2.5, 3.4, 3.5, 5.3, 7.1, 10.1, 10.3, 11.4_

- [x] 6. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement frontend changes
  - [x] 7.1 Modify `local-site/web/frontend/src/components/Footer.tsx`
    - Fetch version from `GET /api/version` and display "App Locale V{version} - {date}" in the footer
    - _Requirements: 5.1_

  - [x] 7.2 Modify `central-site/web/frontend/src/components/Footer.tsx`
    - Fetch version from `GET /api/health` and display "Site Central V{version} - {date}" in the footer
    - _Requirements: 12.1, 12.2_

  - [x] 7.3 Create `local-site/web/frontend/src/components/UpdateScreen.tsx`
    - Implement blocking modal screen with progress bar showing update steps (downloading → installing → restarting)
    - Show error message with retry button on failure
    - Redirect to login page on completion
    - Display "Application mise à jour en version {version}" banner after update
    - _Requirements: 3.3, 4.3, 4.5, 5.2_

  - [x] 7.4 Wire UpdateScreen into the local-site app startup flow
    - On app load, call `GET /api/version` — if `update_available` and `mandatory`, render `UpdateScreen` instead of normal content
    - Display LLM update warning on login page when status is `downloading`
    - Display "Nouveau modèle prêt — sera activé au prochain redémarrage" when status is `ready`
    - _Requirements: 3.2, 3.3, 6.2, 7.2, 7.3_

- [ ] 8. Modify shell scripts and entrypoint
  - [x] 8.1 Modify `local-site/ollama-entrypoint.sh`
    - Add digest comparison logic: compare local model digest vs remote digest
    - Write update status JSON to `/root/.ollama/update-status.json` (status: idle/downloading/ready/error, progress, model, started_at, error)
    - Launch `ollama pull` in background when new version detected
    - Update status file on completion or error
    - _Requirements: 6.1, 6.3, 6.4, 6.5, 6.6_

  - [x] 8.2 Modify `local-site/scripts/start.sh`
    - Add `ollama pull $LLM_MODEL` step before container startup to force model check/download
    - Display download progress in console
    - Abort startup on download failure
    - _Requirements: 8.1, 8.3, 8.4, 8.5_

  - [x] 8.3 Modify `local-site/scripts/restart.sh`
    - Add `ollama pull $LLM_MODEL` step before container rebuild to force model check/download
    - Display download progress in console
    - Abort restart on download failure
    - _Requirements: 8.2, 8.3, 8.4, 8.5_

  - [x] 8.4 Modify `central-site/app_locale_package/package.sh`
    - Read version from `local-site/VERSION` instead of `JUDI_VERSION` env var
    - _Requirements: 1.3_

  - [x] 8.5 Modify central-site deployment scripts (`build.sh`, `push-ecr.sh`, `deploy.sh`)
    - Read version from `central-site/VERSION` and use it to tag Docker images (e.g. `judi-central-backend:1.2.0`)
    - _Requirements: 13.1, 13.2_

  - [x] 8.6 Write property test for installer filename version inclusion
    - **Property 6: Installer filename includes version** — verify generated installer filename contains the exact semver string
    - **Validates: Requirement 10.2**

- [x] 9. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Integration tests and final wiring
  - [x] 10.1 Write integration tests (`tests/integration/test_version_integration.py`)
    - Test startup reads VERSION file correctly
    - Test publish-then-get version flow on central site
    - Test forced update workflow with mocked Docker commands
    - Test rollback on update failure
    - Test volume preservation during update
    - Test downloads endpoint uses latest published version
    - _Requirements: 1.2, 2.2, 4.1-4.6, 10.1, 11.2_

  - [x] 10.2 Write smoke tests (`tests/smoke/test_version_smoke.py`)
    - Test VERSION files exist in both sites
    - Test HTTPS-only for version requests
    - _Requirements: 1.1, 9.3, 11.1_

- [x] 11. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Create documentation file
  - [x] 12.1 Create `docs/version-management.md`
    - Document the VERSION file format (2 lines: semver + ISO date)
    - Document semver conventions (MAJOR = breaking changes, MINOR = new features, PATCH = bugfixes)
    - Document the version publication process (admin publishes via POST /api/admin/versions)
    - Document the forced update process (startup check → download → install → restart)
    - Document the LLM model update process (background download, activation on restart)
    - Document the version display format in the UI (`V{x}.{y}.{z} - {jour} {mois} {année}`)
    - Include concrete examples of VERSION files and publication commands
    - _Requirements: 15.1, 15.2, 15.3_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate the 6 universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The version reader utility is shared between both sites (copy, not symlink) to keep deployments independent
- Alembic migrations are needed for both local (SQLite) and central (PostgreSQL) databases
- VERSION files are present in 3 locations: `local-site/VERSION`, `central-site/VERSION`, `central-site/app_locale_package/VERSION`
- The `app_locale_package/VERSION` must always be synchronized with `local-site/VERSION` at release time
- Documentation in `docs/version-management.md` serves as the single reference for the versioning system
