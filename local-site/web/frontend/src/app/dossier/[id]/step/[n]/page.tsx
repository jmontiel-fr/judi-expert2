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
  type DossierDetail,
} from "@/lib/api";
import FileList from "@/components/FileList";

/* ------------------------------------------------------------------ */
/* Constants                                                           */
/* ------------------------------------------------------------------ */

const STEP_NAMES: Record<number, string> = {
  0: "Extraction",
  1: "Préparation entretien",
  2: "Mise en forme RE-Projet",
  3: "Upload / Compression dossier final",
};

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
    if (!isNaN(stepNumber) && stepNumber >= 0 && stepNumber <= 3) {
      fetchStep();
    } else {
      setLoading(false);
      setError("Numéro d'étape invalide.");
    }
  }, [fetchStep, stepNumber]);

  // Poll when step is "en_cours" to detect completion
  useEffect(() => {
    if (step?.statut !== "en_cours") return;
    const interval = setInterval(async () => {
      try {
        const stepData = await dossiersApi.getStep(dossierId, stepNumber);
        if (stepData.statut !== "en_cours") {
          setStep(stepData);
          // Also refresh dossier
          const dossierData = await dossiersApi.get(dossierId);
          setDossier(dossierData);
        }
      } catch { /* ignore polling errors */ }
    }, 5000);
    return () => clearInterval(interval);
  }, [step?.statut, dossierId, stepNumber]);

  const isValidStep = !isNaN(stepNumber) && stepNumber >= 0 && stepNumber <= 3;
  const stepName = STEP_NAMES[stepNumber] ?? `Step${stepNumber}`;
  const locked = step ? isStepLocked(step) : false;
  const isProcessing = step?.statut === "en_cours";
  const dossierStatut = dossier?.statut ?? "actif";
  const isDossierClosed = dossierStatut === "fermé";
  const showReplace = !locked && !isDossierClosed;

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

          {/* Locked notice */}
          {locked && (
            <div className={styles.lockedNotice}>
              <span aria-hidden="true">🔒</span>
              Cette étape est validée et verrouillée. Aucune modification n&apos;est possible.
            </div>
          )}

          {/* Dossier closed notice */}
          {isDossierClosed && !locked && (
            <div className={styles.lockedNotice}>
              <span aria-hidden="true">🔒</span>
              Le dossier est fermé, aucune modification n&apos;est possible.
            </div>
          )}

          {/* Processing indicator */}
          {isProcessing && (
            <div className={styles.extractingIndicator}>
              <span className={styles.hourglass} aria-hidden="true">⏳</span>
              <div>
                {stepNumber === 0 && (
                  <>
                    <div>Étape 1/3 — OCR (extraction du texte)</div>
                    <div>Étape 2/3 — Structuration Markdown par l&apos;IA</div>
                    <div>Étape 3/3 — Génération du document Word</div>
                  </>
                )}
                {stepNumber === 1 && (
                  <>
                    <div>Étape 1/2 — Génération du plan d&apos;entretien par l&apos;IA</div>
                    <div>Étape 2/2 — Génération du document Word</div>
                  </>
                )}
                {stepNumber === 2 && (
                  <>
                    <div>Étape 1/2 — Génération du RE-Projet par l&apos;IA</div>
                    <div>Étape 2/2 — Génération du RE-Projet-Auxiliaire</div>
                  </>
                )}
                {stepNumber === 3 && (
                  <>
                    <div>Étape 1/3 — Génération de l&apos;archive ZIP</div>
                    <div>Étape 2/3 — Génération du hash pour horodatage</div>
                    <div>Étape 3/3 — Stockage du hash</div>
                  </>
                )}
                <div style={{ marginTop: 8, fontStyle: "italic", fontSize: "0.85rem" }}>
                  Vous pouvez quitter cette page, le traitement continue en arrière-plan.
                </div>
                <button
                  type="button"
                  className={styles.btnDanger}
                  style={{ marginTop: 12 }}
                  onClick={async () => {
                    if (confirm("Annuler le traitement en cours ?")) {
                      try {
                        await dossiersApi.cancelStep(dossierId, stepNumber);
                        await fetchStep();
                      } catch { /* ignore */ }
                    }
                  }}
                >
                  ✕ Annuler
                </button>
              </div>
            </div>
          )}

          {/* File list */}
          <div className={styles.section}>
            <h2 className={styles.sectionTitle}>Fichiers de l&apos;étape</h2>
            <FileList
              dossierId={dossierId}
              stepNumber={stepNumber}
              files={step.files}
              isLocked={locked || isDossierClosed}
              showReplaceButton={showReplace}
              onFileReplaced={fetchStep}
            />
          </div>

          {/* Step-specific content */}
          {stepNumber === 0 && (
            <Step0View
              dossierId={dossierId}
              step={step}
              isLocked={locked || isDossierClosed}
              dossierStatut={dossierStatut}
              onRefresh={fetchStep}
            />
          )}
          {stepNumber === 1 && (
            <Step1View
              dossierId={dossierId}
              step={step}
              isLocked={locked || isDossierClosed}
              dossierStatut={dossierStatut}
              onRefresh={fetchStep}
            />
          )}
          {stepNumber === 2 && (
            <Step2View
              dossierId={dossierId}
              step={step}
              isLocked={locked || isDossierClosed}
              dossierStatut={dossierStatut}
              onRefresh={fetchStep}
            />
          )}
          {stepNumber === 3 && (
            <Step3View
              dossierId={dossierId}
              step={step}
              isLocked={locked || isDossierClosed}
              dossierStatut={dossierStatut}
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
  dossierStatut: string;
  onRefresh: () => Promise<void>;
}

function Step0View({ dossierId, step, isLocked, onRefresh }: StepViewProps) {
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [docxFile, setDocxFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");

  const hasDocx = step.files.some((f) => f.file_type === "docx");

  const handleExtract = async () => {
    if (!pdfFile) return;
    setExtracting(true);
    setActionError("");
    setActionSuccess("");
    try {
      await step0Api.extract(dossierId, pdfFile);
      setActionSuccess("Extraction terminée. Téléchargez le .docx pour vérification.");
      await onRefresh();
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Erreur lors de l'extraction."));
    } finally {
      setExtracting(false);
    }
  };

  const handleImportDocx = async () => {
    if (!docxFile) return;
    setImporting(true);
    setActionError("");
    setActionSuccess("");
    try {
      await step0Api.importDocx(dossierId, docxFile);
      setDocxFile(null);
      setActionSuccess("Document modifié importé avec succès.");
      await onRefresh();
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Erreur lors de l'import."));
    } finally {
      setImporting(false);
    }
  };

  return (
    <>
      {actionError && <p className={styles.error} role="alert">{actionError}</p>}
      {actionSuccess && <p className={styles.success}>{actionSuccess}</p>}

      {/* Upload & Extract */}
      {!isLocked && !hasDocx && (
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
            />
          </div>
          <div className={styles.actions}>
            {extracting ? (
              <div className={styles.extractingIndicator}>
                <span className={styles.hourglass} aria-hidden="true">⏳</span>
                <div>
                  <div>Étape 1/3 — OCR (extraction du texte)</div>
                  <div>Étape 2/3 — Structuration Markdown par l&apos;IA</div>
                  <div>Étape 3/3 — Génération du document Word</div>
                  <div style={{ marginTop: 8, fontStyle: "italic" }}>
                    Cette opération peut prendre plusieurs minutes…
                  </div>
                </div>
              </div>
            ) : (
              <button
                className={styles.btnPrimary}
                onClick={handleExtract}
                disabled={!pdfFile}
              >
                Extraction
              </button>
            )}
          </div>
        </div>
      )}

      {/* Import modified docx */}
      {!isLocked && hasDocx && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Importer un document modifié</h2>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: 12 }}>
            Téléchargez le .docx ci-dessus, modifiez-le si nécessaire, puis importez la version finale.
            Vous pouvez aussi valider directement le document tel quel.
          </p>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="docx-import">
              Document .docx modifié
            </label>
            <input
              id="docx-import"
              type="file"
              accept=".docx"
              className={styles.fileInput}
              onChange={(e) => setDocxFile(e.target.files?.[0] ?? null)}
            />
          </div>
          <div className={styles.actions}>
            <button
              className={styles.btnPrimary}
              onClick={handleImportDocx}
              disabled={!docxFile || importing}
            >
              {importing ? "Import…" : "Importer le .docx modifié"}
            </button>
          </div>
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
  const isRealise = step.statut === "fait";

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
    a.download = "qmec.docx";
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
          {!isLocked && !hasQmec && !executing && (
            <button
              className={styles.btnPrimary}
              onClick={handleExecute}
            >
              Générer le QMEC
            </button>
          )}

          {/* Hourglass during execution */}
          {executing && (
            <div className={styles.extractingIndicator}>
              <span className={styles.hourglass} aria-hidden="true">⏳</span>
              <div>
                <div>Étape 1/2 — Génération du plan d&apos;entretien par l&apos;IA</div>
                <div>Étape 2/2 — Génération du document Word</div>
                <div style={{ marginTop: 8, fontStyle: "italic" }}>
                  Cette opération peut prendre plusieurs minutes…
                </div>
              </div>
            </div>
          )}

          {/* Download */}
          {hasQmec && !executing && (
            <button className={styles.btnDownload} onClick={handleDownload}>
              ⬇ Download QMEC
            </button>
          )}

          {/* Validate */}
          {!isLocked && isRealise && !executing && (
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
/* Step2View — Mise en forme RE-Projet                                 */
/* ================================================================== */

function Step2View({ dossierId, step, isLocked, onRefresh }: StepViewProps) {
  const [neaFile, setNeaFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");

  const isRealise = step.statut === "fait";
  const hasFiles = step.files.length > 0;

  const handleUpload = async () => {
    setActionError("");
    setActionSuccess("");

    if (!neaFile) {
      setActionError("Veuillez sélectionner un fichier NEA (.docx).");
      return;
    }
    if (!neaFile.name.toLowerCase().endsWith(".docx")) {
      setActionError("Seul le format .docx est accepté.");
      return;
    }

    setUploading(true);
    try {
      const data = await step2Api.upload(dossierId, neaFile);
      setActionSuccess(
        `Fichiers générés avec succès : ${data.filenames.map((f: string) => f.replace(/\.tpl$/i, ".md")).join(", ")}`,
      );
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
      setActionSuccess("Step 2 validé avec succès.");
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

      {/* Upload NEA section */}
      {!isLocked && !hasFiles && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Upload du NEA</h2>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: 12 }}>
            Uploadez votre fichier NEA (Notes d&apos;Entretien et Analyse) au format .docx.
            L&apos;IA générera automatiquement le RE-Projet et le RE-Projet-Auxiliaire.
          </p>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="nea-upload">
              Notes d&apos;Entretien et Analyse (NEA)
            </label>
            <input
              id="nea-upload"
              type="file"
              accept=".docx"
              className={styles.fileInput}
              onChange={(e) => setNeaFile(e.target.files?.[0] ?? null)}
              disabled={isLocked}
            />
            <span className={styles.fileHint}>Format accepté : .docx uniquement</span>
          </div>
          <div className={styles.actions}>
            {uploading ? (
              <div className={styles.extractingIndicator}>
                <span className={styles.hourglass} aria-hidden="true">⏳</span>
<div>
                  <div>Étape 1/2 — Génération du RE-Projet par l&apos;IA</div>
                  <div>Étape 2/2 — Génération du RE-Projet-Auxiliaire</div>
                  <div style={{ marginTop: 8, fontStyle: 'italic' }}>
                    Cette opération peut prendre plusieurs minutes…
                  </div>
                </div>
              </div>
            ) : (
              <button
                className={styles.btnPrimary}
                onClick={handleUpload}
                disabled={!neaFile || isLocked}
              >
                Upload et générer
              </button>
            )}
          </div>
        </div>
      )}

      {/* Re-upload when files exist but step not locked */}
      {!isLocked && hasFiles && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Relancer la génération</h2>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: 12 }}>
            Vous pouvez uploader un nouveau fichier NEA pour relancer la génération.
          </p>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="nea-reupload">
              Nouveau fichier NEA (.docx)
            </label>
            <input
              id="nea-reupload"
              type="file"
              accept=".docx"
              className={styles.fileInput}
              onChange={(e) => setNeaFile(e.target.files?.[0] ?? null)}
              disabled={isLocked}
            />
            <span className={styles.fileHint}>Format accepté : .docx uniquement</span>
          </div>
          <div className={styles.actions}>
            {uploading ? (
              <div className={styles.extractingIndicator}>
                <span className={styles.hourglass} aria-hidden="true">⏳</span>
<div>
                  <div>Étape 1/2 — Génération du RE-Projet par l&apos;IA</div>
                  <div>Étape 2/2 — Génération du RE-Projet-Auxiliaire</div>
                  <div style={{ marginTop: 8, fontStyle: 'italic' }}>
                    Cette opération peut prendre plusieurs minutes…
                  </div>
                </div>
              </div>
            ) : (
              <button
                className={styles.btnPrimary}
                onClick={handleUpload}
                disabled={!neaFile || isLocked}
              >
                Upload et régénérer
              </button>
            )}
          </div>
        </div>
      )}

      {/* Validate section */}
      {!isLocked && isRealise && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Validation</h2>
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
    </>
  );
}


/* ================================================================== */
/* Step3View — Upload / Compression dossier final                            */
/* ================================================================== */

function Step3View({ dossierId, step, isLocked, onRefresh }: StepViewProps) {
  const [projetFile, setProjetFile] = useState<File | null>(null);
  const [executing, setExecuting] = useState(false);
  const [validating, setValidating] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");

  const hasArchive = step.files.some((f) => f.file_type === "archive_zip");
  const isRealise = step.statut === "fait";

  const handleExecute = async () => {
    setExecuting(true);
    setActionError("");
    setActionSuccess("");
    try {
      const data = await step3Api.execute(dossierId, projetFile ?? undefined);
      setActionSuccess(data.message);
      setProjetFile(null);
      await onRefresh();
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Erreur lors de la génération."));
    } finally {
      setExecuting(false);
    }
  };

  const handleValidate = async () => {
    setValidating(true);
    setActionError("");
    setActionSuccess("");
    try {
      await step3Api.validate(dossierId);
      setActionSuccess("Step 3 validé avec succès.");
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
        <h2 className={styles.sectionTitle}>Finalisation du dossier</h2>

        {!isLocked && !hasArchive && (
          <>
            <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: 12 }}>
              Uploadez le rapport d&apos;expertise final (.docx), puis lancez la génération
              de l&apos;archive et du hash d&apos;horodatage.
            </p>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="projet-final-upload">
                Rapport d&apos;expertise final (.docx)
              </label>
              <input
                id="projet-final-upload"
                type="file"
                accept=".docx"
                className={styles.fileInput}
                onChange={(e) => setProjetFile(e.target.files?.[0] ?? null)}
              />
            </div>
            <div className={styles.actions}>
              {executing ? (
                <div className={styles.extractingIndicator}>
                  <span className={styles.hourglass} aria-hidden="true">⏳</span>
                  <div>
                    <div>Étape 1/3 — Génération de l&apos;archive ZIP</div>
                    <div>Étape 2/3 — Génération du hash pour horodatage</div>
                    <div>Étape 3/3 — Stockage du hash</div>
                    <div style={{ marginTop: 8, fontStyle: "italic" }}>
                      Cette opération peut prendre quelques instants…
                    </div>
                  </div>
                </div>
              ) : (
                <button
                  className={styles.btnPrimary}
                  onClick={handleExecute}
                  disabled={!projetFile}
                >
                  Générer l&apos;archive et le hash
                </button>
              )}
            </div>
          </>
        )}

        {!isLocked && hasArchive && (
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: 12 }}>
            L&apos;archive et le hash ont été générés. Vous pouvez valider pour clore cette étape.
          </p>
        )}

        {!isLocked && isRealise && (
          <div className={styles.actions} style={{ marginTop: 16 }}>
            <button
              className={styles.btnPrimary}
              onClick={handleValidate}
              disabled={validating}
            >
              {validating ? "Validation…" : "Valider"}
            </button>
          </div>
        )}
      </div>
    </>
  );
}
