"use client";

import { useState, useEffect, useRef } from "react";
import { STEP_CONFIG } from "@/lib/stepConfig";
import type { StepDetail } from "@/lib/api";
import StepProgressList from "./StepProgressList";
import styles from "./OperationSection.module.css";

// ---------------------------------------------------------------------------
// Progress steps per step number
// ---------------------------------------------------------------------------

const PROGRESS_STEPS: Record<number, string[]> = {
  1: [
    "Étape 1/3 — OCR (extraction du texte)",
    "Étape 2/3 — Structuration, extraction questions et placeholders",
    "Étape 3/3 — Génération des documents (.md, .docx, questions.md, place_holders.csv)",
  ],
  2: [
    "Étape 1/3 — Récupération du TPE/TPA et du contexte RAG",
    "Étape 2/3 — Génération du Plan d'Entretien (PE) ou Plan d'Analyse (PA)",
    "Étape 3/3 — Génération des documents Word (.docx)",
  ],
  3: [
    "Étape 1/2 — OCR (extraction du texte des pièces de diligence)",
    "Étape 2/2 — Mise en forme pour validation",
  ],
  4: [
    "Étape 1/4 — Interprétation des annotations (@dires, @analyse, @question, @reference)",
    "Étape 2/4 — Substitution des placeholders dans le TRE",
    "Étape 3/4 — Génération du Pré-Rapport (PRE)",
    "Étape 4/4 — Génération du Document d'Analyse Contradictoire (DAC)",
  ],
  5: [
    "Étape 1/3 — Import du Rapport Final (REF)",
    "Étape 2/3 — Création de l'archive ZIP",
    "Étape 3/3 — Génération du timbre SHA-256",
  ],
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface OperationSectionProps {
  stepNumber: number;
  dossierId: string;
  step: StepDetail;
  isLocked: boolean;
  isDossierClosed: boolean;
  onExecute: () => Promise<void>;
  onCancel: () => Promise<void>;
  executionDuration?: number | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  if (mins === 0) return `${secs}s`;
  return `${mins}min ${secs.toString().padStart(2, "0")}s`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function OperationSection({
  stepNumber,
  dossierId,
  step,
  isLocked,
  isDossierClosed,
  onExecute,
  onCancel,
  executionDuration,
}: OperationSectionProps) {
  const config = STEP_CONFIG[stepNumber];
  if (!config) return null;

  const isProcessing = step.statut === "en_cours";
  const isValidated = step.statut === "valide";
  const isRealise = step.statut === "fait";
  const isInitial = step.statut === "initial";
  const showLockIndicator = isLocked || isDossierClosed;
  const progressSteps = PROGRESS_STEPS[stepNumber] ?? [];

  // Chrono progressif pendant le traitement
  const [elapsed, setElapsed] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (isProcessing) {
      setElapsed(0);
      intervalRef.current = setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isProcessing]);

  // Steps 4, 5: le bouton principal est dans InputSection (upload déclenche le traitement).
  // Step 1: upload séparé de l'exécution — le bouton "Extraire" est ici.
  // Steps 2, 3: bouton d'exécution classique.
  const isUploadStep = stepNumber === 4 || stepNumber === 5;
  const showValidateButton = (isUploadStep || stepNumber === 1) && isRealise && !isDossierClosed;
  const showExecuteButton = !isUploadStep && !isProcessing && !isRealise && !isValidated;
  const isButtonDisabled = isProcessing || isValidated || isDossierClosed;

  // Label du bouton selon le contexte
  let buttonLabel = config.buttonLabel;
  if (showValidateButton) {
    buttonLabel = "✓ Valider cette étape";
  }

  return (
    <div className={styles.section}>
      <h2 className={styles.heading}>Opération</h2>

      {/* Lock indicator */}
      {showLockIndicator && (
        <div className={styles.lockNotice}>
          <span aria-hidden="true">🔒</span>
          {isDossierClosed
            ? "Le dossier est fermé, aucune opération n'est possible."
            : "Cette étape est validée et verrouillée."}
        </div>
      )}

      {/* Progress indicator — sablier + étapes en cours + chrono */}
      {isProcessing && (
        <div className={styles.progressContainer}>
          <span className={styles.hourglass} aria-hidden="true">⏳</span>
          <div>
            <StepProgressList active steps={progressSteps} />
            <p className={styles.progressHint}>
              Traitement en cours… <strong>{formatDuration(elapsed)}</strong>
            </p>
          </div>
        </div>
      )}

      {/* Temps total d'exécution une fois terminé */}
      {(isRealise || isValidated) && executionDuration != null && executionDuration > 0 && (
        <p className={styles.durationInfo}>
          ⏱ Durée d&apos;exécution : <strong>{formatDuration(executionDuration)}</strong>
        </p>
      )}

      {/* Info pour les steps upload (4, 5) quand initial */}
      {isUploadStep && isInitial && !showLockIndicator && (
        <p className={styles.uploadHint}>
          ↑ Importez vos fichiers dans la section « Fichiers d&apos;entrée » ci-dessus pour lancer le traitement.
        </p>
      )}

      {/* Action buttons */}
      <div className={styles.actions}>
        {/* Bouton exécuter (Step 2, 3) ou valider (Step 1, 4, 5 quand fait) */}
        {(showExecuteButton || showValidateButton) && (
          <button
            type="button"
            className={showValidateButton ? styles.btnValidate : styles.btnPrimary}
            disabled={showExecuteButton ? (isProcessing || isValidated || isDossierClosed) : false}
            onClick={onExecute}
          >
            {buttonLabel}
          </button>
        )}

        {/* Bouton réinitialiser pendant le traitement */}
        {isProcessing && (
          <button
            type="button"
            className={styles.btnDanger}
            onClick={onCancel}
          >
            ✕ Réinitialiser cette étape
          </button>
        )}
      </div>
    </div>
  );
}
