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
  type WorkflowType,
} from "@/lib/api";
import { getStepConfig, getMaxStepNumber } from "@/lib/stepConfig";
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

  const fetchStep = useCallback(async (options?: { preserveError?: boolean }) => {
    setLoading(true);
    if (!options?.preserveError) setError("");
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
    if (isNaN(stepNumber) || stepNumber < 1) {
      setLoading(false);
      setError("Numéro d'étape invalide.");
      return;
    }
    fetchStep();
  }, [fetchStep, stepNumber]);

  const workflowType: WorkflowType = dossier?.workflow_type ?? "standard";
  const maxStep = getMaxStepNumber(workflowType);
  const isValidStep = !isNaN(stepNumber) && stepNumber >= 1 && stepNumber <= maxStep;
  const config = getStepConfig(stepNumber, workflowType);
  const stepName = config?.name ?? `Étape ${stepNumber}`;
  const locked = step ? isStepLocked(step) : false;
  const dossierStatut = dossier?.statut ?? "actif";
  const isDossierClosed = dossierStatut === "fermé";
  const dossierName = dossier?.nom ?? "";

  useEffect(() => {
    if (dossier && (stepNumber > maxStep || stepNumber < 1)) {
      setError("Numéro d'étape invalide pour ce type de workflow.");
    }
  }, [dossier, stepNumber, maxStep]);

  // Poll when step is "en_cours" to detect completion and update progress
  useEffect(() => {
    if (step?.statut !== "en_cours") return;
    const interval = setInterval(async () => {
      try {
        const stepData = await dossiersApi.getStep(dossierId, stepNumber);
        setStep(stepData);
        if (stepData.statut !== "en_cours") {
          const dossierData = await dossiersApi.get(dossierId);
          setDossier(dossierData);
        }
      } catch { /* ignore polling errors */ }
    }, 5000);
    return () => clearInterval(interval);
  }, [step?.statut, dossierId, stepNumber]);

  /* ---------------------------------------------------------------- */
  /* Execute / Cancel handlers                                         */
  /* ---------------------------------------------------------------- */

  const handleExecute = useCallback(async () => {
    const isSimple = workflowType === "simple";
    try {
      if (stepNumber === 1) {
        if (step?.statut === "fait") {
          await step1Api.validate(dossierId);
          await fetchStep();
        } else if (step?.statut === "initial") {
          setStep((prev) => prev ? { ...prev, statut: "en_cours", executed_at: new Date().toISOString(), progress_current: null, progress_total: null, progress_message: null } : prev);
          step1Api.execute(dossierId).then(() => fetchStep()).catch((err) => {
            setError(getErrorMessage(err, "Erreur lors de l'exécution."));
            fetchStep({ preserveError: true });
          });
        }
      } else if (stepNumber === 2) {
        if (isSimple) {
          if (step?.statut === "fait") {
            await step2Api.validate(dossierId);
            await fetchStep();
          }
        } else if (step?.statut === "fait") {
          await step2Api.validate(dossierId);
          await fetchStep();
        } else if (step?.statut === "initial") {
          setStep((prev) => prev ? { ...prev, statut: "en_cours", executed_at: new Date().toISOString(), progress_current: null, progress_total: null, progress_message: null } : prev);
          step2Api.execute(dossierId).then(() => fetchStep()).catch((err) => {
            setError(getErrorMessage(err, "Erreur lors de l'exécution."));
            fetchStep({ preserveError: true });
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
            fetchStep({ preserveError: true });
          });
        }
      } else if (stepNumber === 4) {
        if (step?.statut === "fait") {
          await step4Api.validate(dossierId);
          await fetchStep();
        } else if (step?.statut === "initial") {
          setStep((prev) => prev ? { ...prev, statut: "en_cours", executed_at: new Date().toISOString(), progress_current: null, progress_total: null, progress_message: null } : prev);
          step4Api.execute(dossierId).then(() => fetchStep()).catch((err) => {
            setError(getErrorMessage(err, "Erreur lors de l'exécution."));
            fetchStep({ preserveError: true });
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
      await fetchStep({ preserveError: true });
    }
  }, [dossierId, stepNumber, step?.statut, fetchStep, workflowType]);

  const handleRerunSimpleStep1 = useCallback(async () => {
    setStep((prev) => prev ? { ...prev, statut: "en_cours" } : prev);
    try {
      await step1Api.execute(dossierId);
      await fetchStep();
    } catch (err: unknown) {
      setError(getErrorMessage(err, "Erreur lors de la relance."));
      await fetchStep({ preserveError: true });
    }
  }, [dossierId, fetchStep]);

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

      {/* Error (affiché au-dessus du contenu, pas en remplacement) */}
      {!loading && error && (
        <p className={styles.error} role="alert">{error}</p>
      )}

      {/* Step detail */}
      {!loading && step && isValidStep && (
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
          <ActionBanner stepNumber={stepNumber} dossierName={dossierName} workflowType={workflowType} />

          {/* Tripartite sections */}
          <div className={styles.tripartiteLayout}>
            <InputSection
              stepNumber={stepNumber}
              dossierId={dossierId}
              files={step.files}
              isLocked={locked}
              dossierStatut={dossierStatut}
              workflowType={workflowType}
              onFileUploaded={fetchStep}
            />

            <OperationSection
              stepNumber={stepNumber}
              dossierId={dossierId}
              step={step}
              isLocked={locked}
              isDossierClosed={isDossierClosed}
              workflowType={workflowType}
              onExecute={handleExecute}
              onCancel={handleCancel}
              onRerunSimpleStep1={workflowType === "simple" && stepNumber === 1 ? handleRerunSimpleStep1 : undefined}
              onSkip={stepNumber === 3 ? handleSkip : undefined}
              onRefresh={fetchStep}
              executionDuration={step.execution_duration_seconds}
            />

            <OutputSection
              stepNumber={stepNumber}
              dossierId={dossierId}
              files={step.files}
              isLocked={locked}
              workflowType={workflowType}
            />
          </div>
        </>
      )}
    </div>
  );
}
