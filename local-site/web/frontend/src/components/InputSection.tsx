"use client";

import { useState } from "react";
import type { StepFileItem } from "@/lib/api";
import { step1Api, step3Api, step4Api, step5Api, getErrorMessage } from "@/lib/api";
import { getInputFiles } from "@/lib/stepConfig";
import FileList from "@/components/FileList";
import styles from "./InputSection.module.css";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface InputSectionProps {
  stepNumber: number;
  dossierId: string;
  files: StepFileItem[];
  isLocked: boolean;
  dossierStatut: string;
  mode?: "entretien" | "analyse";
  onFileUploaded: () => Promise<void>;
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ComplementaryEntry {
  file: File | null;
  label: string;
  extractOcr: boolean;
  docType: string;
  docFormat: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function InputSection({
  stepNumber,
  dossierId,
  files,
  isLocked,
  dossierStatut,
  mode,
  onFileUploaded,
}: InputSectionProps) {
  const inputFiles = getInputFiles(stepNumber, files);
  const isDossierClosed = dossierStatut === "fermé";
  const canUpload = !isLocked && !isDossierClosed;

  return (
    <section className={styles.section} aria-labelledby="input-section-title">
      <h2 id="input-section-title" className={styles.sectionTitle}>
        Fichiers d&apos;entrée
      </h2>

      {/* Mode-dependent template info for Step 2 */}
      {stepNumber === 2 && (
        <TemplateInfo mode={mode} />
      )}

      {/* File list or placeholder */}
      {inputFiles.length > 0 ? (
        <FileList
          dossierId={dossierId}
          stepNumber={stepNumber}
          files={inputFiles}
          isLocked={isLocked || isDossierClosed}
          showReplaceButton={canUpload}
          onFileReplaced={onFileUploaded}
        />
      ) : (
        <p className={styles.placeholder}>
          Aucun fichier d&apos;entrée disponible
        </p>
      )}

      {/* Upload controls for steps that accept uploads */}
      {canUpload && stepNumber === 1 && (
        <Step1Upload dossierId={dossierId} onFileUploaded={onFileUploaded} />
      )}
      {canUpload && stepNumber === 3 && (
        <Step3Upload dossierId={dossierId} onFileUploaded={onFileUploaded} />
      )}
      {canUpload && stepNumber === 4 && (
        <Step4Upload dossierId={dossierId} onFileUploaded={onFileUploaded} />
      )}
      {canUpload && stepNumber === 5 && (
        <Step5Upload dossierId={dossierId} onFileUploaded={onFileUploaded} />
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// TemplateInfo — Step 2 mode-dependent template display
// ---------------------------------------------------------------------------

function TemplateInfo({ mode }: { mode?: "entretien" | "analyse" }) {
  if (mode === "analyse") {
    return (
      <div className={styles.templateInfo}>
        <span className={styles.templateIcon} aria-hidden="true">📄</span>
        Template utilisé : <strong>TPA</strong> (Template de Plan d&apos;Analyse)
      </div>
    );
  }

  // Default to entretien mode
  return (
    <div className={styles.templateInfo}>
      <span className={styles.templateIcon} aria-hidden="true">📄</span>
      Template utilisé : <strong>TPE</strong> (Template de Plan d&apos;Entretien)
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step1Upload — Ordonnance + complementary files upload
// ---------------------------------------------------------------------------

function Step1Upload({
  dossierId,
  onFileUploaded,
}: {
  dossierId: string;
  onFileUploaded: () => Promise<void>;
}) {
  const [ordonnanceFile, setOrdonnanceFile] = useState<File | null>(null);
  const [complementaryFiles, setComplementaryFiles] = useState<ComplementaryEntry[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const addComplementaryFile = () => {
    setComplementaryFiles([
      ...complementaryFiles,
      { file: null, label: "", extractOcr: true, docType: "autre", docFormat: "pdf" },
    ]);
  };

  const updateComplementaryFile = (index: number, updates: Partial<ComplementaryEntry>) => {
    const updated = [...complementaryFiles];
    updated[index] = { ...updated[index], ...updates };
    setComplementaryFiles(updated);
  };

  const removeComplementaryFile = (index: number) => {
    setComplementaryFiles(complementaryFiles.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (!ordonnanceFile) return;
    setUploading(true);
    setError("");
    setSuccess("");
    try {
      await step1Api.upload(dossierId, ordonnanceFile);

      for (const entry of complementaryFiles) {
        if (entry.file) {
          await step1Api.uploadComplementary(
            dossierId,
            entry.file,
            entry.label,
            entry.extractOcr,
            entry.docType,
            entry.docFormat,
          );
        }
      }

      setSuccess("Fichiers importés — lancez l'extraction via le bouton ci-dessous.");
      setOrdonnanceFile(null);
      setComplementaryFiles([]);
      await onFileUploaded();
    } catch (err: unknown) {
      setError(getErrorMessage(err, "Erreur lors de l'import des fichiers."));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className={styles.uploadArea}>
      <h3 className={styles.uploadTitle}>Import des pièces constitutives</h3>

      {error && <p role="alert" style={{ fontSize: "0.875rem", color: "#dc2626", marginBottom: 12 }}>{error}</p>}
      {success && <p style={{ fontSize: "0.875rem", color: "#166534", marginBottom: 12 }}>{success}</p>}

      {/* Ordonnance */}
      <div className={styles.field}>
        <label className={styles.label} htmlFor="input-ordonnance-upload">
          Ordonnance (PDF) *
        </label>
        <input
          id="input-ordonnance-upload"
          type="file"
          accept=".pdf"
          className={styles.fileInput}
          onChange={(e) => setOrdonnanceFile(e.target.files?.[0] ?? null)}
          disabled={uploading}
        />
      </div>

      {/* Complementary files */}
      <h4 style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: 10 }}>
        Pièces complémentaires
      </h4>
      {complementaryFiles.map((entry, index) => (
        <div key={index} className={styles.complementaryRow}>
          <input
            type="text"
            placeholder="Nom de la pièce"
            className={styles.input}
            style={{ flex: "1 1 180px" }}
            value={entry.label}
            onChange={(e) => updateComplementaryFile(index, { label: e.target.value })}
            disabled={uploading}
          />
          <select
            className={styles.input}
            style={{ flex: "0 0 120px" }}
            value={entry.docType}
            onChange={(e) => updateComplementaryFile(index, { docType: e.target.value })}
            disabled={uploading}
          >
            <option value="rapport">Rapport</option>
            <option value="plainte">Plainte</option>
            <option value="autre">Autre</option>
          </select>
          <select
            className={styles.input}
            style={{ flex: "0 0 100px" }}
            value={entry.docFormat}
            onChange={(e) => {
              const fmt = e.target.value;
              const ocrEnabled = fmt === "pdf" || fmt === "scan";
              updateComplementaryFile(index, { docFormat: fmt, extractOcr: ocrEnabled });
            }}
            disabled={uploading}
          >
            <option value="pdf">PDF</option>
            <option value="scan">Scan</option>
            <option value="image">Image</option>
            <option value="csv">.csv</option>
            <option value="xlsx">.xlsx</option>
          </select>
          <input
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.csv,.xlsx,.xls"
            className={styles.fileInput}
            style={{ flex: "1 1 180px" }}
            onChange={(e) => updateComplementaryFile(index, { file: e.target.files?.[0] ?? null })}
            disabled={uploading}
          />
          {(entry.docFormat === "pdf" || entry.docFormat === "scan") && (
            <span className={styles.ocrHint}>→ OCR</span>
          )}
          <button
            type="button"
            className={styles.btnRemove}
            onClick={() => removeComplementaryFile(index)}
            aria-label="Supprimer cette pièce"
            disabled={uploading}
          >
            ✕
          </button>
        </div>
      ))}
      <button
        type="button"
        className={styles.btnSecondary}
        onClick={addComplementaryFile}
        disabled={uploading}
        style={{ marginTop: 8 }}
      >
        + Ajouter une pièce complémentaire
      </button>

      {/* Upload button */}
      <div style={{ marginTop: 16 }}>
        <button
          type="button"
          className={styles.btnSecondary}
          onClick={handleUpload}
          disabled={!ordonnanceFile || uploading}
          style={{ fontWeight: 600 }}
        >
          {uploading ? "Import en cours…" : "Importer les fichiers"}
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step3Upload — Diligence response files upload
// ---------------------------------------------------------------------------

function Step3Upload({
  dossierId,
  onFileUploaded,
}: {
  dossierId: string;
  onFileUploaded: () => Promise<void>;
}) {
  const [diligenceFiles, setDiligenceFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleUpload = async () => {
    if (diligenceFiles.length === 0) return;
    setUploading(true);
    setError("");
    setSuccess("");
    try {
      for (const file of diligenceFiles) {
        await step3Api.upload(dossierId, file);
      }
      setSuccess("Fichiers de diligence importés avec succès.");
      setDiligenceFiles([]);
      await onFileUploaded();
    } catch (err: unknown) {
      setError(getErrorMessage(err, "Erreur lors de l'import des fichiers de diligence."));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className={styles.uploadArea}>
      <h3 className={styles.uploadTitle}>Import des rapports de diligence</h3>

      {error && <p role="alert" style={{ fontSize: "0.875rem", color: "#dc2626", marginBottom: 12 }}>{error}</p>}
      {success && <p style={{ fontSize: "0.875rem", color: "#166534", marginBottom: 12 }}>{success}</p>}

      <div className={styles.field}>
        <label className={styles.label} htmlFor="input-diligence-upload">
          Rapports de diligence (PDF)
        </label>
        <input
          id="input-diligence-upload"
          type="file"
          accept=".pdf"
          multiple
          className={styles.fileInput}
          onChange={(e) => setDiligenceFiles(Array.from(e.target.files ?? []))}
          disabled={uploading}
        />
        <span className={styles.fileHint}>
          Vous pouvez sélectionner plusieurs fichiers
        </span>
      </div>

      <button
        type="button"
        className={styles.btnSecondary}
        onClick={handleUpload}
        disabled={diligenceFiles.length === 0 || uploading}
        style={{ fontWeight: 600 }}
      >
        {uploading ? "Import en cours…" : "Importer les fichiers"}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step4Upload — PEA/PAA annotated plan upload
// ---------------------------------------------------------------------------

function Step4Upload({
  dossierId,
  onFileUploaded,
}: {
  dossierId: string;
  onFileUploaded: () => Promise<void>;
}) {
  const [peaFile, setPeaFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleUpload = async () => {
    if (!peaFile) return;
    setUploading(true);
    setError("");
    setSuccess("");
    try {
      await step4Api.execute(dossierId, peaFile);
      setSuccess("PEA/PAA importé — pré-rapport en cours de génération.");
      setPeaFile(null);
      await onFileUploaded();
    } catch (err: unknown) {
      setError(getErrorMessage(err, "Erreur lors de l'import du PEA/PAA."));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className={styles.uploadArea}>
      <h3 className={styles.uploadTitle}>Import du Plan Annoté (PEA ou PAA)</h3>
      <p style={{ fontSize: "0.85rem", color: "#555", marginBottom: 12 }}>
        Importez le plan d&apos;entretien ou d&apos;analyse annoté avec vos observations
        (balises @dires, @analyse, @verbatim, @question, @reference).
      </p>

      {error && <p role="alert" style={{ fontSize: "0.875rem", color: "#dc2626", marginBottom: 12 }}>{error}</p>}
      {success && <p style={{ fontSize: "0.875rem", color: "#166534", marginBottom: 12 }}>{success}</p>}

      <div className={styles.field}>
        <label className={styles.label} htmlFor="input-pea-upload">
          Plan annoté (.docx) *
        </label>
        <input
          id="input-pea-upload"
          type="file"
          accept=".docx"
          className={styles.fileInput}
          onChange={(e) => setPeaFile(e.target.files?.[0] ?? null)}
          disabled={uploading}
        />
      </div>

      <button
        type="button"
        className={styles.btnSecondary}
        onClick={handleUpload}
        disabled={!peaFile || uploading}
        style={{ fontWeight: 600 }}
      >
        {uploading ? "Génération en cours…" : "Importer et générer le pré-rapport"}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step5Upload — REF (rapport final) upload
// ---------------------------------------------------------------------------

function Step5Upload({
  dossierId,
  onFileUploaded,
}: {
  dossierId: string;
  onFileUploaded: () => Promise<void>;
}) {
  const [refFile, setRefFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleUpload = async () => {
    if (!refFile) return;
    setUploading(true);
    setError("");
    setSuccess("");
    try {
      await step5Api.execute(dossierId, refFile);
      setSuccess("Rapport final importé — archive générée.");
      setRefFile(null);
      await onFileUploaded();
    } catch (err: unknown) {
      setError(getErrorMessage(err, "Erreur lors de l'archivage."));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className={styles.uploadArea}>
      <h3 className={styles.uploadTitle}>Import du Rapport Final (REF)</h3>
      <p style={{ fontSize: "0.85rem", color: "#555", marginBottom: 12 }}>
        Importez le rapport d&apos;expertise final ajusté et validé.
        L&apos;archivage créera un ZIP immuable avec un timbre d&apos;horodatage SHA-256.
      </p>

      {error && <p role="alert" style={{ fontSize: "0.875rem", color: "#dc2626", marginBottom: 12 }}>{error}</p>}
      {success && <p style={{ fontSize: "0.875rem", color: "#166534", marginBottom: 12 }}>{success}</p>}

      <div className={styles.field}>
        <label className={styles.label} htmlFor="input-ref-upload">
          Rapport final (.docx) *
        </label>
        <input
          id="input-ref-upload"
          type="file"
          accept=".docx"
          className={styles.fileInput}
          onChange={(e) => setRefFile(e.target.files?.[0] ?? null)}
          disabled={uploading}
        />
      </div>

      <button
        type="button"
        className={styles.btnSecondary}
        onClick={handleUpload}
        disabled={!refFile || uploading}
        style={{ fontWeight: 600 }}
      >
        {uploading ? "Archivage en cours…" : "Importer et archiver"}
      </button>
    </div>
  );
}
