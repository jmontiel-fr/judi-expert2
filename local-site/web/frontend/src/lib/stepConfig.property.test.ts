/**
 * Property-Based Test: File list rendering completeness (Property 1)
 *
 * Validates: Requirements 1.2, 1.4, 3.4, 5.3, 6.3, 7.3, 9.3
 *
 * For any step number (1–4) and for any set of files associated with that step,
 * every file whose file_type is classified as an input type for that step SHALL
 * appear in the Input result, and every file whose file_type is classified as an
 * output type SHALL appear in the Output result. No file shall be omitted or
 * duplicated across results.
 */

import { describe, it, expect } from "vitest";
import * as fc from "fast-check";
import { STEP_CONFIG, getInputFiles, getOutputFiles } from "./stepConfig";
import type { StepFileItem } from "./api";

// ---------------------------------------------------------------------------
// Generators
// ---------------------------------------------------------------------------

/** All known file_type values across all steps, plus some unknown types. */
const ALL_FILE_TYPES = [
  // Step 1 input
  "ordonnance",
  "complementaire",
  // Step 1 output
  "ordonnance_ocr",
  "questions",
  "docx",
  "complementaire_ocr",
  // Step 2 input
  "template_tpe",
  "template_tpa",
  // Step 2 output
  "trame_entretien",
  "courrier_diligence",
  "plan_analyse",
  // Step 3 input
  "diligence_response",
  // Step 3 output
  "diligence_ocr",
  // Step 4 input
  "trame_annotee",
  "notes_expert",
  "template_rapport",
  // Step 4 output
  "pre_rapport",
  "dac",
  // Unknown types (for fallback testing)
  "unknown_type",
  "random_file",
  "misc",
];

/** Arbitrary for a valid step number (1–4). */
const stepNumberArb = fc.integer({ min: 1, max: 4 });

/** Arbitrary for a file_type string drawn from known + unknown types. */
const fileTypeArb = fc.oneof(
  fc.constantFrom(...ALL_FILE_TYPES),
  fc.string({ minLength: 1, maxLength: 30 }).filter((s) => s.trim().length > 0),
);

/** Arbitrary for a single StepFileItem. */
const stepFileItemArb = (fileType: fc.Arbitrary<string>): fc.Arbitrary<StepFileItem> =>
  fc.record({
    id: fc.nat(),
    filename: fc.string({ minLength: 1, maxLength: 50 }),
    file_path: fc.string({ minLength: 1, maxLength: 100 }),
    file_type: fileType,
    file_size: fc.nat(),
    created_at: fc.constant("2024-01-01T00:00:00Z"),
    is_modified: fc.boolean(),
    original_file_path: fc.option(fc.string({ minLength: 1, maxLength: 100 }), { nil: null }),
    updated_at: fc.option(fc.constant("2024-01-02T00:00:00Z"), { nil: null }),
  });

/** Arbitrary for an array of StepFileItems with various file_types. */
const filesArb = fc.array(stepFileItemArb(fileTypeArb), { minLength: 0, maxLength: 30 });

// ---------------------------------------------------------------------------
// Property Tests
// ---------------------------------------------------------------------------

describe("Property 1: File list rendering completeness", () => {
  /**
   * **Validates: Requirements 1.2, 1.4, 3.4, 5.3, 6.3, 7.3, 9.3**
   *
   * For any step and any set of files, every file whose file_type is in
   * inputFileTypes appears in getInputFiles result with no omissions.
   */
  it("every file with an input file_type appears in getInputFiles result", () => {
    fc.assert(
      fc.property(stepNumberArb, filesArb, (stepNumber, files) => {
        const config = STEP_CONFIG[stepNumber];
        const result = getInputFiles(stepNumber, files);

        // Every file whose file_type is in inputFileTypes must appear in result
        const expectedInputFiles = files.filter((f) =>
          config.inputFileTypes.includes(f.file_type),
        );

        // No omissions: every expected file is in the result
        for (const expected of expectedInputFiles) {
          expect(result).toContain(expected);
        }

        // No extra files: result only contains files with input file_types
        for (const file of result) {
          expect(config.inputFileTypes).toContain(file.file_type);
        }

        // Same count (no duplicates introduced by the filter)
        expect(result.length).toBe(expectedInputFiles.length);
      }),
      { numRuns: 100 },
    );
  });

  /**
   * **Validates: Requirements 1.2, 1.4, 3.4, 5.3, 6.3, 7.3, 9.3**
   *
   * For any step and any set of files, every file whose file_type is in
   * outputFileTypes appears in getOutputFiles result with no omissions.
   */
  it("every file with an output file_type appears in getOutputFiles result", () => {
    fc.assert(
      fc.property(stepNumberArb, filesArb, (stepNumber, files) => {
        const config = STEP_CONFIG[stepNumber];
        const result = getOutputFiles(stepNumber, files);

        // Every file whose file_type is in outputFileTypes must appear in result
        const expectedOutputFiles = files.filter((f) =>
          config.outputFileTypes.includes(f.file_type),
        );

        for (const expected of expectedOutputFiles) {
          expect(result).toContain(expected);
        }
      }),
      { numRuns: 100 },
    );
  });

  /**
   * **Validates: Requirements 1.2, 1.4, 3.4, 5.3, 6.3, 7.3, 9.3**
   *
   * No duplicates in getInputFiles result — each file appears at most once.
   */
  it("getInputFiles produces no duplicates", () => {
    fc.assert(
      fc.property(stepNumberArb, filesArb, (stepNumber, files) => {
        const result = getInputFiles(stepNumber, files);
        const uniqueSet = new Set(result);
        expect(uniqueSet.size).toBe(result.length);
      }),
      { numRuns: 100 },
    );
  });

  /**
   * **Validates: Requirements 1.2, 1.4, 3.4, 5.3, 6.3, 7.3, 9.3**
   *
   * No duplicates in getOutputFiles result — each file appears at most once.
   */
  it("getOutputFiles produces no duplicates", () => {
    fc.assert(
      fc.property(stepNumberArb, filesArb, (stepNumber, files) => {
        const result = getOutputFiles(stepNumber, files);
        const uniqueSet = new Set(result);
        expect(uniqueSet.size).toBe(result.length);
      }),
      { numRuns: 100 },
    );
  });
});
