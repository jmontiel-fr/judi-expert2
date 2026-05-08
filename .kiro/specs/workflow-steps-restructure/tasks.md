# Implementation Plan: Workflow Steps Restructure

## Overview

Refactor the Step pages in the Judi-Expert Application Locale frontend to use a uniform tripartite layout (Input → Operation → Output) with a descriptive Action Banner. This is a frontend-only restructuring using configuration-driven step metadata to replace the current monolithic step-specific views (Step1View through Step5View in `page.tsx`).

## Tasks

- [x] 1. Create step configuration module and shared types
  - [x] 1.1 Create `stepConfig.ts` in `local-site/web/frontend/src/lib/`
    - Define `StepConfig` interface with `name`, `bannerText`, `buttonLabel`, `inputFileTypes`, `outputFileTypes`
    - Implement `STEP_CONFIG` constant mapping step numbers 1–4 to their configuration
    - Export helper functions `getInputFiles(stepNumber, files)` and `getOutputFiles(stepNumber, files)` that filter `StepFileItem[]` by file type classification
    - Banner text for Step 1 must be a function accepting `dossierName` for path interpolation
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 11.1, 11.2, 11.3, 11.4, 13.1, 13.2, 13.3, 13.4_

  - [x] 1.2 Write property test for file filtering logic (Property 1: File list rendering completeness)
    - **Property 1: File list rendering completeness**
    - Generate random arrays of `StepFileItem` with various `file_type` values; verify that for each step, every file whose `file_type` is in `inputFileTypes` appears in `getInputFiles` result, and every file in `outputFileTypes` appears in `getOutputFiles` result, with no omissions or duplicates
    - Use fast-check (TypeScript) with minimum 100 iterations
    - **Validates: Requirements 1.2, 1.4, 3.4, 5.3, 6.3, 7.3, 9.3**

- [x] 2. Create ActionBanner component
  - [x] 2.1 Create `ActionBanner.tsx` and `ActionBanner.module.css` in `local-site/web/frontend/src/components/`
    - Accept props: `stepNumber: number`, `dossierName: string`
    - Render the banner text from `STEP_CONFIG`, interpolating `dossierName` for Step 1
    - Style with highlighted background, left border accent, and "Action" label/icon
    - Ensure visual distinction from surrounding content (requirement 2.6)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [x]* 2.2 Write unit tests for ActionBanner
    - Verify each step (1–4) renders the exact expected banner text from requirements
    - Verify Step 1 banner interpolates dossier name correctly in the path
    - Verify the "Action" label/icon is rendered
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 3. Create InputSection component
  - [x] 3.1 Create `InputSection.tsx` and `InputSection.module.css` in `local-site/web/frontend/src/components/`
    - Accept props: `stepNumber`, `dossierId`, `files: StepFileItem[]`, `isLocked`, `dossierStatut`, `mode?: "entretien" | "analyse"`, `onFileUploaded`
    - Display heading "Fichiers d'entrée"
    - Filter and display input files using `getInputFiles(stepNumber, files)`
    - Reuse existing `FileList` component for file display
    - Show placeholder message "Aucun fichier d'entrée disponible" when no input files exist
    - Include upload controls for steps that accept uploads (Step 1: ordonnance + complementary; Step 3: diligence files) when not locked
    - For Step 2, display mode-dependent template (TPE in Mode_Entretien, TPA in Mode_Analyse)
    - _Requirements: 1.2, 1.6, 3.1, 3.2, 3.3, 3.4, 5.1, 5.2, 5.3, 5.4, 7.1, 7.2, 7.3, 9.1, 9.2, 9.3, 9.4_

  - [x]* 3.2 Write unit tests for InputSection
    - Test placeholder message when no input files exist
    - Test that only input-classified files are displayed
    - Test upload controls are hidden when locked
    - Test Step 2 mode-dependent template display
    - _Requirements: 1.6, 5.2_

- [x] 4. Create OperationSection component
  - [x] 4.1 Create `OperationSection.tsx` and `OperationSection.module.css` in `local-site/web/frontend/src/components/`
    - Accept props: `stepNumber`, `dossierId`, `step: StepDetail`, `isLocked`, `isDossierClosed`, `onExecute`, `onCancel`
    - Display heading "Opération"
    - Render action button with label from `STEP_CONFIG[stepNumber].buttonLabel`
    - Show progress indicator (reuse existing `StepProgressList`) when `step.statut === "en_cours"`
    - Show lock indicator when step is locked or dossier is closed
    - Disable button when `statut` is `"en_cours"` or `"valide"` or dossier is `"fermé"`
    - Include cancel button during processing
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

  - [x]* 4.2 Write property test for button disabled state (Property 4: Action button disabled state invariant)
    - **Property 4: Action button disabled state invariant**
    - Generate random combinations of `(stepNumber, stepStatut, dossierStatut)`; verify button is disabled iff `statut` is `"en_cours"` or `"valide"` or dossier is `"fermé"`; verify progress indicator shown when `"en_cours"`; verify lock indicator shown when locked/closed
    - Use fast-check (TypeScript) with minimum 100 iterations
    - **Validates: Requirements 13.5, 13.6**

  - [x]* 4.3 Write unit tests for OperationSection
    - Verify correct button label for each step (1–4)
    - Verify progress indicator renders during "en_cours"
    - Verify lock indicator renders when locked
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

- [x] 5. Create OutputSection component
  - [x] 5.1 Create `OutputSection.tsx` and `OutputSection.module.css` in `local-site/web/frontend/src/components/`
    - Accept props: `stepNumber`, `dossierId`, `files: StepFileItem[]`, `isLocked`
    - Display heading "Fichiers de sortie"
    - Filter and display output files using `getOutputFiles(stepNumber, files)`
    - Reuse existing `FileList` component for file display
    - Show placeholder message "Aucun fichier de sortie généré" when no output files exist
    - Handle unknown `file_type` fallback: display in output section by default (already implemented in `getOutputFiles`)
    - _Requirements: 1.4, 1.5, 4.1, 4.2, 4.3, 4.4, 6.1, 6.2, 6.3, 6.4, 8.1, 8.2, 8.3, 10.1, 10.2, 10.3_

  - [x]* 5.2 Write unit tests for OutputSection
    - Test placeholder message when no output files exist
    - Test that only output-classified files are displayed
    - Test unknown file_type fallback behavior
    - _Requirements: 1.5, 8.3_

- [x] 6. Checkpoint - Ensure all component tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Refactor StepViewPage to use new tripartite layout
  - [x] 7.1 Refactor `page.tsx` at `local-site/web/frontend/src/app/dossier/[id]/step/[n]/`
    - Remove Step1View, Step2View, Step3View, Step4View, Step5View inline components
    - Replace with unified layout: Back link → Header → ActionBanner → InputSection → OperationSection → OutputSection
    - Fetch dossier name for ActionBanner interpolation
    - Pass filtered file lists and step-specific props to each section
    - Move step-specific upload logic into InputSection
    - Move step-specific execution logic into OperationSection
    - Preserve existing polling logic for "en_cours" status detection
    - Preserve existing error handling and loading states
    - _Requirements: 1.1, 2.1, 11.5, 11.6_

  - [x] 7.2 Update `step.module.css` with new section styles
    - Add styles for the tripartite section layout (input, operation, output)
    - Ensure consistent spacing and visual separation between sections
    - Remove unused styles from old step-specific views
    - _Requirements: 1.1, 2.6_

- [x] 8. Update step names and terminology alignment
  - [x] 8.1 Update all step name references in the frontend to use `STEP_CONFIG` names
    - Replace hardcoded `STEP_NAMES` constant in page.tsx with `STEP_CONFIG[n].name`
    - Ensure "Création dossier", "Préparation investigations", "Consolidation documentaire", "Production pré-rapport" are used consistently
    - Use labels "Entrée" and "Sortie" in section headings consistent with Site Central
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Integration testing and edge cases
  - [x]* 10.1 Write integration tests for the refactored StepViewPage
    - Test full page renders with ActionBanner, InputSection, OperationSection, OutputSection in correct order
    - Test step with no input files shows placeholder
    - Test step with no output files shows placeholder
    - Test file with unknown `file_type` appears in output section (fallback)
    - Test step in unexpected status defaults to button disabled
    - _Requirements: 1.1, 1.5, 1.6_

  - [x]* 10.2 Write property test for OCR input-to-output correspondence (Property 2)
    - **Property 2: OCR input-to-output file correspondence**
    - Generate random sets of input filenames with PDF/scan format for Step 1 and Step 3; verify output section contains exactly one `.md` file per OCR-processed input
    - Use fast-check (TypeScript) with minimum 100 iterations
    - **Validates: Requirements 4.2, 8.1**

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- This is a frontend-only refactoring — no backend changes required
- The existing `FileList` component is reused as-is; sections pre-filter files before passing them
- The existing `StepProgressList` component is reused for progress indication in OperationSection
- Property 3 (Directory tree creation invariant) is a backend concern already handled by existing code and is not included in frontend tasks
- fast-check is the PBT library for TypeScript frontend testing

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["2.2", "3.2", "4.3", "5.2"] },
    { "id": 1, "tasks": ["4.2", "10.1"] },
    { "id": 2, "tasks": ["10.2"] }
  ]
}
```
