"use client";

import { useState, useCallback, useRef } from "react";
import { revisionApi, getErrorMessage, type TextRevisionResponse } from "@/lib/api";
import styles from "./revision.module.css";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type InputMode = "file" | "text";
type RevisionStatus = "idle" | "uploading" | "processing" | "done" | "error";

// ---------------------------------------------------------------------------
// InputTabs Component
// ---------------------------------------------------------------------------

interface InputTabsProps {
  activeMode: InputMode;
  onChange: (mode: InputMode) => void;
  disabled: boolean;
}

function InputTabs({ activeMode, onChange, disabled }: InputTabsProps) {
  return (
    <div className={styles.tabs} role="tablist" aria-label="Mode d'entrée">
      <button
        role="tab"
        aria-selected={activeMode === "file"}
        aria-controls="panel-file"
        id="tab-file"
        className={`${styles.tab} ${activeMode === "file" ? styles.tabActive : ""}`}
        onClick={() => onChange("file")}
        disabled={disabled}
        type="button"
      >
        📄 Fichier
      </button>
      <button
        role="tab"
        aria-selected={activeMode === "text"}
        aria-controls="panel-text"
        id="tab-text"
        className={`${styles.tab} ${activeMode === "text" ? styles.tabActive : ""}`}
        onClick={() => onChange("text")}
        disabled={disabled}
        type="button"
      >
        ✏️ Texte
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// UploadCard Component
// ---------------------------------------------------------------------------

interface UploadCardProps {
  onUpload: (file: File) => void;
  accept: string;
}

function UploadCard({ onUpload, accept }: UploadCardProps) {
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) onUpload(file);
    },
    [onUpload],
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onUpload(file);
      // Reset input so the same file can be re-selected
      e.target.value = "";
    },
    [onUpload],
  );

  const handleClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        fileInputRef.current?.click();
      }
    },
    [],
  );

  return (
    <div
      id="panel-file"
      role="tabpanel"
      aria-labelledby="tab-file"
      className={styles.card}
    >
      <div
        className={`${styles.dropZone} ${dragOver ? styles.dropZoneDragOver : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        role="button"
        tabIndex={0}
        aria-label="Zone de dépôt de fichier. Cliquez ou glissez-déposez un fichier .docx, .txt ou .md"
      >
        <div className={styles.dropZoneIcon}>📁</div>
        <p className={styles.dropZoneText}>
          Glissez-déposez un fichier ici ou cliquez pour sélectionner
        </p>
        <p className={styles.dropZoneHint}>
          Formats acceptés : .docx, .txt, .md — Taille max : 20 Mo
        </p>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleFileChange}
        className={styles.fileInput}
        aria-hidden="true"
        tabIndex={-1}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// TextInputCard Component
// ---------------------------------------------------------------------------

interface TextInputCardProps {
  onSubmit: (text: string) => void;
}

function TextInputCard({ onSubmit }: TextInputCardProps) {
  const [text, setText] = useState("");
  const maxChars = 100_000;

  const handleSubmit = useCallback(() => {
    const trimmed = text.trim();
    if (trimmed.length > 0) {
      onSubmit(trimmed);
    }
  }, [text, onSubmit]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  return (
    <div
      id="panel-text"
      role="tabpanel"
      aria-labelledby="tab-text"
      className={styles.card}
    >
      <textarea
        className={styles.textarea}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Collez ou saisissez votre texte ici…"
        aria-label="Zone de saisie de texte pour révision"
        maxLength={maxChars}
        rows={10}
      />
      <div className={styles.charCount}>
        {text.length.toLocaleString("fr-FR")} / {maxChars.toLocaleString("fr-FR")} caractères
      </div>
      <div className={styles.submitRow}>
        <button
          className={styles.btnPrimary}
          onClick={handleSubmit}
          disabled={text.trim().length === 0}
          type="button"
          aria-label="Soumettre le texte pour révision"
        >
          🚀 Réviser le texte
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ProgressCard Component
// ---------------------------------------------------------------------------

function ProgressCard() {
  return (
    <div className={styles.card} role="status" aria-live="polite">
      <div className={styles.progressContent}>
        <div className={styles.spinner} aria-hidden="true" />
        <p className={styles.progressText}>
          Révision en cours… Le traitement peut prendre plusieurs minutes.
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// DownloadCard Component
// ---------------------------------------------------------------------------

interface DownloadCardProps {
  url: string;
  filename: string;
  onReset: () => void;
}

function DownloadCard({ url, filename, onReset }: DownloadCardProps) {
  return (
    <div className={styles.card} aria-label="Fichier révisé disponible">
      <div className={styles.downloadContent}>
        <div className={styles.downloadInfo}>
          <span className={styles.downloadIcon} aria-hidden="true">✅</span>
          <span className={styles.downloadLabel}>Révision terminée</span>
        </div>
        <div className={styles.downloadActions}>
          <a
            href={url}
            download={filename}
            className={styles.downloadLink}
            aria-label={`Télécharger ${filename}`}
          >
            ⬇️ Télécharger {filename}
          </a>
          <button
            className={styles.btnSecondary}
            onClick={onReset}
            type="button"
            aria-label="Nouvelle révision"
          >
            🔄 Nouvelle révision
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// OutputZone Component
// ---------------------------------------------------------------------------

interface OutputZoneProps {
  text: string;
  filename: string | null;
  onCopy: () => void;
}

function OutputZone({ text, filename, onCopy }: OutputZoneProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    onCopy();
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [onCopy]);

  // Generate a download URL for .txt/.md files
  const downloadUrl = filename
    ? URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }))
    : null;

  return (
    <section className={styles.outputSection} aria-label="Résultat de la révision">
      <h2 className={styles.outputTitle}>Texte corrigé</h2>
      <textarea
        className={`${styles.textarea} ${styles.textareaReadonly}`}
        readOnly
        value={text}
        rows={20}
        aria-label="Texte corrigé en lecture seule"
      />
      <div className={styles.outputActions}>
        <button
          className={styles.btnPrimary}
          onClick={handleCopy}
          type="button"
          aria-label="Copier le texte corrigé dans le presse-papiers"
        >
          📋 Copier
        </button>
        {copied && <span className={styles.copySuccess} aria-live="polite">Copié !</span>}
        {filename && downloadUrl && (
          <a
            href={downloadUrl}
            download={filename}
            className={styles.downloadLink}
            aria-label={`Télécharger ${filename}`}
          >
            ⬇️ Télécharger {filename}
          </a>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// ErrorCard Component
// ---------------------------------------------------------------------------

interface ErrorCardProps {
  message: string | null;
  onRetry: () => void;
}

function ErrorCard({ message, onRetry }: ErrorCardProps) {
  return (
    <div
      className={`${styles.card} ${styles.errorCard}`}
      role="alert"
      aria-live="assertive"
    >
      <div className={styles.errorContent}>
        <span className={styles.errorIcon} aria-hidden="true">⚠️</span>
        <div className={styles.errorBody}>
          <p className={styles.errorMessage}>
            {message || "Une erreur est survenue lors de la révision."}
          </p>
          <button
            className={styles.btnPrimary}
            onClick={onRetry}
            type="button"
            aria-label="Réessayer la révision"
          >
            🔄 Réessayer
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// RevisionPage — Main Page Component
// ---------------------------------------------------------------------------

export default function RevisionPage() {
  const [inputMode, setInputMode] = useState<InputMode>("file");
  const [status, setStatus] = useState<RevisionStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [downloadFilename, setDownloadFilename] = useState<string>("fichier-revu.docx");
  const [outputText, setOutputText] = useState<string | null>(null);
  const [outputFilename, setOutputFilename] = useState<string | null>(null);

  const handleFileUpload = useCallback(async (file: File) => {
    // Validate extension
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!ext || !["docx", "txt", "md"].includes(ext)) {
      setError("Format non supporté. Formats acceptés : .docx, .txt, .md");
      setStatus("error");
      return;
    }

    // Validate size (20 MB)
    if (file.size > 20 * 1024 * 1024) {
      setError("Le fichier dépasse la taille maximale de 20 Mo.");
      setStatus("error");
      return;
    }

    setStatus("processing");
    setError(null);
    setDownloadUrl(null);
    setOutputText(null);
    setOutputFilename(null);

    try {
      const result = await revisionApi.uploadFile(file);

      if (result instanceof Blob) {
        // .docx → create blob URL for download
        const url = URL.createObjectURL(result);
        setDownloadUrl(url);
        setDownloadFilename("fichier-revu.docx");
      } else {
        // .txt/.md → display corrected text in OutputZone
        const textResult = result as TextRevisionResponse;
        setOutputText(textResult.corrected_text);
        setOutputFilename(textResult.filename || null);
      }

      setStatus("done");
    } catch (err) {
      setError(getErrorMessage(err, "Erreur lors de la révision du fichier."));
      setStatus("error");
    }
  }, []);

  const handleTextSubmit = useCallback(async (text: string) => {
    setStatus("processing");
    setError(null);
    setDownloadUrl(null);
    setOutputText(null);
    setOutputFilename(null);

    try {
      const result = await revisionApi.submitText(text);
      setOutputText(result.corrected_text);
      setOutputFilename(null); // No download for copy-paste text
      setStatus("done");
    } catch (err) {
      setError(getErrorMessage(err, "Erreur lors de la révision du texte."));
      setStatus("error");
    }
  }, []);

  const handleRetry = useCallback(() => {
    // Clean up any existing blob URL
    if (downloadUrl) {
      URL.revokeObjectURL(downloadUrl);
    }
    setStatus("idle");
    setError(null);
    setDownloadUrl(null);
    setOutputText(null);
    setOutputFilename(null);
  }, [downloadUrl]);

  const handleCopy = useCallback(async () => {
    if (outputText) {
      try {
        await navigator.clipboard.writeText(outputText);
      } catch {
        // Fallback: some browsers block clipboard in non-secure contexts
        // The OutputZone component handles the visual feedback
      }
    }
  }, [outputText]);

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Révision documentaire</h1>
      <p className={styles.subtitle}>
        Soumettez un fichier ou du texte pour correction orthographique, grammaticale et amélioration de la lisibilité.
      </p>

      <InputTabs
        activeMode={inputMode}
        onChange={setInputMode}
        disabled={status === "processing"}
      />

      {inputMode === "file" && status === "idle" && (
        <UploadCard onUpload={handleFileUpload} accept=".docx,.txt,.md" />
      )}

      {inputMode === "text" && status === "idle" && (
        <TextInputCard onSubmit={handleTextSubmit} />
      )}

      {status === "processing" && <ProgressCard />}

      {status === "done" && downloadUrl && (
        <DownloadCard
          url={downloadUrl}
          filename={downloadFilename}
          onReset={handleRetry}
        />
      )}

      {status === "error" && (
        <ErrorCard message={error} onRetry={handleRetry} />
      )}

      {status === "done" && outputText && (
        <OutputZone
          text={outputText}
          filename={outputFilename}
          onCopy={handleCopy}
        />
      )}

      {/* Reset button when done with text output (no download card shown) */}
      {status === "done" && outputText && !downloadUrl && (
        <div className={styles.submitRow} style={{ marginTop: "16px" }}>
          <button
            className={styles.btnSecondary}
            onClick={handleRetry}
            type="button"
            aria-label="Nouvelle révision"
          >
            🔄 Nouvelle révision
          </button>
        </div>
      )}
    </div>
  );
}
