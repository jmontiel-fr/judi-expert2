/**
 * Unit tests for OutputSection component.
 *
 * Validates: Requirements 1.5, 8.3
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import OutputSection from "./OutputSection";
import type { StepFileItem } from "@/lib/api";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Mock the FileList component to simplify assertions
vi.mock("@/components/FileList", () => ({
  default: ({ files }: { files: StepFileItem[] }) => (
    <ul data-testid="file-list">
      {files.map((f) => (
        <li key={f.id} data-testid={`file-${f.id}`}>
          {f.filename}
        </li>
      ))}
    </ul>
  ),
}));

// Mock CSS module
vi.mock("./OutputSection.module.css", () => ({
  default: new Proxy({}, { get: (_target, prop) => String(prop) }),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeFile(overrides: Partial<StepFileItem> & { id: number; filename: string; file_type: string }): StepFileItem {
  return {
    file_path: `/path/${overrides.filename}`,
    file_size: 1024,
    created_at: "2024-01-01T00:00:00Z",
    is_modified: false,
    original_file_path: null,
    updated_at: null,
    ...overrides,
  };
}

const defaultProps = {
  dossierId: "dossier-1",
  isLocked: false,
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("OutputSection", () => {
  describe("Placeholder message when no output files exist (Requirement 1.5)", () => {
    it("shows placeholder when files array is empty", () => {
      render(
        <OutputSection
          {...defaultProps}
          stepNumber={1}
          files={[]}
        />,
      );

      expect(screen.getByText("Aucun fichier de sortie généré")).toBeInTheDocument();
    });

    it("shows placeholder when files exist but none match output types for the step", () => {
      // Step 1 output types: ordonnance_ocr, questions, docx, complementaire_ocr
      // Step 1 input types: ordonnance, complementaire
      // Provide only input-type files — these are in inputFileTypes so they won't appear in output
      const files: StepFileItem[] = [
        makeFile({ id: 1, filename: "ordonnance.pdf", file_type: "ordonnance" }),
        makeFile({ id: 2, filename: "piece-01.pdf", file_type: "complementaire" }),
      ];

      render(
        <OutputSection
          {...defaultProps}
          stepNumber={1}
          files={files}
        />,
      );

      expect(screen.getByText("Aucun fichier de sortie généré")).toBeInTheDocument();
    });
  });

  describe("Only output-classified files are displayed", () => {
    it("displays only output files for Step 1 (ordonnance_ocr, questions, docx, complementaire_ocr)", () => {
      const files: StepFileItem[] = [
        // Input files (should NOT appear)
        makeFile({ id: 1, filename: "ordonnance.pdf", file_type: "ordonnance" }),
        makeFile({ id: 2, filename: "piece-01.pdf", file_type: "complementaire" }),
        // Output files (should appear)
        makeFile({ id: 3, filename: "ordonnance.md", file_type: "ordonnance_ocr" }),
        makeFile({ id: 4, filename: "questions.md", file_type: "questions" }),
      ];

      render(
        <OutputSection
          {...defaultProps}
          stepNumber={1}
          files={files}
        />,
      );

      // Output files should be displayed
      expect(screen.getByTestId("file-3")).toHaveTextContent("ordonnance.md");
      expect(screen.getByTestId("file-4")).toHaveTextContent("questions.md");

      // Input files should NOT be displayed
      expect(screen.queryByTestId("file-1")).not.toBeInTheDocument();
      expect(screen.queryByTestId("file-2")).not.toBeInTheDocument();
    });

    it("displays only output files for Step 3 (diligence_ocr)", () => {
      const files: StepFileItem[] = [
        makeFile({ id: 1, filename: "diligence-01.pdf", file_type: "diligence_response" }),
        makeFile({ id: 2, filename: "diligence-01.md", file_type: "diligence_ocr" }),
      ];

      render(
        <OutputSection
          {...defaultProps}
          stepNumber={3}
          files={files}
        />,
      );

      // Output file should be displayed
      expect(screen.getByTestId("file-2")).toHaveTextContent("diligence-01.md");

      // Input file should NOT be displayed
      expect(screen.queryByTestId("file-1")).not.toBeInTheDocument();
    });

    it("displays only output files for Step 4 (pre_rapport, dac)", () => {
      const files: StepFileItem[] = [
        // Input files
        makeFile({ id: 1, filename: "trame.docx", file_type: "trame_annotee" }),
        makeFile({ id: 2, filename: "notes.md", file_type: "notes_expert" }),
        // Output files
        makeFile({ id: 3, filename: "pre-rapport.docx", file_type: "pre_rapport" }),
        makeFile({ id: 4, filename: "dac.docx", file_type: "dac" }),
      ];

      render(
        <OutputSection
          {...defaultProps}
          stepNumber={4}
          files={files}
        />,
      );

      // Output files should be displayed
      expect(screen.getByTestId("file-3")).toHaveTextContent("pre-rapport.docx");
      expect(screen.getByTestId("file-4")).toHaveTextContent("dac.docx");

      // Input files should NOT be displayed
      expect(screen.queryByTestId("file-1")).not.toBeInTheDocument();
      expect(screen.queryByTestId("file-2")).not.toBeInTheDocument();
    });
  });

  describe("Unknown file_type fallback behavior (Requirement 8.3)", () => {
    it("displays files with unknown file_type in the output section (fallback)", () => {
      const files: StepFileItem[] = [
        makeFile({ id: 1, filename: "ordonnance.pdf", file_type: "ordonnance" }),
        makeFile({ id: 2, filename: "mystery-file.txt", file_type: "unknown_type" }),
      ];

      render(
        <OutputSection
          {...defaultProps}
          stepNumber={1}
          files={files}
        />,
      );

      // Unknown file_type should appear in output (fallback: not in inputFileTypes)
      expect(screen.getByTestId("file-2")).toHaveTextContent("mystery-file.txt");

      // Known input file should NOT appear
      expect(screen.queryByTestId("file-1")).not.toBeInTheDocument();
    });

    it("displays files with completely novel file_type in output section", () => {
      const files: StepFileItem[] = [
        makeFile({ id: 1, filename: "random-doc.pdf", file_type: "never_seen_before" }),
      ];

      render(
        <OutputSection
          {...defaultProps}
          stepNumber={2}
          files={files}
        />,
      );

      // Novel file_type is not in Step 2 inputFileTypes, so it appears in output
      expect(screen.getByTestId("file-1")).toHaveTextContent("random-doc.pdf");
    });

    it("displays unknown file_type alongside known output files", () => {
      const files: StepFileItem[] = [
        makeFile({ id: 1, filename: "diligence-01.md", file_type: "diligence_ocr" }),
        makeFile({ id: 2, filename: "extra-file.pdf", file_type: "unexpected_format" }),
        makeFile({ id: 3, filename: "diligence-01.pdf", file_type: "diligence_response" }),
      ];

      render(
        <OutputSection
          {...defaultProps}
          stepNumber={3}
          files={files}
        />,
      );

      // Known output file
      expect(screen.getByTestId("file-1")).toHaveTextContent("diligence-01.md");
      // Unknown type (fallback to output)
      expect(screen.getByTestId("file-2")).toHaveTextContent("extra-file.pdf");
      // Known input file should NOT appear
      expect(screen.queryByTestId("file-3")).not.toBeInTheDocument();
    });
  });
});
