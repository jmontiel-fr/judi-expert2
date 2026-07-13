"use client";

import { useCallback, useRef, useState } from "react";
import {
  type StepFileItem,
  stepFilesApi,
  getErrorMessage,
  formatFileSize,
} from "@/lib/api";
import styles from "./FileList.module.css";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface FileListProps {
  dossierId: string | number;
  stepNumber: number;
  files: StepFileItem[];
  isLocked: boolean;
  showReplaceButton: boolean;
  showDeleteButton?: boolean;
  onFileReplaced?: () => void;
  onFileDeleted?: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getExtension(filename: string): string {
  const dot = filename.lastIndexOf(".");
  return dot >= 0 ? filename.slice(dot).toLowerCase() : "";
}

// ---------------------------------------------------------------------------
// Single file row
// ---------------------------------------------------------------------------

function FileRow({
  file,
  dossierId,
  stepNumber,
  isLocked,
  showReplaceButton,
  showDeleteButton,
  onFileReplaced,
  onFileDeleted,
}: {
  file: StepFileItem;
  dossierId: string | number;
  stepNumber: number;
  isLocked: boolean;
  showReplaceButton: boolean;
  showDeleteButton?: boolean;
  onFileReplaced?: () => void;
  onFileDeleted?: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [replacing, setReplacing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [mdPreview, setMdPreview] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const ext = getExtension(file.filename);

  const handleOpen = useCallback(async () => {
    setError(null);
    if (ext === ".md") {
      // Inline preview — fetch via view endpoint
      try {
        const url = stepFilesApi.getViewUrl(dossierId, stepNumber, file.id);
        const res = await fetch(url);
        if (!res.ok) {
          setError("Fichier introuvable");
          return;
        }
        const text = await res.text();
        setMdPreview((prev) => (prev === null ? text : null)); // toggle
      } catch {
        setError("Fichier introuvable");
      }
    } else {
      // PDF / DOCX — open in new tab
      const url = stepFilesApi.getViewUrl(dossierId, stepNumber, file.id);
      window.open(url, "_blank", "noopener,noreferrer");
    }
  }, [dossierId, stepNumber, file.id, ext]);

  const handleDownload = useCallback(() => {
    const url = stepFilesApi.getDownloadUrl(dossierId, stepNumber, file.id);
    const a = document.createElement("a");
    a.href = url;
    a.download = file.filename.replace(/\.tpl$/i, ".md");
    a.click();
  }, [dossierId, stepNumber, file.id, file.filename]);

  const handleReplaceClick = useCallback(() => {
    inputRef.current?.click();
  }, []);

  const handleFileSelected = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0];
      if (!selected) return;

      // Validate extension matches original
      const selectedExt = getExtension(selected.name);
      if (selectedExt !== ext) {
        setError(`Le fichier doit avoir la même extension que l'original (${ext})`);
        // Reset input so the same file can be re-selected
        if (inputRef.current) inputRef.current.value = "";
        return;
      }

      setError(null);
      setReplacing(true);
      try {
        await stepFilesApi.replaceFile(dossierId, stepNumber, file.id, selected);
        onFileReplaced?.();
      } catch (err) {
        setError(getErrorMessage(err, "Erreur lors du remplacement du fichier."));
      } finally {
        setReplacing(false);
        if (inputRef.current) inputRef.current.value = "";
      }
    },
    [dossierId, stepNumber, file.id, ext, onFileReplaced],
  );

  const handleDelete = useCallback(async () => {
    if (!window.confirm(`Supprimer le fichier « ${file.filename} » ?`)) return;
    setError(null);
    setDeleting(true);
    try {
      await stepFilesApi.deleteFile(dossierId, stepNumber, file.id);
      onFileDeleted?.();
    } catch (err) {
      setError(getErrorMessage(err, "Erreur lors de la suppression du fichier."));
    } finally {
      setDeleting(false);
    }
  }, [dossierId, stepNumber, file.id, file.filename, onFileDeleted]);

  return (
    <li className={styles.fileRow}>
      <div className={styles.fileInfo}>
        <span className={styles.filename}>{file.filename.replace(/\.tpl$/i, ".md")}</span>
        {file.is_modified && (
          <span className={styles.modifiedBadge}>
            Modifié par l&apos;expert
            {file.updated_at && ` — ${formatDate(file.updated_at)}`}
          </span>
        )}
        <span className={styles.fileMeta}>
          {file.file_type} · {formatFileSize(file.file_size)} · {formatDate(file.created_at)}
        </span>
      </div>

      <div className={styles.actions}>
        <button type="button" className={styles.btn} onClick={handleOpen}>
          Ouvrir
        </button>
        <button type="button" className={styles.btn} onClick={handleDownload}>
          Télécharger
        </button>
        {showReplaceButton && !isLocked && (
          <>
            <button
              type="button"
              className={`${styles.btn} ${styles.btnReplace}`}
              onClick={handleReplaceClick}
              disabled={replacing}
            >
              {replacing ? "Envoi…" : "Remplacer"}
            </button>
            <input
              ref={inputRef}
              type="file"
              className={styles.hiddenInput}
              onChange={handleFileSelected}
              aria-label={`Remplacer ${file.filename.replace(/\.tpl$/i, ".md")}`}
            />
          </>
        )}
        {showDeleteButton && !isLocked && (
          <button
            type="button"
            className={`${styles.btn} ${styles.btnDelete}`}
            onClick={handleDelete}
            disabled={deleting}
          >
            {deleting ? "…" : "Supprimer"}
          </button>
        )}
      </div>

      {error && (
        <div role="alert" className={styles.errorBanner}>
          {error}
        </div>
      )}

      {mdPreview !== null && (
        <pre className={styles.mdPreview}>{mdPreview}</pre>
      )}
    </li>
  );
}

// ---------------------------------------------------------------------------
// FileList component
// ---------------------------------------------------------------------------

export default function FileList({
  dossierId,
  stepNumber,
  files,
  isLocked,
  showReplaceButton,
  showDeleteButton,
  onFileReplaced,
  onFileDeleted,
}: FileListProps) {
  if (files.length === 0) {
    return <p className={styles.empty}>Aucun fichier pour cette étape</p>;
  }

  return (
    <ul className={styles.list}>
      {files.map((f) => (
        <FileRow
          key={f.id}
          file={f}
          dossierId={dossierId}
          stepNumber={stepNumber}
          isLocked={isLocked}
          showReplaceButton={showReplaceButton}
          showDeleteButton={showDeleteButton}
          onFileReplaced={onFileReplaced}
          onFileDeleted={onFileDeleted}
        />
      ))}
    </ul>
  );
}
