"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { revisionApi, getErrorMessage } from "@/lib/api";
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
// TextInputCardWithSummarize Component — Réviser + Résumer
// ---------------------------------------------------------------------------

interface TextInputCardWithSummarizeProps {
  onSubmitRevise: (text: string) => void;
  onSubmitSummarize: (text: string) => void;
  initialText?: string;
}

function TextInputCardWithSummarize({ onSubmitRevise, onSubmitSummarize, initialText = "" }: TextInputCardWithSummarizeProps) {
  const [text, setText] = useState(initialText);
  const maxChars = 100_000;

  // Sync with initialText when it changes (transfer from output)
  useState(() => { if (initialText) setText(initialText); });

  const handleRevise = useCallback(() => {
    const trimmed = text.trim();
    if (trimmed.length > 0) onSubmitRevise(trimmed);
  }, [text, onSubmitRevise]);

  const handleSummarize = useCallback(() => {
    const trimmed = text.trim();
    if (trimmed.length > 0) onSubmitSummarize(trimmed);
  }, [text, onSubmitSummarize]);

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
        placeholder="Collez ou saisissez votre texte ici…"
        aria-label="Zone de saisie de texte"
        maxLength={maxChars}
        rows={10}
      />
      <div className={styles.charCount}>
        {text.length.toLocaleString("fr-FR")} / {maxChars.toLocaleString("fr-FR")} caractères
      </div>
      <div className={styles.submitRow} style={{ gap: "12px", display: "flex", flexWrap: "wrap" }}>
        <button
          className={styles.btnPrimary}
          onClick={handleRevise}
          disabled={text.trim().length === 0}
          type="button"
        >
          🚀 Réviser
        </button>
        <button
          className={styles.btnPrimary}
          onClick={handleSummarize}
          disabled={text.trim().length === 0}
          type="button"
          style={{ backgroundColor: "#7c3aed" }}
        >
          📝 Résumer
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ProgressCard Component
// ---------------------------------------------------------------------------

function ProgressCard({ onCancel }: { onCancel: () => void }) {
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
          <p style={{ fontSize: "0.8rem", color: "#6b7280", margin: "4px 0" }}>
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
  const [inputText, setInputText] = useState<string>("");

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

    // Extraire le texte du fichier et le mettre dans la zone de saisie
    try {
      if (ext === "docx") {
        // Pour .docx : lire via le backend (extraction texte)
        const formData = new FormData();
        formData.append("file", file);
        const token = localStorage.getItem("token");
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${API_URL}/api/revision/extract-text`, {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "Erreur lors de l'extraction du texte");
        }
        const data = await res.json();
        setInputText(data.text);
      } else {
        // .txt/.md : lire directement côté client
        const text = await file.text();
        setInputText(text);
      }
      // Passer en mode texte pour afficher le contenu et les boutons d'action
      setInputMode("text");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors du chargement du fichier.");
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
      setOutputFilename(null);
      setStatus("done");
    } catch (err) {
      setError(getErrorMessage(err, "Erreur lors de la révision du texte."));
      setStatus("error");
    }
  }, []);

  const handleSummarize = useCallback(async (text: string) => {
    setStatus("processing");
    setError(null);
    setDownloadUrl(null);
    setOutputText(null);
    setOutputFilename(null);

    try {
      const result = await revisionApi.summarize(text);
      setOutputText(result.summary);
      setOutputFilename(null);
      setStatus("done");
    } catch (err) {
      setError(getErrorMessage(err, "Erreur lors du résumé."));
      setStatus("error");
    }
  }, []);

  const handleTransferToInput = useCallback(() => {
    if (outputText) {
      setInputText(outputText);
      setInputMode("text");
      setStatus("idle");
      setOutputText(null);
      setOutputFilename(null);
      setDownloadUrl(null);
    }
  }, [outputText]);

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
      }
    }
  }, [outputText]);

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Révision & Résumé</h1>
      <p className={styles.subtitle}>
        Soumettez un fichier ou du texte pour correction orthographique/grammaticale ou pour résumé.
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
        <TextInputCardWithSummarize
          onSubmitRevise={handleTextSubmit}
          onSubmitSummarize={handleSummarize}
          initialText={inputText}
        />
      )}

      {status === "processing" && <ProgressCard onCancel={handleRetry} />}

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
        <>
          <OutputZone
            text={outputText}
            filename={outputFilename}
            onCopy={handleCopy}
          />
          <div className={styles.submitRow} style={{ marginTop: "12px", gap: "12px", display: "flex", flexWrap: "wrap" }}>
            <button
              className={styles.btnPrimary}
              onClick={handleTransferToInput}
              type="button"
              aria-label="Transférer le résultat dans la zone d'entrée"
              style={{ backgroundColor: "#7c3aed" }}
            >
              ⇒ Utiliser comme entrée
            </button>
            <button
              className={styles.btnSecondary}
              onClick={handleRetry}
              type="button"
              aria-label="Nouvelle opération"
            >
              🔄 Nouvelle opération
            </button>
          </div>
        </>
      )}
    </div>
  );
}
