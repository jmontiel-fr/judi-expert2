"use client";

import { useEffect, useState } from "react";
import styles from "./StepProgressList.module.css";

interface StepProgressListProps {
  /** Labels for each sub-step, e.g. ["OCR (extraction)", "Structuration", "Génération Word"] */
  steps: string[];
  /** Whether the process is currently running */
  active: boolean;
  /** Approximate duration per step in ms (default: 8000) */
  stepDurationMs?: number;
}

/**
 * Displays a list of sub-steps with progress indicators:
 * - ✓ before completed steps
 * - → before the current step (animated)
 * - · before pending steps
 */
export default function StepProgressList({
  steps,
  active,
  stepDurationMs = 8000,
}: StepProgressListProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (!active) {
      setCurrentIndex(0);
      return;
    }

    const interval = setInterval(() => {
      setCurrentIndex((prev) => {
        // Stay on the last step (don't go past it)
        if (prev >= steps.length - 1) return prev;
        return prev + 1;
      });
    }, stepDurationMs);

    return () => clearInterval(interval);
  }, [active, steps.length, stepDurationMs]);

  // Reset when steps change
  useEffect(() => {
    setCurrentIndex(0);
  }, [steps]);

  return (
    <div className={styles.list}>
      {steps.map((label, i) => {
        const isDone = i < currentIndex;
        const isCurrent = i === currentIndex;

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
