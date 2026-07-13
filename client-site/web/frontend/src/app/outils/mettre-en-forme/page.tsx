"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { revisionApi, getErrorMessage } from "@/lib/api";
import styles from "./mettre-en-forme.module.css";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type InputMode = "file" | "text";
type FormatterStatus = "idle" | "processing" | "done" | "error";

// ---------------------------------------------------------------------------
// InputModeTabs Component
// ---------------------------------------------------------------------------

interface InputModeTabsProps {
  activeMode: InputMode;
  onChange: (mode: InputMode) => void;
  disabled: boolean;
}

function InputModeTabs({ activeMode, onChange, disabled }: InputModeTabsProps) {
  return (
    <div className={styles.modeTabs} role="tablist" aria-label="Mode d'entrée">
      <button
        role="tab"
        aria-selected={activeMode === "file"}
        aria-controls="panel-file"
        id="tab-file"
        className={`${styles.modeTab} ${activeMode === "file" ? styles.modeTabActive : ""}`}
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
        className={`${styles.modeTab} ${activeMode === "text" ? styles.modeTabActive : ""}`}
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
}

function UploadCard({ onUpload }: UploadCardProps) {
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
        accept=".docx,.txt,.md"
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
  initialText?: string;
}

function TextInputCard({ onSubmit, initialText = "" }: TextInputCardProps) {
  const [text, setText] = useState(initialText);
  const maxChars = 100_000;

  // Sync with initialText when it changes (e.g. file loaded into text mode)
  useEffect(() => {
    if (initialText) setText(initialText);
  }, [initialText]);

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
        aria-label="Zone de saisie de texte pour correction"
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
          🚀 Réviser
        </button>
      </div>
    </div>
  );
}


// ---------------------------------------------------------------------------
// ProcessingTimer Component (ProgressCard with elapsed timer)
// ---------------------------------------------------------------------------

function ProcessingTimer({ onCancel }: { onCancel: () => void }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = Date.now();
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  const timeStr = mins > 0 ? `${mins}min ${secs.toString().padStart(2, "0")}s` : `${secs}s`;

  return (
    <div className={styles.card} role="status" aria-live="polite">
      <div className={styles.progressContent}>
        <div className={styles.spinner} aria-hidden="true" />
        <div>
          <p className={styles.progressText}>
            Traitement en cours… ⏳ LLM — <strong>{timeStr}</strong>
          </p>
          <p className={styles.progressHint}>
            La révision peut prendre plusieurs minutes selon la longueur du texte.
          </p>
        </div>
      </div>
      <button
        className={styles.btnSecondary}
        onClick={onCancel}
        type="button"
        style={{ marginTop: "12px" }}
      >
        ✕ Annuler
      </button>
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
// MettreEnFormePage — Main Page Component
// ---------------------------------------------------------------------------

export default function MettreEnFormePage() {
  const [inputMode, setInputMode] = useState<InputMode>("file");
  const [status, setStatus] = useState<FormatterStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [downloadFilename, setDownloadFilename] = useState<string>("fichier-revu.docx");
  const [outputText, setOutputText] = useState<string | null>(null);
  const [outputFilename, setOutputFilename] = useState<string | null>(null);
  const [inputText, setInputText] = useState<string>("");

  // --- File mode handler ---
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

    // For .docx: use the upload endpoint directly (returns revised file)
    // For .txt/.md: extract text and switch to text mode
    try {
      if (ext === "docx") {
        // Send .docx to /api/revision/upload for direct LLM revision
        setStatus("processing");
        setError(null);
        const result = await revisionApi.uploadFile(file);
        if (result instanceof Blob) {
          // .docx returns a Blob (revised file with track changes)
          const blobUrl = URL.createObjectURL(result);
          setDownloadUrl(blobUrl);
          setDownloadFilename(`revu-${file.name}`);
          setStatus("done");
        } else {
          // Fallback: text response
          setOutputText(result.corrected_text);
          setOutputFilename(result.filename);
          setStatus("done");
        }
      } else {
        // .txt/.md: read directly on client side and switch to text mode
        const text = await file.text();
        setInputText(text);
        setInputMode("text");
      }
    } catch (err) {
      setError(getErrorMessage(err, "Erreur lors de la révision du fichier."));
      setStatus("error");
    }
  }, []);

  // --- Text mode handler (revision only) ---
  const handleTextSubmit = useCallback(async (text: string) => {
    setStatus("processing");
    setError(null);
    setDownloadUrl(null);
    setOutputText(null);
    setOutputFilename(null);

    try {
      const result = await revisionApi.submitText(text);
      setOutputText(result.corrected_text);
      setOutputFilename(null);
      setStatus("done");
    } catch (err) {
      setError(getErrorMessage(err, "Erreur lors de la révision du texte."));
      setStatus("error");
    }
  }, []);

  // --- Reset handler ---
  const handleReset = useCallback(() => {
    if (downloadUrl) {
      URL.revokeObjectURL(downloadUrl);
    }
    setStatus("idle");
    setError(null);
    setDownloadUrl(null);
    setOutputText(null);
    setOutputFilename(null);
  }, [downloadUrl]);

  // --- Copy handler ---
  const handleCopy = useCallback(async () => {
    if (outputText) {
      try {
        await navigator.clipboard.writeText(outputText);
      } catch {
        // Fallback: some browsers block clipboard in non-secure contexts
      }
    }
  }, [outputText]);

  return (
    <div>
      <InputModeTabs
        activeMode={inputMode}
        onChange={setInputMode}
        disabled={status === "processing"}
      />

      {inputMode === "file" && status === "idle" && (
        <UploadCard onUpload={handleFileUpload} />
      )}

      {inputMode === "text" && status === "idle" && (
        <TextInputCard
          onSubmit={handleTextSubmit}
          initialText={inputText}
        />
      )}

      {status === "processing" && <ProcessingTimer onCancel={handleReset} />}

      {status === "done" && downloadUrl && (
        <DownloadCard
          url={downloadUrl}
          filename={downloadFilename}
          onReset={handleReset}
        />
      )}

      {status === "error" && (
        <ErrorCard message={error} onRetry={handleReset} />
      )}

      {status === "done" && outputText && (
        <>
          <OutputZone
            text={outputText}
            filename={outputFilename}
            onCopy={handleCopy}
          />
          <div className={styles.submitRow} style={{ marginTop: "12px" }}>
            <button
              className={styles.btnSecondary}
              onClick={handleReset}
              type="button"
              aria-label="Nouvelle révision"
            >
              🔄 Nouvelle révision
            </button>
          </div>
        </>
      )}
    </div>
  );
}
