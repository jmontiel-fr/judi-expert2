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
    "Étape 1/5 — OCR (extraction du texte)",
    "Étape 2/5 — Structuration en Markdown (LLM)",
    "Étape 3/5 — Extraction des questions (LLM)",
    "Étape 4/5 — Extraction des placeholders (LLM)",
    "Étape 5/5 — Sauvegarde des fichiers (demande.md, placeholders.csv)",
  ],
  2: [
    "Étape 1/4 — Validation syntaxique du TRE (annotations, placeholders)",
    "Étape 2/4 — Extraction du Plan d'Entretien depuis le TRE",
    "Étape 3/4 — Intégration des questions en conclusion",
    "Étape 4/4 — Sauvegarde du PE (.docx)",
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
  onSkip?: () => Promise<void>;
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
  onSkip,
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

  // Chrono progressif pendant le traitement — calcule depuis executed_at
  const [elapsed, setElapsed] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (isProcessing && step.executed_at) {
      // Calculer le temps déjà écoulé depuis executed_at
      // Ajouter 'Z' si pas de timezone (le backend stocke en UTC sans suffixe)
      const isoDate = step.executed_at.endsWith("Z") || step.executed_at.includes("+")
        ? step.executed_at
        : step.executed_at + "Z";
      const startTime = new Date(isoDate).getTime();
      const initialElapsed = Math.max(0, Math.floor((Date.now() - startTime) / 1000));
      setElapsed(initialElapsed);

      intervalRef.current = setInterval(() => {
        setElapsed(Math.max(0, Math.floor((Date.now() - startTime) / 1000)));
      }, 1000);
    } else {
      setElapsed(0);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isProcessing, step.executed_at]);

  // Steps 4, 5: le bouton principal est dans InputSection (upload déclenche le traitement).
  // Step 1: upload séparé de l'exécution — le bouton "Extraire" est ici.
  // Steps 2, 3: bouton d'exécution classique.
  const isUploadStep = stepNumber === 5;
  const showValidateButton = (isUploadStep || stepNumber === 1 || stepNumber === 2 || stepNumber === 3) && isRealise && !isDossierClosed;
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
            <StepProgressList
              active
              steps={progressSteps}
              currentStep={step.progress_current ?? undefined}
            />
            {step.progress_message && (
              <p style={{ fontSize: "0.8rem", color: "#2563eb", margin: "4px 0" }}>
                {step.progress_message}
              </p>
            )}
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

        {/* Bouton réinitialiser — visible dès qu'il y a quelque chose à réinitialiser (pas validé, pas dossier fermé) */}
        {(isProcessing || isRealise || isInitial) && !isValidated && !isDossierClosed && (
          <button
            type="button"
            className={styles.btnDanger}
            onClick={onCancel}
          >
            ✕ Réinitialiser cette étape
          </button>
        )}

        {/* Bouton "Sans objet" pour le Step 3 quand initial (pas de pièces à consolider) */}
        {stepNumber === 3 && isInitial && !isDossierClosed && onSkip && (
          <button
            type="button"
            className={styles.btnValidate}
            onClick={onSkip}
            style={{ backgroundColor: "#6b7280" }}
          >
            Sans objet — Valider sans pièces
          </button>
        )}
      </div>
    </div>
  );
}
