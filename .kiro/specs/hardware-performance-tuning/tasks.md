# Implementation Plan: Hardware Performance Tuning

## Overview

Implement automatic hardware detection and dynamic LLM performance profile selection. The system detects CPU/RAM/GPU at startup, selects an appropriate profile (high/medium/low/minimal), applies parameters to all LLM calls, and exposes a frontend section for monitoring and manual override. Implementation spans backend services, database migration, API endpoints, LLM service integration, and frontend UI.

## Tasks

- [x] 1. Data models, migration, and core interfaces
  - [x] 1.1 Add hardware performance columns to LocalConfig model and create Alembic migration
    - Add `detected_hardware_json` (String 1024, nullable) and `performance_profile_override` (String 50, nullable) columns to `local-site/web/backend/models/local_config.py`
    - Create migration `local-site/web/backend/alembic/versions/009_add_hardware_performance_columns.py` with upgrade/downgrade
    - _Requirements: 1.4, 5.2_

  - [x] 1.2 Create HardwareInfo and PerformanceProfile dataclasses and PROFILES dictionary
    - Create `local-site/web/backend/services/hardware_service.py`
    - Define `HardwareInfo` dataclass (cpu_model, cpu_freq_ghz, cpu_cores, ram_total_gb, gpu_name, gpu_vram_gb)
    - Define `PerformanceProfile` dataclass (name, display_name, ram_range, ctx_max, model, rag_chunks, tokens_per_sec)
    - Define `PROFILES` dictionary with all 4 profiles (high, medium, low, minimal)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 2. Hardware detection and profile selection logic
  - [x] 2.1 Implement HardwareDetector class
    - Implement `detect()` method in `hardware_service.py` using `psutil` for CPU cores and RAM, `/proc/cpuinfo` for model/frequency, nvidia-smi/proc for GPU
    - Implement safe defaults on failure: "Unknown CPU", 2.0 GHz, 4 cores, 8.0 GB RAM, None GPU
    - Log warnings on detection failures
    - _Requirements: 1.1, 1.2, 1.3, 1.5_

  - [x] 2.2 Implement ProfileSelector class
    - Implement `select()` method with RAM threshold logic (≥32 → high, ≥16 → medium, ≥8 → low, <8 → minimal)
    - Implement `compute_tokens_per_sec()` with formula: `8.0 × (cores × freq_ghz) / 16`
    - Implement `get_active_profile()` that respects override from DB
    - Implement `check_ram_warning()` that flags over-provisioned profiles
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 5.5_

  - [x] 2.3 Write property test: Profile selection matches RAM thresholds
    - **Property 1: Profile selection is consistent with RAM thresholds**
    - Create `tests/property/test_prop_hardware_performance.py`
    - Generator: `st.floats(min_value=0.5, max_value=256.0)` for RAM
    - Assert correct profile name, ctx_max, model, and rag_chunks for each RAM range
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

  - [x] 2.4 Write property test: Tokens per second formula
    - **Property 2: Tokens per second computation follows the formula**
    - Generator: `st.integers(1, 64)` for cores, `st.floats(0.5, 6.0)` for freq
    - Assert result equals `8.0 × (cores × frequency_ghz) / 16`
    - **Validates: Requirements 2.6**

  - [x] 2.5 Write property test: RAM warning consistency
    - **Property 3: RAM warning for over-provisioned profiles**
    - Generator: `st.floats(1.0, 128.0)` for RAM, `st.sampled_from(PROFILES)` for profile
    - Assert warning raised when profile requires more RAM than detected
    - **Validates: Requirements 5.5**

  - [x] 2.6 Write property test: Step duration estimate formula
    - **Property 4: Step duration estimate follows the formula**
    - Generator: `st.integers(100, 50000)` for tokens, `st.floats(0.1, 3.0)` for ratio, `st.floats(1.0, 50.0)` for tps
    - Assert result equals `(estimated_input_tokens × output_ratio) / tokens_per_sec`
    - **Validates: Requirements 6.2**

- [x] 3. LLM Service integration
  - [x] 3.1 Implement ActiveProfile singleton in llm_service.py
    - Add `ActiveProfile` class with thread-safe class methods: `set()`, `get_ctx_max()`, `get_model()`, `get_tokens_per_sec()`
    - Store both `PerformanceProfile` and `HardwareInfo` references
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 3.2 Modify LLM_Service to use ActiveProfile values
    - Replace hardcoded `CTX_MAX`, `LLM_MODEL`, `LLM_TOKENS_PER_SEC` reads with `ActiveProfile` getters
    - Implement fallback chain: ActiveProfile → environment variables → hardcoded defaults
    - Ensure hot-reload: changing ActiveProfile affects subsequent requests without restart
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 3.3 Implement step duration estimation
    - Add `compute_step_duration()` method using formula: `(estimated_input_tokens × output_ratio) / tokens_per_sec`
    - Define step-specific output_ratios for Steps 1–5
    - Return durations in minutes with tolerance indicator
    - _Requirements: 6.1, 6.2_

  - [x] 3.4 Implement model download trigger on profile change
    - Add logic to check if active profile's model differs from currently available model
    - Trigger `ollama pull` when model mismatch detected
    - Handle download failure gracefully: keep previous model, log error
    - _Requirements: 7.1, 7.3, 7.4_

  - [x] 3.5 Write unit tests for ActiveProfile and LLM_Service integration
    - Test `ActiveProfile` singleton set/get behavior
    - Test hot-reload: changing profile updates subsequent reads
    - Test fallback chain when ActiveProfile not initialized
    - Test model download trigger on mismatch
    - Test model download failure fallback
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 7.1, 7.3_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Startup integration and persistence
  - [x] 5.1 Integrate hardware detection into FastAPI lifespan
    - Modify `local-site/web/backend/main.py` lifespan to call `HardwareDetector.detect()` at startup
    - Read override from `local_config` DB table
    - Call `ProfileSelector.get_active_profile()` with hardware info and override
    - Store detected hardware JSON in `local_config.detected_hardware_json`
    - Call `ActiveProfile.set()` with selected profile
    - Log selected profile at startup
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4_

  - [x] 5.2 Write unit tests for hardware detection and startup flow
    - Test `HardwareDetector.detect()` returns valid `HardwareInfo` (mock psutil)
    - Test safe defaults when psutil raises exceptions
    - Test override persistence to DB (write and clear)
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 5.2, 5.4_

- [x] 6. API endpoints
  - [x] 6.1 Add hardware info and performance profile endpoints to config router
    - Add `GET /api/config/hardware-info` returning `HardwareInfoResponse`
    - Add `GET /api/config/performance-profile` returning `PerformanceProfileResponse` (active profile, is_override flag, auto-detected profile name, all profiles list, hardware info)
    - Add Pydantic response schemas in `routers/config.py`
    - _Requirements: 3.5, 4.1, 4.2, 4.3_

  - [x] 6.2 Add override and model download status endpoints
    - Add `PUT /api/config/performance-profile/override` accepting `OverrideRequest` (profile_name or null for auto)
    - Validate profile name, return 400 for unknown profiles
    - Persist override to `local_config.performance_profile_override`
    - Apply new profile to `ActiveProfile` immediately
    - Trigger model download if needed
    - Add `GET /api/config/model-download-status` returning `ModelDownloadStatus`
    - _Requirements: 5.1, 5.2, 5.4, 7.1, 7.2, 7.4_

  - [x] 6.3 Write unit tests for API endpoints
    - Test `GET /hardware-info` response shape
    - Test `GET /performance-profile` returns all profiles with active highlighted
    - Test `PUT /override` with valid profile name
    - Test `PUT /override` with null (revert to auto)
    - Test `PUT /override` with invalid name returns 400
    - _Requirements: 3.5, 4.1, 4.2, 5.1, 5.2, 5.4_

- [x] 7. Frontend Performance section
  - [x] 7.1 Create PerformanceSection component in config page
    - Add performance section to `local-site/web/frontend/src/app/config/page.tsx`
    - Create "Matériel détecté" card displaying CPU model, frequency, cores, RAM, GPU info
    - Create "Profil actif" card showing active profile name, model, CTX_MAX, RAG chunks
    - Add visual indicator distinguishing auto-detected vs manually overridden profile
    - _Requirements: 4.1, 4.2, 5.3_

  - [x] 7.2 Implement profile reference table and override selector
    - Create reference table showing all profiles: name, RAM range, model, CTX_MAX, RAG chunks, estimated durations per step
    - Highlight the row corresponding to the auto-detected profile
    - Add dropdown selector for manual override (all profiles + "Automatique" option)
    - Display RAM warning when selecting a profile requiring more RAM than available
    - _Requirements: 4.3, 4.4, 5.1, 5.5, 6.1_

  - [x] 7.3 Implement API integration and state management
    - Fetch hardware info and active profile from backend API on page load
    - Handle override selection: call PUT endpoint, update UI state
    - Display model download progress indicator when download in progress
    - Update step duration estimates when profile changes
    - _Requirements: 4.5, 5.2, 6.3, 7.2_

- [x] 8. Integration and wiring
  - [x] 8.1 Write integration tests for full startup flow
    - Test full lifespan: detect → persist → profile active → LLM uses profile CTX_MAX
    - Test override applies to LLM calls (new model/ctx_max used after override)
    - Create `tests/integration/test_hardware_integration.py`
    - _Requirements: 1.4, 3.1, 3.4, 5.2_

  - [x] 8.2 Add psutil dependency and verify Docker compatibility
    - Add `psutil` to `local-site/web/backend/requirements.txt` (pinned version)
    - Verify `/proc/cpuinfo` and `/proc/meminfo` accessible in Docker container
    - Verify `nvidia-smi` detection works when GPU passthrough is configured
    - _Requirements: 1.1, 1.2, 1.3_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The design specifies Python (FastAPI backend) and TypeScript (Next.js frontend) — no language selection needed
- Migration numbering follows existing convention (009 is next)
- Frontend section integrates into existing `/config` page, not a separate route

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1", "2.2"] },
    { "id": 2, "tasks": ["2.3", "2.4", "2.5", "2.6", "3.1"] },
    { "id": 3, "tasks": ["3.2", "3.3", "3.4"] },
    { "id": 4, "tasks": ["3.5", "5.1"] },
    { "id": 5, "tasks": ["5.2", "6.1", "6.2", "8.2"] },
    { "id": 6, "tasks": ["6.3", "7.1"] },
    { "id": 7, "tasks": ["7.2", "7.3"] },
    { "id": 8, "tasks": ["8.1"] }
  ]
}
```
