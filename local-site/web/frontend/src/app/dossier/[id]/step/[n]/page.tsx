"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import styles from "./step.module.css";
import {
  dossiersApi,
  step0Api,
  step1Api,
  step2Api,
  step3Api,
  getErrorMessage,
  isStepLocked,
  type StepDetail,
} from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Constants                                                           */
/* ------------------------------------------------------------------ */

const STEP_NAMES: Record<number, string> = {
  0: "Extraction",
  1: "PEMEC",
  2: "Upload",
  3: "REF",
};

/* ------------------------------------------------------------------ */
/* Main component                                                      */
/* ------------------------------------------------------------------ */

export default function StepViewPage() {
  const params = useParams();
  const dossierId = params.id as string;
  const stepNumber = parseInt(params.n as string, 10);

  const [step, setStep] = useState<StepDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchStep = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await dossiersApi.getStep(dossierId, stepNumber);
      setStep(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err, "Impossible de charger l'étape."));
    } finally {
      setLoading(false);
    }
  }, [dossierId, stepNumber]);

  useEffect(() => {
    if (!isNaN(stepNumber) && stepNumber >= 0 && stepNumber <= 3) {
      fetchStep();
    } else {
      setLoading(false);
      setError("Numéro d'étape invalide.");
    }
  }, [fetchStep, stepNumber]);

  const isValidStep = !isNaN(stepNumber) && stepNumber >= 0 && stepNumber <= 3;
  const stepName = STEP_NAMES[stepNumber] ?? `Step${stepNumber}`;
  const locked = step ? isStepLocked(step) : false;

  /* ---------------------------------------------------------------- */
  /* Status helpers                                                    */
  /* ---------------------------------------------------------------- */

  const statusClass =
    step?.statut === "valide"
      ? styles.statusValide
      : step?.statut === "realise"
        ? styles.statusRealise
        : styles.statusInitial;

  const statusLabel =
    step?.statut === "valide"
      ? "Validé"
      : step?.statut === "realise"
        ? "Réalisé"
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

          {/* Locked notice */}
          {locked && (
            <div className={styles.lockedNotice}>
              <span aria-hidden="true">🔒</span>
              Cette étape est validée et verrouillée. Aucune modification n&apos;est possible.
            </div>
          )}

          {/* Step-specific content */}
          {stepNumber === 0 && (
            <Step0View
              dossierId={dossierId}
              step={step}
              isLocked={locked}
              onRefresh={fetchStep}
            />
          )}
          {stepNumber === 1 && (
            <Step1View
              dossierId={dossierId}
              step={step}
              isLocked={locked}
              onRefresh={fetchStep}
            />
          )}
          {stepNumber === 2 && (
            <Step2View
              dossierId={dossierId}
              step={step}
              isLocked={locked}
              onRefresh={fetchStep}
            />
          )}
          {stepNumber === 3 && (
            <Step3View
              dossierId={dossierId}
              step={step}
              isLocked={locked}
              onRefresh={fetchStep}
            />
          )}
        </>
      )}
    </div>
  );
}


/* ================================================================== */
/* Step0View — Extraction                                              */
/* ================================================================== */

interface StepViewProps {
  dossierId: string;
  step: StepDetail;
  isLocked: boolean;
  onRefresh: () => Promise<void>;
}

function Step0View({ dossierId, step, isLocked, onRefresh }: StepViewProps) {
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [markdown, setMarkdown] = useState("");
  const [showMarkdown, setShowMarkdown] = useState(false);
  const [loadingMd, setLoadingMd] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");

  const hasMarkdown = step.files.some((f) => f.file_type === "markdown");

  const handleExtract = async () => {
    if (!pdfFile) return;
    setExtracting(true);
    setActionError("");
    setActionSuccess("");
    try {
      const data = await step0Api.extract(dossierId, pdfFile);
      setMarkdown(data.markdown);
      setShowMarkdown(true);
      setActionSuccess("Extraction terminée avec succès.");
      await onRefresh();
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Erreur lors de l'extraction."));
    } finally {
      setExtracting(false);
    }
  };

  const handleVisualize = async () => {
    setLoadingMd(true);
    setActionError("");
    try {
      const data = await step0Api.getMarkdown(dossierId);
      setMarkdown(data.markdown);
      setShowMarkdown(true);
      setEditing(false);
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Erreur lors du chargement du Markdown."));
    } finally {
      setLoadingMd(false);
    }
  };

  const handleStartEdit = () => {
    setEditContent(markdown);
    setEditing(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setActionError("");
    setActionSuccess("");
    try {
      await step0Api.updateMarkdown(dossierId, editContent);
      setMarkdown(editContent);
      setEditing(false);
      setActionSuccess("Fichier Markdown sauvegardé.");
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Erreur lors de la sauvegarde."));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      {actionError && <p className={styles.error} role="alert">{actionError}</p>}
      {actionSuccess && <p className={styles.success}>{actionSuccess}</p>}

      {/* Upload & Extract */}
      {!isLocked && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Upload du PDF-scan</h2>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="pdf-upload">
              Fichier PDF de réquisition
            </label>
            <input
              id="pdf-upload"
              type="file"
              accept=".pdf"
              className={styles.fileInput}
              onChange={(e) => setPdfFile(e.target.files?.[0] ?? null)}
              disabled={isLocked}
            />
          </div>
          <div className={styles.actions}>
            <button
              className={styles.btnPrimary}
              onClick={handleExtract}
              disabled={!pdfFile || extracting || isLocked}
            >
              {extracting ? "Extraction en cours…" : "Extraction"}
            </button>
            {hasMarkdown && (
              <button
                className={styles.btnSecondary}
                onClick={handleVisualize}
                disabled={loadingMd}
              >
                {loadingMd ? "Chargement…" : "Visualiser"}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Locked: just show visualize */}
      {isLocked && hasMarkdown && (
        <div className={styles.section}>
          <div className={styles.actions}>
            <button
              className={styles.btnSecondary}
              onClick={handleVisualize}
              disabled={loadingMd}
            >
              {loadingMd ? "Chargement…" : "Visualiser"}
            </button>
          </div>
        </div>
      )}

      {/* Markdown viewer / editor */}
      {showMarkdown && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Contenu Markdown</h2>
          {!editing ? (
            <>
              <div className={styles.markdownContent}>{markdown}</div>
              {!isLocked && (
                <div className={styles.actions}>
                  <button
                    className={styles.btnSecondary}
                    onClick={handleStartEdit}
                  >
                    Modifier
                  </button>
                </div>
              )}
            </>
          ) : (
            <>
              <textarea
                className={styles.textarea}
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                aria-label="Édition du contenu Markdown"
              />
              <div className={styles.actions}>
                <button
                  className={styles.btnPrimary}
                  onClick={handleSave}
                  disabled={saving}
                >
                  {saving ? "Sauvegarde…" : "Sauvegarder"}
                </button>
                <button
                  className={styles.btnSecondary}
                  onClick={() => setEditing(false)}
                >
                  Annuler
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}


/* ================================================================== */
/* Step1View — PEMEC                                                   */
/* ================================================================== */

function Step1View({ dossierId, step, isLocked, onRefresh }: StepViewProps) {
  const [executing, setExecuting] = useState(false);
  const [validating, setValidating] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");

  const hasQmec = step.files.some((f) => f.file_type === "qmec");
  const isRealise = step.statut === "realise";

  const handleExecute = async () => {
    setExecuting(true);
    setActionError("");
    setActionSuccess("");
    try {
      await step1Api.execute(dossierId);
      setActionSuccess("QMEC généré avec succès.");
      await onRefresh();
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Erreur lors de l'exécution."));
    } finally {
      setExecuting(false);
    }
  };

  const handleDownload = () => {
    const url = step1Api.getDownloadUrl(dossierId);
    const a = document.createElement("a");
    a.href = url;
    a.download = "qmec.md";
    a.click();
  };

  const handleValidate = async () => {
    setValidating(true);
    setActionError("");
    setActionSuccess("");
    try {
      await step1Api.validate(dossierId);
      setActionSuccess("Step1 validé avec succès.");
      await onRefresh();
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Erreur lors de la validation."));
    } finally {
      setValidating(false);
    }
  };

  return (
    <>
      {actionError && <p className={styles.error} role="alert">{actionError}</p>}
      {actionSuccess && <p className={styles.success}>{actionSuccess}</p>}

      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Génération du QMEC</h2>
        <div className={styles.actions}>
          {/* Execute */}
          {!isLocked && !hasQmec && (
            <button
              className={styles.btnPrimary}
              onClick={handleExecute}
              disabled={executing}
            >
              {executing ? "Génération en cours…" : "Execute"}
            </button>
          )}

          {/* Download */}
          {hasQmec && (
            <button className={styles.btnDownload} onClick={handleDownload}>
              ⬇ Download QMEC
            </button>
          )}

          {/* Validate */}
          {!isLocked && isRealise && (
            <button
              className={styles.btnPrimary}
              onClick={handleValidate}
              disabled={validating}
            >
              {validating ? "Validation…" : "Valider"}
            </button>
          )}
        </div>
      </div>
    </>
  );
}


/* ================================================================== */
/* Step2View — Upload NE + REB                                         */
/* ================================================================== */

function Step2View({ dossierId, step, isLocked, onRefresh }: StepViewProps) {
  const [neFile, setNeFile] = useState<File | null>(null);
  const [rebFile, setRebFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");

  const isRealise = step.statut === "realise";
  const hasFiles = step.files.length > 0;

  const validateDocx = (file: File | null): boolean => {
    if (!file) return false;
    return file.name.toLowerCase().endsWith(".docx");
  };

  const handleUpload = async () => {
    setActionError("");
    setActionSuccess("");

    if (!neFile || !rebFile) {
      setActionError("Veuillez sélectionner les deux fichiers (NE et REB).");
      return;
    }
    if (!validateDocx(neFile)) {
      setActionError("Le fichier NE doit être au format .docx.");
      return;
    }
    if (!validateDocx(rebFile)) {
      setActionError("Le fichier REB doit être au format .docx.");
      return;
    }

    setUploading(true);
    try {
      await step2Api.upload(dossierId, neFile, rebFile);
      setActionSuccess("Fichiers NE et REB uploadés avec succès.");
      await onRefresh();
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Erreur lors de l'upload."));
    } finally {
      setUploading(false);
    }
  };

  const handleValidate = async () => {
    setValidating(true);
    setActionError("");
    setActionSuccess("");
    try {
      await step2Api.validate(dossierId);
      setActionSuccess("Step2 validé avec succès.");
      await onRefresh();
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Erreur lors de la validation."));
    } finally {
      setValidating(false);
    }
  };

  return (
    <>
      {actionError && <p className={styles.error} role="alert">{actionError}</p>}
      {actionSuccess && <p className={styles.success}>{actionSuccess}</p>}

      {/* Upload section */}
      {!isLocked && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Upload des fichiers</h2>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="ne-upload">
              Notes d&apos;entretien (NE)
            </label>
            <input
              id="ne-upload"
              type="file"
              accept=".docx"
              className={styles.fileInput}
              onChange={(e) => setNeFile(e.target.files?.[0] ?? null)}
              disabled={isLocked}
            />
            <span className={styles.fileHint}>Format accepté : .docx uniquement</span>
          </div>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="reb-upload">
              Rapport d&apos;expertise brut (REB)
            </label>
            <input
              id="reb-upload"
              type="file"
              accept=".docx"
              className={styles.fileInput}
              onChange={(e) => setRebFile(e.target.files?.[0] ?? null)}
              disabled={isLocked}
            />
            <span className={styles.fileHint}>Format accepté : .docx uniquement</span>
          </div>
          <div className={styles.actions}>
            <button
              className={styles.btnPrimary}
              onClick={handleUpload}
              disabled={!neFile || !rebFile || uploading || isLocked}
            >
              {uploading ? "Upload en cours…" : "Upload"}
            </button>
          </div>
        </div>
      )}

      {/* Validate section */}
      {!isLocked && isRealise && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Validation</h2>
          {hasFiles && (
            <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: 12 }}>
              Fichiers uploadés : {step.files.map((f) => f.filename).join(", ")}
            </p>
          )}
          <div className={styles.actions}>
            <button
              className={styles.btnPrimary}
              onClick={handleValidate}
              disabled={validating}
            >
              {validating ? "Validation…" : "Valider"}
            </button>
          </div>
        </div>
      )}

      {/* Locked: show uploaded files */}
      {isLocked && hasFiles && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Fichiers uploadés</h2>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
            {step.files.map((f) => f.filename).join(", ")}
          </p>
        </div>
      )}
    </>
  );
}


/* ================================================================== */
/* Step3View — REF + RAUX                                              */
/* ================================================================== */

function Step3View({ dossierId, step, isLocked, onRefresh }: StepViewProps) {
  const [executing, setExecuting] = useState(false);
  const [validating, setValidating] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");

  const hasRef = step.files.some((f) => f.file_type === "ref");
  const hasRaux = step.files.some((f) => f.file_type === "raux");
  const isRealise = step.statut === "realise";

  const handleExecute = async () => {
    setExecuting(true);
    setActionError("");
    setActionSuccess("");
    try {
      await step3Api.execute(dossierId);
      setActionSuccess("REF et RAUX générés avec succès.");
      await onRefresh();
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Erreur lors de l'exécution."));
    } finally {
      setExecuting(false);
    }
  };

  const handleDownload = (docType: "ref" | "raux") => {
    const url = step3Api.getDownloadUrl(dossierId, docType);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${docType}.md`;
    a.click();
  };

  const handleValidate = async () => {
    if (
      !window.confirm(
        "Attention : la validation du Step3 verrouillera définitivement le dossier. Voulez-vous continuer ?"
      )
    ) {
      return;
    }
    setValidating(true);
    setActionError("");
    setActionSuccess("");
    try {
      await step3Api.validate(dossierId);
      setActionSuccess("Step3 validé — dossier archivé avec succès.");
      await onRefresh();
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Erreur lors de la validation."));
    } finally {
      setValidating(false);
    }
  };

  return (
    <>
      {actionError && <p className={styles.error} role="alert">{actionError}</p>}
      {actionSuccess && <p className={styles.success}>{actionSuccess}</p>}

      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Génération REF et RAUX</h2>
        <div className={styles.actions}>
          {/* Execute */}
          {!isLocked && !hasRef && (
            <button
              className={styles.btnPrimary}
              onClick={handleExecute}
              disabled={executing}
            >
              {executing ? "Génération en cours…" : "Execute"}
            </button>
          )}

          {/* Download REF */}
          {hasRef && (
            <button
              className={styles.btnDownload}
              onClick={() => handleDownload("ref")}
            >
              ⬇ Download REF
            </button>
          )}

          {/* Download RAUX */}
          {hasRaux && (
            <button
              className={styles.btnDownload}
              onClick={() => handleDownload("raux")}
            >
              ⬇ Download RAUX
            </button>
          )}

          {/* Validate */}
          {!isLocked && isRealise && (
            <button
              className={styles.btnDanger}
              onClick={handleValidate}
              disabled={validating}
            >
              {validating ? "Validation…" : "Valider (verrouillage définitif)"}
            </button>
          )}
        </div>
      </div>
    </>
  );
}
