"use client";

import type { StepFileItem } from "@/lib/api";
import { getOutputFiles } from "@/lib/stepConfig";
import FileList from "./FileList";
import styles from "./OutputSection.module.css";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface OutputSectionProps {
  stepNumber: number;
  dossierId: string;
  files: StepFileItem[];
  isLocked: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function OutputSection({
  stepNumber,
  dossierId,
  files,
  isLocked,
}: OutputSectionProps) {
  const outputFiles = getOutputFiles(stepNumber, files);

  return (
    <section className={styles.section} aria-labelledby="output-section-heading">
      <h2 id="output-section-heading" className={styles.heading}>
        Fichiers de sortie
      </h2>

      {outputFiles.length === 0 ? (
        <p className={styles.placeholder}>Aucun fichier de sortie généré</p>
      ) : (
        <FileList
          dossierId={dossierId}
          stepNumber={stepNumber}
          files={outputFiles}
          isLocked={isLocked}
          showReplaceButton={false}
        />
      )}
    </section>
  );
}
