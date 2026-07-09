"use client";

import { useState } from "react";
import { getStepConfig } from "@/lib/stepConfig";
import type { WorkflowType } from "@/lib/api";
import styles from "./ActionBanner.module.css";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ActionBannerProps {
  stepNumber: number;
  dossierName: string;
  workflowType?: WorkflowType;
}

export default function ActionBanner({ stepNumber, dossierName, workflowType = "standard" }: ActionBannerProps) {
  const config = getStepConfig(stepNumber, workflowType);
  const [expanded, setExpanded] = useState(false);

  if (!config) return null;

  const { description } = config;

  return (
    <div className={styles.banner} role="region" aria-label={`Description de l'étape ${stepNumber}`}>
      {/* Header — always visible, clickable to expand */}
      <button
        type="button"
        className={styles.header}
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
      >
        <span className={styles.label}>
          <span className={styles.labelIcon} aria-hidden="true">⚡</span>
          Étape {stepNumber}
        </span>
        <h3 className={styles.title}>{config.name}</h3>
        <span className={styles.chevron} aria-hidden="true">
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {/* Collapsible content */}
      {expanded && (
        <div className={styles.content}>
          {/* Objectif */}
          <div className={styles.block}>
            <span className={styles.blockLabel}>🎯 Objectif</span>
            <p className={styles.text}>{description.objectif}</p>
          </div>

          {/* Préparation */}
          {description.preparation && description.preparation.length > 0 && (
            <div className={styles.block}>
              <span className={styles.blockLabel}>📋 Préparation (avant déclenchement)</span>
              <ul className={styles.fileList}>
                {description.preparation.map((item, i) => (
                  <li key={i} className={styles.fileItem}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Entrées */}
          <div className={styles.block}>
            <span className={styles.blockLabel}>📥 Fichiers d&apos;entrée</span>
            <ul className={styles.fileList}>
              {description.entrees.map((entry, i) => (
                <li key={i} className={styles.fileItem}>{entry}</li>
              ))}
            </ul>
          </div>

          {/* Opération */}
          <div className={styles.block}>
            <span className={styles.blockLabel}>⚙️ Opération</span>
            <p className={styles.text}>{description.operation}</p>
          </div>

          {/* Sorties */}
          <div className={styles.block}>
            <span className={styles.blockLabel}>📤 Fichiers de sortie</span>
            <ul className={styles.fileList}>
              {description.sorties.map((entry, i) => (
                <li key={i} className={styles.fileItem}>{entry}</li>
              ))}
            </ul>
          </div>

          {/* Rôle expert */}
          <div className={styles.expertBlock}>
            <span className={styles.blockLabel}>👤 Votre rôle</span>
            <p className={styles.text}>{description.roleExpert}</p>
          </div>
        </div>
      )}
    </div>
  );
}
