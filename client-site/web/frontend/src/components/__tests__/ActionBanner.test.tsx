/**
 * Unit Tests: ActionBanner component
 *
 * Validates: Requirements 2.2, 2.3, 2.4, 2.5, 2.6
 *
 * Verifies that each step (1–5) renders the structured description block
 * with objectif, entrées, opération, sorties, and rôle expert.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ActionBanner from "../ActionBanner";
import { STEP_CONFIG } from "@/lib/stepConfig";

describe("ActionBanner", () => {
  const TEST_DOSSIER_NAME = "Dupont-2024";

  // -------------------------------------------------------------------------
  // Step 1: Structured description
  // -------------------------------------------------------------------------
  describe("Step 1 description block", () => {
    it("renders the step name", () => {
      render(<ActionBanner stepNumber={1} dossierName={TEST_DOSSIER_NAME} />);
      expect(screen.getByText("Création dossier")).toBeInTheDocument();
    });

    it("renders the objectif", () => {
      render(<ActionBanner stepNumber={1} dossierName={TEST_DOSSIER_NAME} />);
      expect(screen.getByText(STEP_CONFIG[1].description.objectif)).toBeInTheDocument();
    });

    it("renders input files", () => {
      render(<ActionBanner stepNumber={1} dossierName={TEST_DOSSIER_NAME} />);
      expect(screen.getByText(/ordonnance\.pdf/)).toBeInTheDocument();
    });

    it("renders output files", () => {
      render(<ActionBanner stepNumber={1} dossierName={TEST_DOSSIER_NAME} />);
      expect(screen.getByText(/questions\.md/)).toBeInTheDocument();
      expect(screen.getByText(/place_holders\.csv/)).toBeInTheDocument();
    });

    it("renders the expert role", () => {
      render(<ActionBanner stepNumber={1} dossierName={TEST_DOSSIER_NAME} />);
      expect(screen.getByText(STEP_CONFIG[1].description.roleExpert)).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Step 2: Structured description
  // -------------------------------------------------------------------------
  describe("Step 2 description block", () => {
    it("renders the step name", () => {
      render(<ActionBanner stepNumber={2} dossierName={TEST_DOSSIER_NAME} />);
      expect(screen.getByText("Préparation investigations")).toBeInTheDocument();
    });

    it("renders the objectif", () => {
      render(<ActionBanner stepNumber={2} dossierName={TEST_DOSSIER_NAME} />);
      expect(screen.getByText(STEP_CONFIG[2].description.objectif)).toBeInTheDocument();
    });

    it("renders output files mentioning PE and PA", () => {
      render(<ActionBanner stepNumber={2} dossierName={TEST_DOSSIER_NAME} />);
      expect(screen.getByText(/pe\.md, pe\.docx/)).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Step 3: Structured description
  // -------------------------------------------------------------------------
  describe("Step 3 description block", () => {
    it("renders the step name", () => {
      render(<ActionBanner stepNumber={3} dossierName={TEST_DOSSIER_NAME} />);
      expect(screen.getByText("Consolidation documentaire")).toBeInTheDocument();
    });

    it("renders the objectif", () => {
      render(<ActionBanner stepNumber={3} dossierName={TEST_DOSSIER_NAME} />);
      expect(screen.getByText(STEP_CONFIG[3].description.objectif)).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Step 4: Structured description
  // -------------------------------------------------------------------------
  describe("Step 4 description block", () => {
    it("renders the step name", () => {
      render(<ActionBanner stepNumber={4} dossierName={TEST_DOSSIER_NAME} />);
      expect(screen.getByText("Production pré-rapport")).toBeInTheDocument();
    });

    it("renders output files mentioning PRE and DAC", () => {
      render(<ActionBanner stepNumber={4} dossierName={TEST_DOSSIER_NAME} />);
      expect(screen.getByText(/pre\.docx/)).toBeInTheDocument();
      expect(screen.getByText(/dac\.docx/)).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Step 5: Structured description
  // -------------------------------------------------------------------------
  describe("Step 5 description block", () => {
    it("renders the step name", () => {
      render(<ActionBanner stepNumber={5} dossierName={TEST_DOSSIER_NAME} />);
      expect(screen.getByText("Finalisation et archivage")).toBeInTheDocument();
    });

    it("renders the objectif", () => {
      render(<ActionBanner stepNumber={5} dossierName={TEST_DOSSIER_NAME} />);
      expect(screen.getByText(STEP_CONFIG[5].description.objectif)).toBeInTheDocument();
    });

    it("renders output files mentioning ZIP and timbre", () => {
      render(<ActionBanner stepNumber={5} dossierName={TEST_DOSSIER_NAME} />);
      expect(screen.getByText(/\.zip/)).toBeInTheDocument();
      expect(screen.getByText(/timbre/)).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Common: label and icon
  // -------------------------------------------------------------------------
  describe("Label and icon", () => {
    it("renders the lightning bolt icon", () => {
      render(<ActionBanner stepNumber={1} dossierName={TEST_DOSSIER_NAME} />);
      expect(screen.getByText("⚡")).toBeInTheDocument();
    });

    it("renders the step number in the label", () => {
      render(<ActionBanner stepNumber={3} dossierName={TEST_DOSSIER_NAME} />);
      expect(screen.getByText("Étape 3")).toBeInTheDocument();
    });

    it("has a region role with appropriate aria-label", () => {
      render(<ActionBanner stepNumber={2} dossierName={TEST_DOSSIER_NAME} />);
      expect(screen.getByRole("region", { name: "Description de l'étape 2" })).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Edge case: invalid step number
  // -------------------------------------------------------------------------
  describe("Edge cases", () => {
    it("renders nothing for an invalid step number", () => {
      const { container } = render(<ActionBanner stepNumber={99} dossierName={TEST_DOSSIER_NAME} />);
      expect(container.innerHTML).toBe("");
    });
  });
});
