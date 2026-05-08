/**
 * Unit tests for InputSection component.
 *
 * Validates: Requirements 1.6, 5.2
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import InputSection from "./InputSection";
import type { StepFileItem } from "@/lib/api";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Mock the API module to avoid real network calls
vi.mock("@/lib/api", () => ({
  step1Api: { extract: vi.fn(), uploadComplementary: vi.fn() },
  step3Api: { upload: vi.fn() },
  step4Api: { execute: vi.fn() },
  step5Api: { execute: vi.fn() },
  getErrorMessage: vi.fn((err: unknown, fallback: string) => fallback),
}));

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
vi.mock("./InputSection.module.css", () => ({
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
  dossierStatut: "en_cours",
  onFileUploaded: vi.fn().mockResolvedValue(undefined),
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("InputSection", () => {
  describe("Placeholder message when no input files exist (Requirement 1.6)", () => {
    it("shows placeholder when files array is empty", () => {
      render(
        <InputSection
          {...defaultProps}
          stepNumber={1}
          files={[]}
        />,
      );

      expect(screen.getByText("Aucun fichier d'entrée disponible")).toBeInTheDocument();
    });

    it("shows placeholder when files exist but none match input types for the step", () => {
      // Step 1 input types: ordonnance, complementaire
      // Provide only output-type files
      const files: StepFileItem[] = [
        makeFile({ id: 1, filename: "ordonnance.md", file_type: "ordonnance_ocr" }),
        makeFile({ id: 2, filename: "questions.md", file_type: "questions" }),
      ];

      render(
        <InputSection
          {...defaultProps}
          stepNumber={1}
          files={files}
        />,
      );

      expect(screen.getByText("Aucun fichier d'entrée disponible")).toBeInTheDocument();
    });
  });

  describe("Only input-classified files are displayed", () => {
    it("displays only input files for Step 1 (ordonnance, complementaire)", () => {
      const files: StepFileItem[] = [
        makeFile({ id: 1, filename: "ordonnance.pdf", file_type: "ordonnance" }),
        makeFile({ id: 2, filename: "piece-01.pdf", file_type: "complementaire" }),
        makeFile({ id: 3, filename: "ordonnance.md", file_type: "ordonnance_ocr" }),
        makeFile({ id: 4, filename: "questions.md", file_type: "questions" }),
      ];

      render(
        <InputSection
          {...defaultProps}
          stepNumber={1}
          files={files}
        />,
      );

      // Input files should be displayed
      expect(screen.getByTestId("file-1")).toHaveTextContent("ordonnance.pdf");
      expect(screen.getByTestId("file-2")).toHaveTextContent("piece-01.pdf");

      // Output files should NOT be displayed
      expect(screen.queryByTestId("file-3")).not.toBeInTheDocument();
      expect(screen.queryByTestId("file-4")).not.toBeInTheDocument();
    });

    it("displays only input files for Step 3 (diligence_response)", () => {
      const files: StepFileItem[] = [
        makeFile({ id: 1, filename: "diligence-01.pdf", file_type: "diligence_response" }),
        makeFile({ id: 2, filename: "diligence-01.md", file_type: "diligence_ocr" }),
      ];

      render(
        <InputSection
          {...defaultProps}
          stepNumber={3}
          files={files}
        />,
      );

      expect(screen.getByTestId("file-1")).toHaveTextContent("diligence-01.pdf");
      expect(screen.queryByTestId("file-2")).not.toBeInTheDocument();
    });
  });

  describe("Upload controls are hidden when locked", () => {
    it("hides Step 1 upload controls when isLocked is true", () => {
      render(
        <InputSection
          {...defaultProps}
          stepNumber={1}
          files={[]}
          isLocked={true}
        />,
      );

      // Upload area should not be present
      expect(screen.queryByText("Import des pièces constitutives")).not.toBeInTheDocument();
    });

    it("hides Step 3 upload controls when isLocked is true", () => {
      render(
        <InputSection
          {...defaultProps}
          stepNumber={3}
          files={[]}
          isLocked={true}
        />,
      );

      expect(screen.queryByText("Import des rapports de diligence")).not.toBeInTheDocument();
    });

    it("hides upload controls when dossier is closed (fermé)", () => {
      render(
        <InputSection
          {...defaultProps}
          stepNumber={1}
          files={[]}
          dossierStatut="fermé"
        />,
      );

      expect(screen.queryByText("Import des pièces constitutives")).not.toBeInTheDocument();
    });

    it("shows Step 1 upload controls when not locked and dossier is open", () => {
      render(
        <InputSection
          {...defaultProps}
          stepNumber={1}
          files={[]}
          isLocked={false}
          dossierStatut="en_cours"
        />,
      );

      expect(screen.getByText("Import des pièces constitutives")).toBeInTheDocument();
    });

    it("shows Step 3 upload controls when not locked and dossier is open", () => {
      render(
        <InputSection
          {...defaultProps}
          stepNumber={3}
          files={[]}
          isLocked={false}
          dossierStatut="en_cours"
        />,
      );

      expect(screen.getByText("Import des rapports de diligence")).toBeInTheDocument();
    });
  });

  describe("Step 2 mode-dependent template display (Requirement 5.2)", () => {
    it("displays TPE template info in Mode Entretien", () => {
      render(
        <InputSection
          {...defaultProps}
          stepNumber={2}
          files={[]}
          mode="entretien"
        />,
      );

      expect(screen.getByText("TPE")).toBeInTheDocument();
      expect(screen.getByText(/Template de Plan d'Entretien/)).toBeInTheDocument();
    });

    it("displays TPA template info in Mode Analyse", () => {
      render(
        <InputSection
          {...defaultProps}
          stepNumber={2}
          files={[]}
          mode="analyse"
        />,
      );

      expect(screen.getByText("TPA")).toBeInTheDocument();
      expect(screen.getByText(/Template de Plan d'Analyse/)).toBeInTheDocument();
    });

    it("defaults to TPE when mode is undefined (Step 2)", () => {
      render(
        <InputSection
          {...defaultProps}
          stepNumber={2}
          files={[]}
        />,
      );

      expect(screen.getByText("TPE")).toBeInTheDocument();
      expect(screen.getByText(/Template de Plan d'Entretien/)).toBeInTheDocument();
    });

    it("does not display template info for non-Step 2 steps", () => {
      render(
        <InputSection
          {...defaultProps}
          stepNumber={1}
          files={[]}
        />,
      );

      expect(screen.queryByText("TPE")).not.toBeInTheDocument();
      expect(screen.queryByText("TPA")).not.toBeInTheDocument();
    });
  });
});
