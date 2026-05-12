"use client";

import styles from "./StepProgressList.module.css";

interface StepProgressListProps {
  /** Labels for each sub-step, e.g. ["OCR (extraction)", "Structuration", "Génération Word"] */
  steps: string[];
  /** Whether the process is currently running */
  active: boolean;
  /** Current step index (1-based) from backend. If provided, overrides internal timer. */
  currentStep?: number;
}

/**
 * Displays a list of sub-steps with progress indicators:
 * - ✓ before completed steps
 * - → before the current step (animated)
 * - · before pending steps
 *
 * Uses `currentStep` from backend (polled every 5s) to show real progression.
 */
export default function StepProgressList({
  steps,
  active,
  currentStep,
}: StepProgressListProps) {
  // currentStep is 1-based from backend, convert to 0-based index
  // If null/undefined, show all steps as pending (no highlight)
  const currentIndex = currentStep != null ? Math.min(currentStep - 1, steps.length - 1) : -1;

  if (!active) return null;

  return (
    <div className={styles.list}>
      {steps.map((label, i) => {
        const isDone = currentIndex >= 0 && i < currentIndex;
        const isCurrent = currentIndex >= 0 && i === currentIndex;

        return (
          <div
            key={i}
            className={`${styles.item} ${isDone ? styles.done : ""} ${isCurrent ? styles.current : ""} ${!isDone && !isCurrent ? styles.pending : ""}`}
          >
            <span className={styles.indicator} aria-hidden="true">
              {isDone ? "✓" : isCurrent ? "→" : "·"}
            </span>
            <span>{label}</span>
          </div>
        );
      })}
    </div>
  );
}
