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
import StepProgressList from "@/components/StepProgressList";

/* ------------------------------------------------------------------ */
/* Constants                                                           */
/* ------------------------------------------------------------------ */

const STEP_NAMES: Record<number, string> = {
  1: "Création dossier",
  2: "Préparation investigations",
  3: "Consolidation documentaire",
  4: "Production pré-rapport",
  5: "Finalisation et archivage",
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
    if (!isNaN(stepNumber) && stepNumber >= 1 && stepNumber <= 5) {
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

  const isValidStep = !isNaN(stepNumber) && stepNumber >= 1 && stepNumber <= 5;
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
                {stepNumber === 1 && (
                  <StepProgressList
                    active
                    steps={[
                      "Étape 1/3 — OCR (extraction du texte)",
                      "Étape 2/3 — Structuration et identification des questions",
                      "Étape 3/3 — Génération des documents",
                    ]}
                  />
                )}
                {stepNumber === 2 && (
                  <StepProgressList
                    active
                    steps={[
                      "Étape 1/3 — Génération des trames d'entretien/audition",
                      "Étape 2/3 — Génération des courriers de diligence",
                      "Étape 3/3 — Génération des documents Word",
                    ]}
                  />
                )}
                {stepNumber === 3 && (
                  <StepProgressList
                    active
                    steps={[
                      "Étape 1/2 — OCR (extraction du texte)",
                      "Étape 2/2 — Mise en forme pour validation",
                    ]}
                  />
                )}
                {stepNumber === 4 && (
                  <StepProgressList
                    active
                    steps={[
                      "Étape 1/4 — Mise en forme des entretiens/auditions",
                      "Étape 2/4 — Génération de l'analyse",
                      "Étape 3/4 — Génération des réponses conclusives",
                      "Étape 4/4 — Assemblage du pré-rapport final",
                    ]}
                  />
                )}
                {stepNumber === 5 && (
                  <StepProgressList
                    active
                    steps={[
                      "Étape 1/3 — Génération de l'archive ZIP",
                      "Étape 2/3 — Génération du hash pour horodatage",
                      "Étape 3/3 — Stockage du hash sur S3",
                    ]}
                  />
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
          {stepNumber === 4 && (
            <Step4View
              dossierId={dossierId}
              step={step}
              isLocked={locked || isDossierClosed}
              dossierStatut={dossierStatut}
              onRefresh={fetchStep}
            />
          )}
          {stepNumber === 5 && (
            <Step5View
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
/* Step1View — Création dossier                                        */
/* ================================================================== */

interface StepViewProps {
  dossierId: string;
  step: StepDetail;
  isLocked: boolean;
  dossierStatut: string;
  onRefresh: () => Promise<void>;
}

interface FileEntry {
  file: File | null;
  label: string;
  extractOcr: boolean;
}

function Step1View({ dossierId, step, isLocked, onRefresh }: StepViewProps) {
  const [ordonnanceFile, setOrdonnanceFile] = useState<File | null>(null);
  const [complementaryFiles, setComplementaryFiles] = useState<FileEntry[]>([]);
  const [extracting, setExtracting] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");

  const hasOutput = step.files.some((f) => f.file_type === "ordonnance_ocr" || f.file_type === "docx");

  const addComplementaryFile = () => {
    setComplementaryFiles([...complementaryFiles, { file: null, label: "", extractOcr: true }]);
  };

  const updateComplementaryFile = (index: number, updates: Partial<FileEntry>) => {
    const updated = [...complementaryFiles];
    updated[index] = { ...updated[index], ...updates };
    setComplementaryFiles(updated);
  };

  const removeComplementaryFile = (index: number) => {
    setComplementaryFiles(complementaryFiles.filter((_, i) => i !== index));
  };

  const handleExtract = async () => {
    if (!ordonnanceFile) return;
    setExtracting(true);
    setActionError("");
    setActionSuccess("");
    try {
      await step0Api.extract(dossierId, ordonnanceFile);
      setActionSuccess("Extraction terminée. Vérifiez les fichiers générés.");
      await onRefresh();
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Erreur lors de l'extraction."));
    } finally {
      setExtracting(false);
    }
  };

  return (
    <>
      {actionError && <p className={styles.error} role="alert">{actionError}</p>}
      {actionSuccess && <p className={styles.success}>{actionSuccess}</p>}

      {/* Upload ordonnance + pièces complémentaires */}
      {!isLocked && !hasOutput && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Import des pièces constitutives</h2>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: 16 }}>
            Importez l&apos;ordonnance (obligatoire) et les pièces complémentaires.
            Pour chaque fichier, nommez-le et indiquez si l&apos;extraction OCR est souhaitée.
          </p>

          {/* Ordonnance */}
          <div className={styles.field}>
            <label className={styles.label} htmlFor="ordonnance-upload">
              Ordonnance (PDF) *
            </label>
            <input
              id="ordonnance-upload"
              type="file"
              accept=".pdf"
              className={styles.fileInput}
              onChange={(e) => setOrdonnanceFile(e.target.files?.[0] ?? null)}
            />
          </div>

          {/* Pièces complémentaires */}
          <div style={{ marginTop: 20 }}>
            <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 12 }}>
              Pièces complémentaires
            </h3>
            {complementaryFiles.map((entry, index) => (
              <div key={index} style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 12, flexWrap: "wrap" }}>
                <input
                  type="text"
                  placeholder="Nom de la pièce"
                  className={styles.input}
                  style={{ flex: "1 1 200px" }}
                  value={entry.label}
                  onChange={(e) => updateComplementaryFile(index, { label: e.target.value })}
                />
                <input
                  type="file"
                  accept=".pdf,.docx,.jpg,.jpeg,.png"
                  className={styles.fileInput}
                  style={{ flex: "1 1 200px" }}
                  onChange={(e) => updateComplementaryFile(index, { file: e.target.files?.[0] ?? null })}
                />
                <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.85rem", whiteSpace: "nowrap" }}>
                  <input
                    type="checkbox"
                    checked={entry.extractOcr}
                    onChange={(e) => updateComplementaryFile(index, { extractOcr: e.target.checked })}
                  />
                  Extraction OCR
                </label>
                <button
                  type="button"
                  onClick={() => removeComplementaryFile(index)}
                  style={{ background: "none", border: "none", color: "red", cursor: "pointer", fontSize: "1.2rem" }}
                  aria-label="Supprimer cette pièce"
                >
                  ✕
                </button>
              </div>
            ))}
            <button
              type="button"
              className={styles.btnSecondary}
              onClick={addComplementaryFile}
              style={{ marginTop: 8 }}
            >
              + Ajouter une pièce complémentaire
            </button>
          </div>

          <div className={styles.actions} style={{ marginTop: 20 }}>
            {extracting ? (
              <div className={styles.extractingIndicator}>
                <span className={styles.hourglass} aria-hidden="true">⏳</span>
                <div>
                  <StepProgressList
                    active
                    steps={[
                      "Étape 1/3 — OCR (extraction du texte)",
                      "Étape 2/3 — Structuration et identification des questions",
                      "Étape 3/3 — Génération des documents",
                    ]}
                  />
                  <div style={{ marginTop: 8, fontStyle: "italic" }}>
                    Cette opération peut prendre plusieurs minutes…
                  </div>
                </div>
              </div>
            ) : (
              <button
                className={styles.btnPrimary}
                onClick={handleExtract}
                disabled={!ordonnanceFile}
              >
                Lancer l&apos;extraction
              </button>
            )}
          </div>
        </div>
      )}

      {/* Résultats */}
      {!isLocked && hasOutput && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Résultats</h2>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: 12 }}>
            L&apos;ordonnance a été extraite. Vérifiez le texte OCR et la liste des questions identifiées.
            Vous pouvez valider pour passer à l&apos;étape suivante.
          </p>
        </div>
      )}
    </>
  );
}


/* ================================================================== */
/* Step2View — Préparation investigations                              */
/* ================================================================== */

function Step2View({ dossierId, step, isLocked, onRefresh }: StepViewProps) {
  const [diligences, setDiligences] = useState<Array<{ destinataire: string; objet: string; echeance: string }>>([
    { destinataire: "", objet: "", echeance: "" },
  ]);
  const [executing, setExecuting] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");

  const hasOutput = step.files.some((f) =>
    f.file_type === "trame_entretien" || f.file_type === "courrier_diligence"
  );

  const addDiligence = () => {
    setDiligences([...diligences, { destinataire: "", objet: "", echeance: "" }]);
  };

  const updateDiligence = (index: number, field: string, value: string) => {
    const updated = [...diligences];
    updated[index] = { ...updated[index], [field]: value };
    setDiligences(updated);
  };

  const removeDiligence = (index: number) => {
    if (diligences.length > 1) {
      setDiligences(diligences.filter((_, i) => i !== index));
    }
  };

  const handleExecute = async () => {
    setExecuting(true);
    setActionError("");
    setActionSuccess("");
    try {
      await step1Api.execute(dossierId);
      setActionSuccess("Trames d'entretien et courriers de diligence générés avec succès.");
      await onRefresh();
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Erreur lors de la génération."));
    } finally {
      setExecuting(false);
    }
  };

  return (
    <>
      {actionError && <p className={styles.error} role="alert">{actionError}</p>}
      {actionSuccess && <p className={styles.success}>{actionSuccess}</p>}

      {!isLocked && !hasOutput && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Préparation des investigations</h2>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: 16 }}>
            Les trames d&apos;entretien/audition seront générées à partir du template configuré
            (par défaut ou personnalisé dans le paramétrage module).
          </p>

          {/* Diligences */}
          <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 12 }}>
            Diligences à émettre
          </h3>
          <p style={{ fontSize: "0.85rem", color: "var(--color-text-muted)", marginBottom: 12 }}>
            Ajoutez une note par diligence : à qui, quoi, pour quand.
          </p>
          {diligences.map((d, index) => (
            <div key={index} style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 10, flexWrap: "wrap" }}>
              <input
                type="text"
                placeholder="Destinataire (à qui)"
                className={styles.input}
                style={{ flex: "1 1 150px" }}
                value={d.destinataire}
                onChange={(e) => updateDiligence(index, "destinataire", e.target.value)}
              />
              <input
                type="text"
                placeholder="Objet (quoi)"
                className={styles.input}
                style={{ flex: "2 1 200px" }}
                value={d.objet}
                onChange={(e) => updateDiligence(index, "objet", e.target.value)}
              />
              <input
                type="date"
                className={styles.input}
                style={{ flex: "0 0 150px" }}
                value={d.echeance}
                onChange={(e) => updateDiligence(index, "echeance", e.target.value)}
              />
              {diligences.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeDiligence(index)}
                  style={{ background: "none", border: "none", color: "red", cursor: "pointer", fontSize: "1.2rem" }}
                  aria-label="Supprimer cette diligence"
                >
                  ✕
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            className={styles.btnSecondary}
            onClick={addDiligence}
            style={{ marginTop: 8, marginBottom: 20 }}
          >
            + Ajouter une diligence
          </button>

          <div className={styles.actions}>
            {executing ? (
              <div className={styles.extractingIndicator}>
                <span className={styles.hourglass} aria-hidden="true">⏳</span>
                <div>
                  <StepProgressList
                    active
                    steps={[
                      "Étape 1/3 — Génération des trames d'entretien/audition",
                      "Étape 2/3 — Génération des courriers de diligence",
                      "Étape 3/3 — Génération des documents Word",
                    ]}
                  />
                  <div style={{ marginTop: 8, fontStyle: "italic" }}>
                    Cette opération peut prendre plusieurs minutes…
                  </div>
                </div>
              </div>
            ) : (
              <button
                className={styles.btnPrimary}
                onClick={handleExecute}
              >
                Générer les trames et courriers
              </button>
            )}
          </div>
        </div>
      )}

      {/* Résultats */}
      {!isLocked && hasOutput && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Documents générés</h2>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: 12 }}>
            Les trames d&apos;entretien/audition et les courriers de diligence ont été générés.
            Téléchargez-les, vérifiez et émettez les courriers séparément.
          </p>
        </div>
      )}
    </>
  );
}


/* ================================================================== */
/* Step3View — Consolidation documentaire (optionnel)                  */
/* ================================================================== */

function Step3View({ dossierId, step, isLocked, onRefresh }: StepViewProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [extracting, setExtracting] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");

  const hasOutput = step.files.some((f) => f.file_type === "diligence_ocr");

  const handleExtract = async () => {
    if (files.length === 0) return;
    setExtracting(true);
    setActionError("");
    setActionSuccess("");
    try {
      for (const file of files) {
        await step2Api.upload(dossierId, file);
      }
      setActionSuccess("Rapports de diligence importés et extraits avec succès.");
      setFiles([]);
      await onRefresh();
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Erreur lors de l'extraction."));
    } finally {
      setExtracting(false);
    }
  };

  return (
    <>
      {actionError && <p className={styles.error} role="alert">{actionError}</p>}
      {actionSuccess && <p className={styles.success}>{actionSuccess}</p>}

      {!isLocked && !hasOutput && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Import des rapports de diligence auxiliaires</h2>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: 16 }}>
            Cette étape est optionnelle. Importez les rapports de diligence auxiliaires
            reçus si nécessaire. L&apos;extraction OCR sera effectuée pour validation.
          </p>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="diligence-upload">
              Rapports de diligence (PDF)
            </label>
            <input
              id="diligence-upload"
              type="file"
              accept=".pdf"
              multiple
              className={styles.fileInput}
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            />
            <span className={styles.fileHint}>
              Vous pouvez sélectionner plusieurs fichiers
            </span>
          </div>
          <div className={styles.actions}>
            {extracting ? (
              <div className={styles.extractingIndicator}>
                <span className={styles.hourglass} aria-hidden="true">⏳</span>
                <div>
                  <StepProgressList
                    active
                    steps={[
                      "Étape 1/2 — OCR (extraction du texte)",
                      "Étape 2/2 — Mise en forme pour validation",
                    ]}
                  />
                  <div style={{ marginTop: 8, fontStyle: "italic" }}>
                    Cette opération peut prendre plusieurs minutes…
                  </div>
                </div>
              </div>
            ) : (
              <button
                className={styles.btnPrimary}
                onClick={handleExtract}
                disabled={files.length === 0}
              >
                Importer et extraire
              </button>
            )}
          </div>
        </div>
      )}

      {!isLocked && hasOutput && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Résultats de l&apos;extraction</h2>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: 12 }}>
            Vérifiez les extractions OCR ci-dessus. Validez pour passer à l&apos;étape suivante.
          </p>
        </div>
      )}
    </>
  );
}


/* ================================================================== */
/* Step4View — Production pré-rapport                                  */
/* ================================================================== */

function Step4View({ dossierId, step, isLocked, onRefresh }: StepViewProps) {
  const [trameFiles, setTrameFiles] = useState<File[]>([]);
  const [notesFile, setNotesFile] = useState<File | null>(null);
  const [templateFile, setTemplateFile] = useState<File | null>(null);
  const [executing, setExecuting] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");

  const hasOutput = step.files.some((f) => f.file_type === "pre_rapport");

  const handleExecute = async () => {
    if (trameFiles.length === 0 || !notesFile) return;
    setExecuting(true);
    setActionError("");
    setActionSuccess("");
    try {
      const data = await step3Api.execute(dossierId, notesFile);
      setActionSuccess(data.message || "Pré-rapport généré avec succès.");
      await onRefresh();
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Erreur lors de la génération du pré-rapport."));
    } finally {
      setExecuting(false);
    }
  };

  return (
    <>
      {actionError && <p className={styles.error} role="alert">{actionError}</p>}
      {actionSuccess && <p className={styles.success}>{actionSuccess}</p>}

      {!isLocked && !hasOutput && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Production du pré-rapport</h2>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: 16 }}>
            Importez les templates d&apos;entretien/audition annotés (style télégraphique)
            et vos notes d&apos;analyse et conclusions. Le format de rapport par défaut sera
            utilisé sauf si vous fournissez un template personnalisé.
          </p>

          {/* Trames annotées */}
          <div className={styles.field}>
            <label className={styles.label} htmlFor="trames-upload">
              Templates entretien/audition annotés (.docx) *
            </label>
            <input
              id="trames-upload"
              type="file"
              accept=".docx"
              multiple
              className={styles.fileInput}
              onChange={(e) => setTrameFiles(Array.from(e.target.files ?? []))}
            />
            <span className={styles.fileHint}>
              Trames avec annotations télégraphiques de l&apos;expert
            </span>
          </div>

          {/* Notes expert */}
          <div className={styles.field} style={{ marginTop: 16 }}>
            <label className={styles.label} htmlFor="notes-upload">
              Notes expert — analyses et conclusions (.docx) *
            </label>
            <input
              id="notes-upload"
              type="file"
              accept=".docx"
              className={styles.fileInput}
              onChange={(e) => setNotesFile(e.target.files?.[0] ?? null)}
            />
            <span className={styles.fileHint}>
              Vos analyses et réponses conclusives pour chaque question
            </span>
          </div>

          {/* Template rapport (optionnel) */}
          <div className={styles.field} style={{ marginTop: 16 }}>
            <label className={styles.label} htmlFor="template-rapport-upload">
              Format de rapport personnalisé (.docx) — optionnel
            </label>
            <input
              id="template-rapport-upload"
              type="file"
              accept=".docx"
              className={styles.fileInput}
              onChange={(e) => setTemplateFile(e.target.files?.[0] ?? null)}
            />
            <span className={styles.fileHint}>
              Si non fourni, le format par défaut du domaine sera utilisé
            </span>
          </div>

          <div className={styles.actions} style={{ marginTop: 20 }}>
            {executing ? (
              <div className={styles.extractingIndicator}>
                <span className={styles.hourglass} aria-hidden="true">⏳</span>
                <div>
                  <StepProgressList
                    active
                    steps={[
                      "Étape 1/4 — Mise en forme des entretiens/auditions",
                      "Étape 2/4 — Génération de l'analyse",
                      "Étape 3/4 — Génération des réponses conclusives",
                      "Étape 4/4 — Assemblage du pré-rapport final",
                    ]}
                  />
                  <div style={{ marginTop: 8, fontStyle: "italic" }}>
                    Cette opération peut prendre plusieurs minutes…
                  </div>
                </div>
              </div>
            ) : (
              <button
                className={styles.btnPrimary}
                onClick={handleExecute}
                disabled={trameFiles.length === 0 || !notesFile}
              >
                Générer le pré-rapport
              </button>
            )}
          </div>
        </div>
      )}

      {!isLocked && hasOutput && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Pré-rapport généré</h2>
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: 12 }}>
            Le pré-rapport intègre la restitution des entretiens (trames annotées mises en forme),
            l&apos;analyse générée, les réponses conclusives et les mentions des documents annexes
            (courriers de diligence et réponses). Téléchargez-le, ajustez-le et validez.
          </p>
        </div>
      )}
    </>
  );
}


/* ================================================================== */
/* Step5View — Finalisation et archivage sécurisé                      */
/* ================================================================== */

function Step5View({ dossierId, step, isLocked, onRefresh }: StepViewProps) {
  const [rapportFile, setRapportFile] = useState<File | null>(null);
  const [executing, setExecuting] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");

  const hasArchive = step.files.some((f) => f.file_type === "archive_zip");

  const handleExecute = async () => {
    if (!rapportFile) return;
    setExecuting(true);
    setActionError("");
    setActionSuccess("");
    try {
      const data = await step3Api.execute(dossierId, rapportFile);
      setActionSuccess(data.message || "Archive et hash générés avec succès.");
      setRapportFile(null);
      await onRefresh();
    } catch (err: unknown) {
      setActionError(getErrorMessage(err, "Erreur lors de la finalisation."));
    } finally {
      setExecuting(false);
    }
  };

  return (
    <>
      {actionError && <p className={styles.error} role="alert">{actionError}</p>}
      {actionSuccess && <p className={styles.success}>{actionSuccess}</p>}

      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Finalisation et archivage</h2>

        {!isLocked && !hasArchive && (
          <>
            <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: 16 }}>
              Importez uniquement le rapport final ajusté et validé par vos soins.
              L&apos;archive .zip sera créée avec l&apos;ensemble des fichiers du dossier
              et un hash sera généré pour horodatage (stocké sur S3).
            </p>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="rapport-final-upload">
                Rapport final validé (.docx) *
              </label>
              <input
                id="rapport-final-upload"
                type="file"
                accept=".docx"
                className={styles.fileInput}
                onChange={(e) => setRapportFile(e.target.files?.[0] ?? null)}
              />
            </div>
            <div className={styles.actions} style={{ marginTop: 16 }}>
              {executing ? (
                <div className={styles.extractingIndicator}>
                  <span className={styles.hourglass} aria-hidden="true">⏳</span>
                  <div>
                    <StepProgressList
                      active
                      steps={[
                        "Étape 1/3 — Génération de l'archive ZIP",
                        "Étape 2/3 — Génération du hash pour horodatage",
                        "Étape 3/3 — Stockage du hash sur S3",
                      ]}
                    />
                    <div style={{ marginTop: 8, fontStyle: "italic" }}>
                      Cette opération peut prendre quelques instants…
                    </div>
                  </div>
                </div>
              ) : (
                <button
                  className={styles.btnPrimary}
                  onClick={handleExecute}
                  disabled={!rapportFile}
                >
                  Finaliser et archiver
                </button>
              )}
            </div>
          </>
        )}

        {!isLocked && hasArchive && (
          <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: 12 }}>
            L&apos;archive .zip et le hash d&apos;horodatage ont été générés.
            Le hash est stocké sur S3 pour traçabilité. Validez pour clore cette étape.
          </p>
        )}
      </div>
    </>
  );
}
