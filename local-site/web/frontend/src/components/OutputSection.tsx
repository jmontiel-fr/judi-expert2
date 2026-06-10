"use client";

import type { StepFileItem, WorkflowType } from "@/lib/api";
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
  workflowType?: WorkflowType;
}

export default function OutputSection({
  stepNumber,
  dossierId,
  files,
  isLocked,
  workflowType = "standard",
}: OutputSectionProps) {
  const outputFiles = getOutputFiles(stepNumber, files, workflowType);

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
