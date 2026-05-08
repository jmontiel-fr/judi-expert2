"use client";

import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import styles from "./UpdateScreen.module.css";

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Polling interval for update status (ms) */
const POLL_INTERVAL_MS = 2000;

/** Delay before redirecting to login after completion (ms) */
const REDIRECT_DELAY_MS = 3000;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type UpdateStatus = "idle" | "downloading" | "installing" | "restarting" | "completed" | "error";

interface UpdateScreenProps {
  /** URL to download Docker images from */
  downloadUrl: string;
  /** Target version to install (semver) */
  targetVersion: string;
  /** Optional release notes to display */
  releaseNotes?: string | null;
}

// ---------------------------------------------------------------------------
// Step labels in French
// ---------------------------------------------------------------------------

const STEP_LABELS: Record<string, string> = {
  downloading: "Téléchargement des images...",
  installing: "Installation...",
  restarting: "Redémarrage...",
  completed: "Terminé",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Full-screen blocking modal displayed during a forced application update.
 *
 * Shows a progress bar with the current step (downloading → installing → restarting),
 * an error state with a retry button, and redirects to login on completion.
 *
 * Requirements: 3.3, 4.3, 4.5, 5.2
 */
export default function UpdateScreen({ downloadUrl, targetVersion, releaseNotes }: UpdateScreenProps) {
  const [status, setStatus] = useState<UpdateStatus>("idle");
  const [progress, setProgress] = useState<number>(0);
  const [step, setStep] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Start update
  // -------------------------------------------------------------------------

  const startUpdate = useCallback(async () => {
    setStatus("downloading");
    setStep("downloading");
    setProgress(0);
    setError(null);

    try {
      const response = await axios.post(`${API_URL}/api/version/update`, {
        download_url: downloadUrl,
        version: targetVersion,
      });

      const data = response.data;

      if (data.status === "completed") {
        setStatus("completed");
        setProgress(100);
        setStep("completed");
        // Redirect to login with success banner
        setTimeout(() => {
          window.location.href = `/login?updated=${encodeURIComponent(targetVersion)}`;
        }, REDIRECT_DELAY_MS);
      } else if (data.status === "error") {
        setError(data.error_message || "Erreur inconnue lors de la mise à jour");
        setStatus("error");
        setStep(data.step || "");
      } else {
        // Update is in progress — start polling
        setStatus(data.status || "downloading");
        setStep(data.step || "downloading");
        setProgress(data.progress || 10);
      }
    } catch (err: unknown) {
      const errorMessage =
        axios.isAxiosError(err) && err.response?.data?.detail
          ? err.response.data.detail
          : "Erreur de connexion au serveur";
      setError(errorMessage);
      setStatus("error");
    }
  }, [downloadUrl, targetVersion]);

  // -------------------------------------------------------------------------
  // Start update on mount
  // -------------------------------------------------------------------------

  useEffect(() => {
    startUpdate();
  }, [startUpdate]);

  // -------------------------------------------------------------------------
  // Simulated progress for long-running steps
  // -------------------------------------------------------------------------

  useEffect(() => {
    if (status === "downloading" || status === "installing" || status === "restarting") {
      const interval = setInterval(() => {
        setProgress((prev) => {
          // Cap progress at 90% until completion is confirmed
          if (prev >= 90) return 90;
          return prev + 5;
        });

        // Simulate step transitions based on progress
        setProgress((prev) => {
          if (prev >= 60 && status === "downloading") {
            setStatus("installing");
            setStep("installing");
          } else if (prev >= 80 && status === "installing") {
            setStatus("restarting");
            setStep("restarting");
          }
          return prev;
        });
      }, POLL_INTERVAL_MS);

      return () => clearInterval(interval);
    }
  }, [status]);

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  const currentStepLabel = STEP_LABELS[step] || STEP_LABELS[status] || "";

  return (
    <div className={styles.overlay} role="dialog" aria-modal="true" aria-label="Mise à jour en cours">
      <div className={styles.modal}>
        {/* Header */}
        <div className={styles.header}>
          <span className={styles.icon} aria-hidden="true">⬆️</span>
          <h2 className={styles.title}>Mise à jour en cours</h2>
          <p className={styles.subtitle}>Version {targetVersion}</p>
        </div>

        {/* Progress section */}
        {status !== "error" && status !== "completed" && (
          <div className={styles.progressSection}>
            {/* Step indicators */}
            <div className={styles.steps}>
              <StepIndicator
                label="Téléchargement"
                active={status === "downloading"}
                done={status === "installing" || status === "restarting"}
              />
              <StepIndicator
                label="Installation"
                active={status === "installing"}
                done={status === "restarting"}
              />
              <StepIndicator
                label="Redémarrage"
                active={status === "restarting"}
                done={false}
              />
            </div>

            {/* Progress bar */}
            <div className={styles.progressBar} role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
              <div className={styles.progressFill} style={{ width: `${progress}%` }} />
            </div>

            {/* Current step label */}
            <p className={styles.stepLabel}>{currentStepLabel}</p>
          </div>
        )}

        {/* Completed state */}
        {status === "completed" && (
          <div className={styles.completedSection}>
            <span className={styles.successIcon} aria-hidden="true">✓</span>
            <p className={styles.successMessage}>
              Application mise à jour en version {targetVersion}
            </p>
            <p className={styles.redirectMessage}>
              Redirection vers la page de connexion...
            </p>
          </div>
        )}

        {/* Error state */}
        {status === "error" && (
          <div className={styles.errorSection}>
            <span className={styles.errorIcon} aria-hidden="true">⚠️</span>
            <p className={styles.errorMessage}>{error}</p>
            <button
              type="button"
              className={styles.retryButton}
              onClick={startUpdate}
            >
              Réessayer
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-component: Step indicator
// ---------------------------------------------------------------------------

interface StepIndicatorProps {
  label: string;
  active: boolean;
  done: boolean;
}

function StepIndicator({ label, active, done }: StepIndicatorProps) {
  let className = styles.stepItem;
  if (done) className += ` ${styles.stepDone}`;
  else if (active) className += ` ${styles.stepActive}`;

  return (
    <div className={className}>
      <span className={styles.stepDot} aria-hidden="true">
        {done ? "✓" : active ? "●" : "○"}
      </span>
      <span className={styles.stepText}>{label}</span>
    </div>
  );
}
