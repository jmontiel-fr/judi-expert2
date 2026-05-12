"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import styles from "./dossier.module.css";
import {
  dossiersApi,
  getErrorMessage,
  isStepAccessible,
  type DossierDetail,
} from "@/lib/api";
import { STEP_CONFIG } from "@/lib/stepConfig";
import FileList from "@/components/FileList";

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/* ------------------------------------------------------------------ */
/* Main component                                                      */
/* ------------------------------------------------------------------ */

export default function DossierDetailPage() {
  const params = useParams();
  const dossierId = params.id as string;

  const [dossier, setDossier] = useState<DossierDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [closing, setClosing] = useState(false);
  const [closeError, setCloseError] = useState("");
  const [resettingStep, setResettingStep] = useState<number | null>(null);
  const [resetError, setResetError] = useState("");
  const [validatingStep, setValidatingStep] = useState<number | null>(null);
  const [validateError, setValidateError] = useState("");
  const [resettingAll, setResettingAll] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [actionError, setActionError] = useState("");

  const fetchDossier = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await dossiersApi.get(dossierId);
      setDossier(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err, "Impossible de charger le dossier."));
    } finally {
      setLoading(false);
    }
  }, [dossierId]);

  useEffect(() => {
    fetchDossier();
  }, [fetchDossier]);

  // Poll when any step is "en_cours"
  const hasEnCours = dossier?.steps.some((s) => s.statut === "en_cours");
  useEffect(() => {
    if (!hasEnCours) return;
    const interval = setInterval(async () => {
      try {
        const data = await dossiersApi.get(dossierId);
        setDossier(data);
      } catch { /* ignore */ }
    }, 5000);
    return () => clearInterval(interval);
  }, [hasEnCours, dossierId]);

  const allStepsValidated =
    dossier?.steps.length === 5 &&
    dossier.steps.every((s) => s.statut === "valide");

  const handleClose = async () => {
    setClosing(true);
    setCloseError("");
    try {
      await dossiersApi.close(dossierId);
      await fetchDossier();
    } catch (err: unknown) {
      setCloseError(getErrorMessage(err, "Impossible de fermer le dossier."));
    } finally {
      setClosing(false);
    }
  };

  const handleDownload = () => {
    const url = dossiersApi.getDownloadUrl(dossierId);
    const a = document.createElement("a");
    a.href = url;
    a.download = "";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleResetStep = async (stepNumber: number) => {
    if (!confirm(`Réinitialiser l'étape ${stepNumber} ? Les fichiers seront supprimés.`)) return;
    setResettingStep(stepNumber);
    setResetError("");
    try {
      await dossiersApi.resetStep(dossierId, stepNumber);
      await fetchDossier();
    } catch (err: unknown) {
      setResetError(getErrorMessage(err, "Impossible de réinitialiser l'étape."));
    } finally {
      setResettingStep(null);
    }
  };

  const handleValidateStep = async (stepNumber: number) => {
    setValidatingStep(stepNumber);
    setValidateError("");
    try {
      await dossiersApi.validateStep(dossierId, stepNumber);
      await fetchDossier();
    } catch (err: unknown) {
      setValidateError(getErrorMessage(err, "Impossible de valider l'étape."));
    } finally {
      setValidatingStep(null);
    }
  };

  const handleResetAll = async () => {
    if (!confirm("Réinitialiser TOUT le dossier ? Tous les fichiers de toutes les étapes seront supprimés.")) return;
    setResettingAll(true);
    setActionError("");
    try {
      await dossiersApi.resetAll(dossierId);
      await fetchDossier();
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Impossible de réinitialiser le dossier."));
    } finally {
      setResettingAll(false);
    }
  };

  const handleArchive = async () => {
    if (!confirm("Archiver le dossier ? Cette action est irréversible.")) return;
    setArchiving(true);
    setActionError("");
    try {
      await dossiersApi.archive(dossierId);
      await fetchDossier();
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Impossible d'archiver le dossier."));
    } finally {
      setArchiving(false);
    }
  };

  /* ---------------------------------------------------------------- */
  /* Render                                                            */
  /* ---------------------------------------------------------------- */

  return (
    <div className={styles.container}>
      {/* Back link */}
      <Link href="/" className={styles.backLink}>
        <span className={styles.backArrow} aria-hidden="true">←</span>
        Retour aux dossiers
      </Link>

      {/* Loading */}
      {loading && (
        <div className={styles.loading}>
          <span className={styles.spinner} aria-hidden="true" />
          Chargement du dossier…
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <p className={styles.error} role="alert">{error}</p>
      )}

      {/* Dossier detail */}
      {!loading && !error && dossier && (
        <>
          {/* Dossier header */}
          <div className={styles.header}>
            <h1 className={styles.title}>{dossier.nom}</h1>
            <div className={styles.meta}>
              <span className={`${styles.badge} ${styles.badgeDomaine}`}>
                {dossier.domaine}
              </span>
              <span
                className={`${styles.badge} ${
                  dossier.statut === "actif"
                    ? styles.badgeActif
                    : dossier.statut === "fermé"
                      ? styles.badgeFerme
                      : styles.badgeArchive
                }`}
              >
                {dossier.statut === "actif"
                  ? "Actif"
                  : dossier.statut === "fermé"
                    ? "Fermé"
                    : "Archivé"}
              </span>
              <span>Créé le {formatDate(dossier.created_at)}</span>
            </div>
          </div>

          {/* Dossier action bar — top */}
          <div className={styles.topActions}>
            {dossier.statut === "actif" && (
              <button
                className={styles.btnResetAll}
                onClick={handleResetAll}
                disabled={resettingAll}
              >
                {resettingAll ? "Réinitialisation…" : "⟲ Reset complet"}
              </button>
            )}
            {allStepsValidated && dossier.statut === "actif" && (
              <button
                className={styles.btnClose}
                onClick={handleClose}
                disabled={closing}
              >
                {closing ? "Fermeture en cours…" : "Clore le dossier"}
              </button>
            )}
            {dossier.statut === "fermé" && (
              <>
                <button
                  className={styles.btnArchive}
                  onClick={handleArchive}
                  disabled={archiving}
                >
                  {archiving ? "Archivage…" : "Archiver"}
                </button>
                <button className={styles.btnDownload} onClick={handleDownload}>
                  Télécharger le dossier
                </button>
              </>
            )}
            {dossier.statut === "archive" && (
              <button className={styles.btnDownload} onClick={handleDownload}>
                Télécharger le dossier
              </button>
            )}
          </div>
          {closeError && <p className={styles.closeError} role="alert">{closeError}</p>}
          {actionError && <p className={styles.closeError} role="alert">{actionError}</p>}

          {/* Steps section */}
          <h2 className={styles.sectionTitle}>Étapes du dossier</h2>
          <div className={styles.stepList} role="list">
            {[...dossier.steps]
              .sort((a, b) => a.step_number - b.step_number)
              .map((step) => {
                const accessible = isStepAccessible(step.step_number, dossier.steps);
                const stepLabel = `Étape ${step.step_number} — ${STEP_CONFIG[step.step_number]?.name ?? `Step${step.step_number}`}`;

                const statusClass =
                  step.statut === "valide"
                    ? styles.statusValide
                    : step.statut === "fait"
                      ? styles.statusRealise
                      : step.statut === "en_cours"
                        ? styles.statusEnCours
                        : styles.statusInitial;

                const statusLabel =
                  step.statut === "valide"
                    ? "Validé"
                    : step.statut === "fait"
                      ? "Fait"
                      : step.statut === "en_cours"
                        ? "⏳ En cours…"
                        : "Initial";

                const isInitial = step.statut === "initial";
                const isRealise = step.statut === "fait";
                const isEnCours = step.statut === "en_cours";
                const isValide = step.statut === "valide";
                const isFerme = dossier.statut === "fermé";
                const canNavigate = accessible && (isInitial || isEnCours) && !isFerme;
                const canValidate = isRealise && dossier.statut === "actif";
                const canReset = isRealise && dossier.statut === "actif";

                const cardContent = (
                  <>
                    <div className={styles.stepInfo}>
                      <div className={styles.stepHeader}>
                        <span className={styles.stepNumber}>{step.step_number}</span>
                        <span className={styles.stepName}>
                          {STEP_CONFIG[step.step_number]?.name ?? `Step${step.step_number}`}
                        </span>
                      </div>
                      <div className={styles.stepDates}>
                        {step.executed_at && (
                          <span>Exécuté : {formatDateTime(step.executed_at)}{step.execution_duration_seconds != null && step.execution_duration_seconds > 0 ? ` — Durée : ${Math.floor(step.execution_duration_seconds / 60)}min ${Math.floor(step.execution_duration_seconds % 60).toString().padStart(2, "0")}s` : ""}</span>
                        )}
                        {step.validated_at && (
                          <span>Validé : {formatDateTime(step.validated_at)}</span>
                        )}
                      </div>
                    </div>
                    <div className={styles.stepRight}>
                      <span className={`${styles.statusBadge} ${statusClass}`}>
                        {statusLabel}
                      </span>
                      {canNavigate && (
                        <span className={styles.accessArrow} aria-hidden="true">→</span>
                      )}
                      {!accessible && isInitial && (
                        <span className={styles.lockIcon} aria-hidden="true" title="Étape verrouillée">🔒</span>
                      )}
                    </div>
                  </>
                );

                return (
                  <div key={step.step_number} role="listitem">
                    {canNavigate ? (
                      <Link
                        href={`/dossier/${dossier.id}/step/${step.step_number}`}
                        className={`${styles.stepCard} ${styles.stepCardAccessible}`}
                        aria-label={`${stepLabel} — ${statusLabel}`}
                      >
                        {cardContent}
                      </Link>
                    ) : (
                      <div
                        className={`${styles.stepCard} ${!accessible && isInitial ? styles.stepCardLocked : ""}`}
                        aria-label={`${stepLabel} — ${statusLabel}`}
                      >
                        {cardContent}
                      </div>
                    )}
                    {(canValidate || canReset) && (
                      <div className={styles.resetRow}>
                        {canValidate && (
                          <button
                            className={styles.btnValidate}
                            onClick={() => handleValidateStep(step.step_number)}
                            disabled={validatingStep === step.step_number}
                          >
                            {validatingStep === step.step_number ? "Validation…" : "Valider"}
                          </button>
                        )}
                        {canReset && (
                          <button
                            className={styles.btnReset}
                            onClick={() => handleResetStep(step.step_number)}
                            disabled={resettingStep === step.step_number}
                          >
                            {resettingStep === step.step_number ? "Reset…" : "Reset"}
                          </button>
                        )}
                      </div>
                    )}
                    {validateError && validatingStep === null && (
                      <p className={styles.resetError} role="alert">{validateError}</p>
                    )}
                    {resetError && resettingStep === null && (
                      <p className={styles.resetError} role="alert">{resetError}</p>
                    )}
                    {step.files && step.files.length > 0 && (
                      <details className={styles.filesCollapsable}>
                        <summary style={{ cursor: "pointer", fontSize: "0.8rem", color: "#2563eb", marginTop: 8 }}>
                          📎 {step.files.length} fichier{step.files.length > 1 ? "s" : ""}
                        </summary>
                        <div style={{ marginTop: 8 }}>
                          <FileList
                            dossierId={dossier.id}
                            stepNumber={step.step_number}
                            files={step.files}
                            isLocked={step.statut === "valide"}
                            showReplaceButton={false}
                          />
                        </div>
                      </details>
                    )}
                  </div>
                );
              })}
          </div>
        </>
      )}
    </div>
  );
}
