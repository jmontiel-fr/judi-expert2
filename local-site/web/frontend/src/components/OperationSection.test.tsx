/**
 * Unit tests for OperationSection component.
 *
 * Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5, 13.6
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import OperationSection from "./OperationSection";
import type { StepDetail } from "@/lib/api";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Mock StepProgressList to simplify assertions
vi.mock("./StepProgressList", () => ({
  default: ({ steps, active }: { steps: string[]; active: boolean }) => (
    <div data-testid="step-progress-list" data-active={active}>
      {steps.map((s, i) => (
        <span key={i}>{s}</span>
      ))}
    </div>
  ),
}));

// Mock CSS module
vi.mock("./OperationSection.module.css", () => ({
  default: new Proxy({}, { get: (_target, prop) => String(prop) }),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeStep(overrides: Partial<StepDetail> = {}): StepDetail {
  return {
    id: 1,
    step_number: 1,
    statut: "initial",
    executed_at: null,
    validated_at: null,
    files: [],
    ...overrides,
  };
}

const defaultProps = {
  dossierId: "dossier-1",
  step: makeStep(),
  isLocked: false,
  isDossierClosed: false,
  onExecute: vi.fn().mockResolvedValue(undefined),
  onCancel: vi.fn().mockResolvedValue(undefined),
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("OperationSection", () => {
  describe("Correct button label for each step (Requirements 13.1, 13.2, 13.3, 13.4)", () => {
    it("Step 1 displays button labeled 'Extraire et structurer'", () => {
      render(
        <OperationSection
          {...defaultProps}
          stepNumber={1}
          step={makeStep({ step_number: 1, statut: "initial" })}
        />,
      );

      expect(screen.getByRole("button", { name: "Extraire et structurer" })).toBeInTheDocument();
    });

    it("Step 2 displays button labeled 'Générer le plan'", () => {
      render(
        <OperationSection
          {...defaultProps}
          stepNumber={2}
          step={makeStep({ step_number: 2, statut: "initial" })}
        />,
      );

      expect(screen.getByRole("button", { name: "Générer le plan" })).toBeInTheDocument();
    });

    it("Step 3 displays button labeled 'Extraire les documents'", () => {
      render(
        <OperationSection
          {...defaultProps}
          stepNumber={3}
          step={makeStep({ step_number: 3, statut: "initial" })}
        />,
      );

      expect(screen.getByRole("button", { name: "Extraire les documents" })).toBeInTheDocument();
    });

    it("Step 4 displays button labeled 'Générer le pré-rapport'", () => {
      render(
        <OperationSection
          {...defaultProps}
          stepNumber={4}
          step={makeStep({ step_number: 4, statut: "initial" })}
        />,
      );

      expect(screen.getByRole("button", { name: "Générer le pré-rapport" })).toBeInTheDocument();
    });
  });

  describe("Progress indicator during 'en_cours' (Requirement 13.5)", () => {
    it("renders StepProgressList when step statut is 'en_cours'", () => {
      render(
        <OperationSection
          {...defaultProps}
          stepNumber={1}
          step={makeStep({ step_number: 1, statut: "en_cours" })}
        />,
      );

      expect(screen.getByTestId("step-progress-list")).toBeInTheDocument();
      expect(screen.getByTestId("step-progress-list")).toHaveAttribute("data-active", "true");
    });

    it("does not render StepProgressList when step statut is 'initial'", () => {
      render(
        <OperationSection
          {...defaultProps}
          stepNumber={1}
          step={makeStep({ step_number: 1, statut: "initial" })}
        />,
      );

      expect(screen.queryByTestId("step-progress-list")).not.toBeInTheDocument();
    });

    it("does not render StepProgressList when step statut is 'fait'", () => {
      render(
        <OperationSection
          {...defaultProps}
          stepNumber={2}
          step={makeStep({ step_number: 2, statut: "fait" })}
        />,
      );

      expect(screen.queryByTestId("step-progress-list")).not.toBeInTheDocument();
    });

    it("shows cancel button during processing", () => {
      render(
        <OperationSection
          {...defaultProps}
          stepNumber={1}
          step={makeStep({ step_number: 1, statut: "en_cours" })}
        />,
      );

      expect(screen.getByRole("button", { name: /Annuler/ })).toBeInTheDocument();
    });

    it("hides the action button during processing", () => {
      render(
        <OperationSection
          {...defaultProps}
          stepNumber={1}
          step={makeStep({ step_number: 1, statut: "en_cours" })}
        />,
      );

      expect(screen.queryByRole("button", { name: "Extraire et structurer" })).not.toBeInTheDocument();
    });
  });

  describe("Lock indicator when locked (Requirement 13.6)", () => {
    it("renders lock indicator when isLocked is true", () => {
      render(
        <OperationSection
          {...defaultProps}
          stepNumber={1}
          step={makeStep({ step_number: 1, statut: "initial" })}
          isLocked={true}
        />,
      );

      expect(screen.getByText("Cette étape est validée et verrouillée.")).toBeInTheDocument();
    });

    it("renders lock indicator when dossier is closed", () => {
      render(
        <OperationSection
          {...defaultProps}
          stepNumber={2}
          step={makeStep({ step_number: 2, statut: "initial" })}
          isDossierClosed={true}
        />,
      );

      expect(screen.getByText("Le dossier est fermé, aucune opération n'est possible.")).toBeInTheDocument();
    });

    it("does not render lock indicator when not locked and dossier is open", () => {
      render(
        <OperationSection
          {...defaultProps}
          stepNumber={1}
          step={makeStep({ step_number: 1, statut: "initial" })}
          isLocked={false}
          isDossierClosed={false}
        />,
      );

      expect(screen.queryByText("Cette étape est validée et verrouillée.")).not.toBeInTheDocument();
      expect(screen.queryByText("Le dossier est fermé, aucune opération n'est possible.")).not.toBeInTheDocument();
    });

    it("disables the action button when locked", () => {
      render(
        <OperationSection
          {...defaultProps}
          stepNumber={3}
          step={makeStep({ step_number: 3, statut: "initial" })}
          isLocked={true}
          isDossierClosed={true}
        />,
      );

      expect(screen.getByRole("button", { name: "Extraire les documents" })).toBeDisabled();
    });
  });
});
