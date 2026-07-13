/**
 * Property-based tests for OperationSection button disabled state.
 *
 * Property 4: Action button disabled state invariant
 * For any step number and for any combination of step status and dossier status,
 * the action button SHALL be disabled if and only if the step's statut is "en_cours"
 * OR "valide" OR the dossier's statut is "fermé". When disabled due to "en_cours",
 * a progress indicator SHALL be shown. When disabled due to lock/close, a lock
 * indicator SHALL be shown.
 *
 * **Validates: Requirements 13.5, 13.6**
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import fc from "fast-check";
import OperationSection from "./OperationSection";
import type { StepDetail } from "@/lib/api";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("./StepProgressList", () => ({
  default: ({ steps, active }: { steps: string[]; active: boolean }) => (
    <div data-testid="step-progress-list" data-active={active}>
      {steps.map((s, i) => (
        <span key={i}>{s}</span>
      ))}
    </div>
  ),
}));

vi.mock("./OperationSection.module.css", () => ({
  default: new Proxy({}, { get: (_target, prop) => String(prop) }),
}));

// ---------------------------------------------------------------------------
// Arbitraries
// ---------------------------------------------------------------------------

const stepNumberArb = fc.integer({ min: 1, max: 4 });
const stepStatutArb = fc.constantFrom("initial", "en_cours", "fait", "valide");
const dossierStatutArb = fc.constantFrom("actif", "fermé", "archive");

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeStep(stepNumber: number, statut: string): StepDetail {
  return {
    id: stepNumber,
    step_number: stepNumber,
    statut,
    executed_at: null,
    validated_at: null,
    files: [],
  };
}

// ---------------------------------------------------------------------------
// Property Tests
// ---------------------------------------------------------------------------

describe("OperationSection — Property 4: Action button disabled state invariant", () => {
  it("button is disabled iff statut is 'en_cours' or 'valide' or dossier is 'fermé'", () => {
    fc.assert(
      fc.property(
        stepNumberArb,
        stepStatutArb,
        dossierStatutArb,
        (stepNumber, statut, dossierStatut) => {
          const isDossierClosed = dossierStatut === "fermé";
          // isLocked is derived from statut === "valide" in real usage,
          // but the component uses isDossierClosed directly for the disabled logic
          const isLocked = statut === "valide";

          const { unmount } = render(
            <OperationSection
              stepNumber={stepNumber}
              dossierId="test-dossier"
              step={makeStep(stepNumber, statut)}
              isLocked={isLocked}
              isDossierClosed={isDossierClosed}
              onExecute={vi.fn().mockResolvedValue(undefined)}
              onCancel={vi.fn().mockResolvedValue(undefined)}
            />,
          );

          const shouldBeDisabled =
            statut === "en_cours" || statut === "valide" || isDossierClosed;

          if (statut === "en_cours") {
            // When "en_cours", the action button is HIDDEN (not rendered)
            // and a cancel button is shown instead
            const actionButton = screen.queryByRole("button", { name: /Extraire|Générer/ });
            expect(actionButton).toBeNull();
          } else {
            // Action button should be present
            const actionButton = screen.getByRole("button", { name: /Extraire|Générer/ });
            if (shouldBeDisabled) {
              expect(actionButton).toBeDisabled();
            } else {
              expect(actionButton).not.toBeDisabled();
            }
          }

          unmount();
        },
      ),
      { numRuns: 100 },
    );
  });

  it("progress indicator (StepProgressList) is shown when statut is 'en_cours'", () => {
    fc.assert(
      fc.property(
        stepNumberArb,
        stepStatutArb,
        dossierStatutArb,
        (stepNumber, statut, dossierStatut) => {
          const isDossierClosed = dossierStatut === "fermé";
          const isLocked = statut === "valide";

          const { unmount } = render(
            <OperationSection
              stepNumber={stepNumber}
              dossierId="test-dossier"
              step={makeStep(stepNumber, statut)}
              isLocked={isLocked}
              isDossierClosed={isDossierClosed}
              onExecute={vi.fn().mockResolvedValue(undefined)}
              onCancel={vi.fn().mockResolvedValue(undefined)}
            />,
          );

          const progressList = screen.queryByTestId("step-progress-list");

          if (statut === "en_cours") {
            expect(progressList).not.toBeNull();
            expect(progressList).toHaveAttribute("data-active", "true");
          } else {
            expect(progressList).toBeNull();
          }

          unmount();
        },
      ),
      { numRuns: 100 },
    );
  });

  it("lock indicator is shown when isLocked is true or isDossierClosed is true", () => {
    fc.assert(
      fc.property(
        stepNumberArb,
        stepStatutArb,
        dossierStatutArb,
        fc.boolean(),
        (stepNumber, statut, dossierStatut, isLockedOverride) => {
          const isDossierClosed = dossierStatut === "fermé";
          // Test with both derived lock state and explicit override
          const isLocked = isLockedOverride;

          const { unmount } = render(
            <OperationSection
              stepNumber={stepNumber}
              dossierId="test-dossier"
              step={makeStep(stepNumber, statut)}
              isLocked={isLocked}
              isDossierClosed={isDossierClosed}
              onExecute={vi.fn().mockResolvedValue(undefined)}
              onCancel={vi.fn().mockResolvedValue(undefined)}
            />,
          );

          const shouldShowLock = isLocked || isDossierClosed;

          const lockTextClosed = screen.queryByText(
            "Le dossier est fermé, aucune opération n'est possible.",
          );
          const lockTextLocked = screen.queryByText(
            "Cette étape est validée et verrouillée.",
          );

          if (shouldShowLock) {
            // At least one lock indicator text should be present
            const hasLockIndicator =
              lockTextClosed !== null || lockTextLocked !== null;
            expect(hasLockIndicator).toBe(true);

            // Verify the correct message is shown based on priority
            if (isDossierClosed) {
              expect(lockTextClosed).not.toBeNull();
            } else {
              expect(lockTextLocked).not.toBeNull();
            }
          } else {
            expect(lockTextClosed).toBeNull();
            expect(lockTextLocked).toBeNull();
          }

          unmount();
        },
      ),
      { numRuns: 100 },
    );
  });
});
