"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import styles from "./step.module.css";
import {
  dossiersApi,
  step1Api,
  step2Api,
  step3Api,
  step4Api,
  step5Api,
  getErrorMessage,
  isStepLocked,
  type StepDetail,
  type DossierDetail,
} from "@/lib/api";
import { STEP_CONFIG } from "@/lib/stepConfig";
import ActionBanner from "@/components/ActionBanner";
import InputSection from "@/components/InputSection";
import OperationSection from "@/components/OperationSection";
import OutputSection from "@/components/OutputSection";

/* ------------------------------------------------------------------ */
/* Main component                                                      */
/* ------------------------------------------------------------------ */

export default function StepViewPage() {
  const params = useParams();
  const dossierId = params.id as string;
  const stepNumber = parseInt(params.n as string, 10);

  const [step, setStep] = useState<StepDetail | null>(null);
  const [dossier, setDossier] = useState<DossierDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchStep = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [stepData, dossierData] = await Promise.all([
        dossiersApi.getStep(dossierId, stepNumber),
        dossiersApi.get(dossierId),
      ]);
      setStep(stepData);
      setDossier(dossierData);
    } catch (err: unknown) {
      setError(getErrorMessage(err, "Impossible de charger l'étape."));
    } finally {
      setLoading(false);
    }
  }, [dossierId, stepNumber]);

  useEffect(() => {
    if (!isNaN(stepNumber) && stepNumber >= 1 && stepNumber <= 5) {
      fetchStep();
    } else {
      setLoading(false);
      setError("Numéro d'étape invalide.");
    }
  }, [fetchStep, stepNumber]);

  // Poll when step is "en_cours" to detect completion and update progress
  useEffect(() => {
    if (step?.statut !== "en_cours") return;
    const interval = setInterval(async () => {
      try {
        const stepData = await dossiersApi.getStep(dossierId, stepNumber);
        setStep(stepData);
        if (stepData.statut !== "en_cours") {
          // Also refresh dossier when completed
          const dossierData = await dossiersApi.get(dossierId);
          setDossier(dossierData);
        }
      } catch { /* ignore polling errors */ }
    }, 5000);
    return () => clearInterval(interval);
  }, [step?.statut, dossierId, stepNumber]);

  const isValidStep = !isNaN(stepNumber) && stepNumber >= 1 && stepNumber <= 5;
  const config = STEP_CONFIG[stepNumber];
  const stepName = config?.name ?? `Étape ${stepNumber}`;
  const locked = step ? isStepLocked(step) : false;
  const dossierStatut = dossier?.statut ?? "actif";
  const isDossierClosed = dossierStatut === "fermé";
  const dossierName = dossier?.nom ?? "";

  /* ---------------------------------------------------------------- */
  /* Execute / Cancel handlers                                         */
  /* ---------------------------------------------------------------- */

  const handleExecute = useCallback(async () => {
    try {
      if (stepNumber === 1) {
        if (step?.statut === "fait") {
          await step1Api.validate(dossierId);
          await fetchStep();
        } else if (step?.statut === "initial") {
          // Mettre à jour l'UI immédiatement pour afficher le sablier
          setStep((prev) => prev ? { ...prev, statut: "en_cours", executed_at: new Date().toISOString(), progress_current: null, progress_total: null, progress_message: null } : prev);
          // Lancer l'extraction en fire-and-forget — le polling détectera la fin
          step1Api.execute(dossierId).then(() => fetchStep()).catch((err) => {
            setError(getErrorMessage(err, "Erreur lors de l'exécution."));
            fetchStep();
          });
        }
      } else if (stepNumber === 2) {
        if (step?.statut === "fait") {
          await step2Api.validate(dossierId);
          await fetchStep();
        } else if (step?.statut === "initial") {
          setStep((prev) => prev ? { ...prev, statut: "en_cours", executed_at: new Date().toISOString(), progress_current: null, progress_total: null, progress_message: null } : prev);
          step2Api.execute(dossierId).then(() => fetchStep()).catch((err) => {
            setError(getErrorMessage(err, "Erreur lors de l'exécution."));
            fetchStep();
          });
        }
      } else if (stepNumber === 3) {
        if (step?.statut === "fait") {
          await step3Api.validate(dossierId);
          await fetchStep();
        } else if (step?.statut === "initial") {
          setStep((prev) => prev ? { ...prev, statut: "en_cours", executed_at: new Date().toISOString(), progress_current: null, progress_total: null, progress_message: null } : prev);
          step3Api.execute(dossierId).then(() => fetchStep()).catch((err) => {
            setError(getErrorMessage(err, "Erreur lors de l'exécution."));
            fetchStep();
          });
        }
      } else if (stepNumber === 4) {
        if (step?.statut === "fait") {
          await step4Api.validate(dossierId);
          await fetchStep();
        } else if (step?.statut === "initial") {
          // Vérifier qu'un PEA est uploadé
          const hasPea = step.files?.some(f => f.file_type === "pea" || f.file_type === "paa");
          if (!hasPea) {
            setError("Importez d'abord le PEA/PAA dans la section « Fichiers d'entrée ».");
            return;
          }
          setStep((prev) => prev ? { ...prev, statut: "en_cours", executed_at: new Date().toISOString(), progress_current: null, progress_total: null, progress_message: null } : prev);
          step4Api.execute(dossierId).then(() => fetchStep()).catch((err) => {
            setError(getErrorMessage(err, "Erreur lors de l'exécution."));
            fetchStep();
          });
        }
      } else if (stepNumber === 5) {
        if (step?.statut === "fait") {
          await step5Api.validate(dossierId);
          await fetchStep();
        }
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err, "Erreur lors de l'exécution."));
      await fetchStep();
    }
  }, [dossierId, stepNumber, step?.statut, fetchStep]);

  const handleCancel = useCallback(async () => {
    if (confirm("Réinitialiser cette étape ? Le traitement en cours sera abandonné.")) {
      try {
        await dossiersApi.cancelStep(dossierId, stepNumber);
        setStep((prev) => prev ? { ...prev, statut: "initial" } : prev);
        await fetchStep();
      } catch { /* ignore */ }
    }
  }, [dossierId, stepNumber, fetchStep]);

  const handleSkip = useCallback(async () => {
    if (stepNumber !== 3) return;
    try {
      const token = localStorage.getItem("token");
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/dossiers/${dossierId}/step3/skip`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || "Impossible de valider sans objet.");
        return;
      }
      await fetchStep();
    } catch {
      setError("Erreur réseau lors de la validation sans objet.");
    }
  }, [dossierId, stepNumber, fetchStep]);

  /* ---------------------------------------------------------------- */
  /* Status helpers                                                    */
  /* ---------------------------------------------------------------- */

  const statusClass =
    step?.statut === "valide"
      ? styles.statusValide
      : step?.statut === "fait"
        ? styles.statusRealise
        : step?.statut === "en_cours"
          ? styles.statusRealise
          : styles.statusInitial;

  const statusLabel =
    step?.statut === "valide"
      ? "Validé"
      : step?.statut === "fait"
        ? "Fait"
        : step?.statut === "en_cours"
          ? "En cours…"
          : "Initial";

  /* ---------------------------------------------------------------- */
  /* Render                                                            */
  /* ---------------------------------------------------------------- */

  return (
    <div className={styles.container}>
      {/* Back link */}
      <Link href={`/dossier/${dossierId}`} className={styles.backLink}>
        <span className={styles.backArrow} aria-hidden="true">←</span>
        Retour au dossier
      </Link>

      {/* Loading */}
      {loading && (
        <div className={styles.loading}>
          <span className={styles.spinner} aria-hidden="true" />
          Chargement de l&apos;étape…
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <p className={styles.error} role="alert">{error}</p>
      )}

      {/* Step detail */}
      {!loading && !error && step && isValidStep && (
        <>
          {/* Header */}
          <div className={styles.header}>
            <h1 className={styles.title}>
              Étape {stepNumber} — {stepName}
            </h1>
            <div className={styles.meta}>
              <span className={`${styles.statusBadge} ${statusClass}`}>
                {statusLabel}
              </span>
            </div>
          </div>

          {/* Action Banner */}
          <ActionBanner stepNumber={stepNumber} dossierName={dossierName} />

          {/* Tripartite sections */}
          <div className={styles.tripartiteLayout}>
            {/* Input Section */}
            <InputSection
              stepNumber={stepNumber}
              dossierId={dossierId}
              files={step.files}
              isLocked={locked}
              dossierStatut={dossierStatut}
              onFileUploaded={fetchStep}
            />

            {/* Operation Section */}
            <OperationSection
              stepNumber={stepNumber}
              dossierId={dossierId}
              step={step}
              isLocked={locked}
              isDossierClosed={isDossierClosed}
              onExecute={handleExecute}
              onCancel={handleCancel}
              onSkip={stepNumber === 3 ? handleSkip : undefined}
              executionDuration={step.execution_duration_seconds}
            />

            {/* Output Section */}
            <OutputSection
              stepNumber={stepNumber}
              dossierId={dossierId}
              files={step.files}
              isLocked={locked}
            />
          </div>
        </>
      )}
    </div>
  );
}
