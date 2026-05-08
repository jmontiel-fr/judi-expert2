/**
 * Property-Based Test: OCR input-to-output file correspondence (Property 2)
 *
 * Validates: Requirements 4.2, 8.1
 *
 * For any set of input files requiring OCR extraction (PDF/scan format) uploaded
 * to Step 1 or Step 3, the Output section (via getOutputFiles) SHALL contain
 * exactly one corresponding .md file for each input file that was processed.
 * The count of output .md files SHALL equal the count of input files that required OCR.
 */

import { describe, it, expect } from "vitest";
import * as fc from "fast-check";
import { STEP_CONFIG, getInputFiles, getOutputFiles } from "./stepConfig";
import type { StepFileItem } from "./api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Maps an OCR input file_type to its corresponding output file_type.
 * Step 1: ordonnance → ordonnance_ocr, complementaire → complementaire_ocr
 * Step 3: diligence_response → diligence_ocr
 */
const OCR_TYPE_MAP: Record<number, Record<string, string>> = {
  1: {
    ordonnance: "ordonnance_ocr",
    complementaire: "complementaire_ocr",
  },
  3: {
    diligence_response: "diligence_ocr",
  },
};

/** PDF/scan file extensions that require OCR processing. */
const OCR_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"];

// ---------------------------------------------------------------------------
// Generators
// ---------------------------------------------------------------------------

/** Arbitrary for a valid OCR step number (1 or 3). */
const ocrStepNumberArb = fc.constantFrom(1, 3);

/** Arbitrary for a PDF/scan filename extension. */
const ocrExtensionArb = fc.constantFrom(...OCR_EXTENSIONS);

/** Arbitrary for a base filename (alphanumeric, no extension). */
const baseFilenameArb = fc
  .stringMatching(/^[a-z][a-z0-9_-]{0,19}$/)
  .filter((s) => s.length > 0);

/**
 * Generates a set of OCR input files for a given step, each with a unique
 * base filename and a PDF/scan extension.
 */
function ocrInputFilesArb(stepNumber: fc.Arbitrary<number>) {
  return stepNumber.chain((step) => {
    const inputTypes = Object.keys(OCR_TYPE_MAP[step] || {});
    if (inputTypes.length === 0) return fc.constant({ step, inputFiles: [] as StepFileItem[] });

    const inputFileArb = fc.tuple(
      fc.constantFrom(...inputTypes),
      baseFilenameArb,
      ocrExtensionArb,
      fc.nat({ max: 10_000_000 }),
    ).map(([fileType, baseName, ext, size], idx) => ({
      id: idx,
      filename: `${baseName}${ext}`,
      file_path: `C:\\judi-expert\\dossier\\step${step}\\in\\${baseName}${ext}`,
      file_type: fileType,
      file_size: size,
      created_at: "2024-01-01T00:00:00Z",
      is_modified: false,
      original_file_path: null,
      updated_at: null,
    } as StepFileItem));

    return fc.array(inputFileArb, { minLength: 1, maxLength: 10 }).map((inputFiles) => ({
      step,
      inputFiles,
    }));
  });
}

/**
 * Given a list of OCR input files, generates the corresponding output .md files
 * with the correct output file_type.
 */
function buildCorrespondingOutputFiles(step: number, inputFiles: StepFileItem[]): StepFileItem[] {
  const typeMap = OCR_TYPE_MAP[step] || {};
  return inputFiles.map((inputFile, idx) => {
    const outputType = typeMap[inputFile.file_type];
    const baseName = inputFile.filename.replace(/\.[^.]+$/, "");
    return {
      id: 1000 + idx,
      filename: `${baseName}.md`,
      file_path: `C:\\judi-expert\\dossier\\step${step}\\out\\${baseName}.md`,
      file_type: outputType,
      file_size: inputFile.file_size,
      created_at: "2024-01-01T00:00:00Z",
      is_modified: false,
      original_file_path: null,
      updated_at: null,
    } as StepFileItem;
  });
}

// ---------------------------------------------------------------------------
// Property Tests
// ---------------------------------------------------------------------------

describe("Property 2: OCR input-to-output file correspondence", () => {
  /**
   * **Validates: Requirements 4.2, 8.1**
   *
   * For any set of OCR input files in Step 1 or Step 3, when corresponding
   * output .md files exist, getOutputFiles returns exactly one .md output
   * per OCR-processed input. The count of OCR output files equals the count
   * of OCR input files.
   */
  it("output contains exactly one .md file per OCR-processed input", () => {
    fc.assert(
      fc.property(ocrInputFilesArb(ocrStepNumberArb), ({ step, inputFiles }) => {
        // Build the corresponding output files for each input
        const outputFiles = buildCorrespondingOutputFiles(step, inputFiles);

        // Combine all files as the step would see them
        const allFiles = [...inputFiles, ...outputFiles];

        // Get the output files via the filtering function
        const result = getOutputFiles(step, allFiles);

        // Every generated output file should be in the result
        for (const outFile of outputFiles) {
          expect(result).toContainEqual(outFile);
        }

        // Count OCR output files in the result (files with OCR output types)
        const ocrOutputTypes = Object.values(OCR_TYPE_MAP[step] || {});
        const ocrOutputsInResult = result.filter((f) =>
          ocrOutputTypes.includes(f.file_type),
        );

        // The count of OCR output .md files must equal the count of OCR inputs
        expect(ocrOutputsInResult.length).toBe(inputFiles.length);
      }),
      { numRuns: 100 },
    );
  });

  /**
   * **Validates: Requirements 4.2, 8.1**
   *
   * For Step 1: each ordonnance/complementaire input produces exactly one
   * ordonnance_ocr/complementaire_ocr output respectively.
   */
  it("Step 1: each input type maps to its specific OCR output type", () => {
    fc.assert(
      fc.property(ocrInputFilesArb(fc.constant(1)), ({ step, inputFiles }) => {
        const outputFiles = buildCorrespondingOutputFiles(step, inputFiles);
        const allFiles = [...inputFiles, ...outputFiles];

        const result = getOutputFiles(step, allFiles);

        // For each input file, verify the corresponding output type exists in result
        for (const inputFile of inputFiles) {
          const expectedOutputType = OCR_TYPE_MAP[1][inputFile.file_type];
          const matchingOutputs = result.filter(
            (f) => f.file_type === expectedOutputType,
          );
          // At least one output of the expected type must exist
          expect(matchingOutputs.length).toBeGreaterThan(0);
        }

        // Count by type: ordonnance inputs → ordonnance_ocr outputs
        const ordonnanceInputCount = inputFiles.filter(
          (f) => f.file_type === "ordonnance",
        ).length;
        const ordonnanceOcrCount = result.filter(
          (f) => f.file_type === "ordonnance_ocr",
        ).length;
        expect(ordonnanceOcrCount).toBe(ordonnanceInputCount);

        // Count by type: complementaire inputs → complementaire_ocr outputs
        const complementaireInputCount = inputFiles.filter(
          (f) => f.file_type === "complementaire",
        ).length;
        const complementaireOcrCount = result.filter(
          (f) => f.file_type === "complementaire_ocr",
        ).length;
        expect(complementaireOcrCount).toBe(complementaireInputCount);
      }),
      { numRuns: 100 },
    );
  });

  /**
   * **Validates: Requirements 4.2, 8.1**
   *
   * For Step 3: each diligence_response input produces exactly one
   * diligence_ocr output.
   */
  it("Step 3: each diligence_response input maps to one diligence_ocr output", () => {
    fc.assert(
      fc.property(ocrInputFilesArb(fc.constant(3)), ({ step, inputFiles }) => {
        const outputFiles = buildCorrespondingOutputFiles(step, inputFiles);
        const allFiles = [...inputFiles, ...outputFiles];

        const result = getOutputFiles(step, allFiles);

        // Count diligence_ocr outputs must equal diligence_response inputs
        const diligenceOcrCount = result.filter(
          (f) => f.file_type === "diligence_ocr",
        ).length;
        expect(diligenceOcrCount).toBe(inputFiles.length);
      }),
      { numRuns: 100 },
    );
  });

  /**
   * **Validates: Requirements 4.2, 8.1**
   *
   * OCR input files (from getInputFiles) should NOT appear in the output
   * section — they are strictly inputs.
   */
  it("OCR input files do not appear in getOutputFiles result", () => {
    fc.assert(
      fc.property(ocrInputFilesArb(ocrStepNumberArb), ({ step, inputFiles }) => {
        const outputFiles = buildCorrespondingOutputFiles(step, inputFiles);
        const allFiles = [...inputFiles, ...outputFiles];

        const inputResult = getInputFiles(step, allFiles);
        const outputResult = getOutputFiles(step, allFiles);

        // No input file should appear in the output result
        for (const inputFile of inputResult) {
          expect(outputResult).not.toContainEqual(inputFile);
        }
      }),
      { numRuns: 100 },
    );
  });
});
