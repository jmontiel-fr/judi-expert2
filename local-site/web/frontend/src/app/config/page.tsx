"use client";

import { useState, useEffect, useCallback, ChangeEvent } from "react";
import styles from "./config.module.css";
import {
  configApi,
  getErrorMessage,
  type RAGVersion,
  type DocumentItem,
} from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Main component                                                      */
/* ------------------------------------------------------------------ */

export default function ConfigPage() {
  /* --- Domain state --- */
  const [domaine, setDomaine] = useState<string>("");

  /* --- RAG versions state --- */
  const [ragVersions, setRagVersions] = useState<RAGVersion[]>([]);
  const [installedVersion, setInstalledVersion] = useState<string | null>(null);
  const [ragLoading, setRagLoading] = useState(true);
  const [ragError, setRagError] = useState("");
  const [installingVersion, setInstallingVersion] = useState<string | null>(null);
  const [ragSuccess, setRagSuccess] = useState("");

  /* --- TPE state --- */
  const [tpeFile, setTpeFile] = useState<File | null>(null);
  const [tpeUploading, setTpeUploading] = useState(false);
  const [tpeError, setTpeError] = useState("");
  const [tpeSuccess, setTpeSuccess] = useState("");
  const [tpeDefaultLoading, setTpeDefaultLoading] = useState(false);

  /* --- Template state --- */
  const [templateFile, setTemplateFile] = useState<File | null>(null);
  const [templateUploading, setTemplateUploading] = useState(false);
  const [templateError, setTemplateError] = useState("");
  const [templateSuccess, setTemplateSuccess] = useState("");
  const [templateDefaultLoading, setTemplateDefaultLoading] = useState(false);

  /* --- Documents state --- */
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [docsError, setDocsError] = useState("");

  /* ---------------------------------------------------------------- */
  /* Data fetching                                                     */
  /* ---------------------------------------------------------------- */

  const fetchDomain = useCallback(async () => {
    try {
      const data = await configApi.getDomain();
      setDomaine(data.domaine ?? "");
      if ((data as { rag_version?: string }).rag_version) {
        setInstalledVersion((data as { rag_version?: string }).rag_version!);
      }
    } catch {
      /* domain may not be set yet */
    }
  }, []);

  const fetchRagVersions = useCallback(async () => {
    setRagLoading(true);
    setRagError("");
    try {
      const data = await configApi.getRagVersions();
      setRagVersions(data.versions ?? []);
    } catch {
      setRagError("Impossible de récupérer les versions RAG.");
    } finally {
      setRagLoading(false);
    }
  }, []);

  const fetchDocuments = useCallback(async () => {
    setDocsLoading(true);
    setDocsError("");
    try {
      const data = await configApi.getDocuments();
      setDocuments(data.documents ?? []);
    } catch (err: unknown) {
      setDocsError(getErrorMessage(err, "Impossible de récupérer la liste des documents."));
    } finally {
      setDocsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDomain();
    fetchRagVersions();
    fetchDocuments();
  }, [fetchDomain, fetchRagVersions, fetchDocuments]);

  /* ---------------------------------------------------------------- */
  /* Handlers                                                          */
  /* ---------------------------------------------------------------- */

  async function handleInstallRag(version: string) {
    setInstallingVersion(version);
    setRagError("");
    setRagSuccess("");
    try {
      const data = await configApi.installRag(version);
      setInstalledVersion(version);
      setRagSuccess(data.message ?? `Module RAG ${version} installé.`);
      fetchDocuments();
    } catch (err: unknown) {
      setRagError(getErrorMessage(err, "Erreur lors de l'installation du module RAG."));
    } finally {
      setInstallingVersion(null);
    }
  }

  async function handleUploadTpe() {
    if (!tpeFile) return;
    setTpeUploading(true);
    setTpeError("");
    setTpeSuccess("");
    try {
      const data = await configApi.uploadTpe(tpeFile);
      setTpeSuccess(data.message ?? "TPE uploadé avec succès.");
      setTpeFile(null);
      fetchDocuments();
    } catch (err: unknown) {
      setTpeError(getErrorMessage(err, "Erreur lors de l'upload du TPE."));
    } finally {
      setTpeUploading(false);
    }
  }

  async function handleUploadTemplate() {
    if (!templateFile) return;
    setTemplateUploading(true);
    setTemplateError("");
    setTemplateSuccess("");
    try {
      const data = await configApi.uploadTemplate(templateFile);
      setTemplateSuccess(data.message ?? "Template uploadé avec succès.");
      setTemplateFile(null);
      fetchDocuments();
    } catch (err: unknown) {
      setTemplateError(getErrorMessage(err, "Erreur lors de l'upload du Template."));
    } finally {
      setTemplateUploading(false);
    }
  }

  async function handleUseDefaultTpe() {
    setTpeDefaultLoading(true);
    setTpeError("");
    setTpeSuccess("");
    try {
      const response = await fetch("/defaults/TPE_psychologie.tpl");
      const blob = await response.blob();
      const file = new File([blob], "TPE_psychologie.tpl", { type: "text/plain" });
      const data = await configApi.uploadTpe(file);
      setTpeSuccess(data.message ?? "TPE par défaut installé.");
      fetchDocuments();
    } catch (err: unknown) {
      setTpeError(getErrorMessage(err, "Erreur lors de l'installation du TPE par défaut."));
    } finally {
      setTpeDefaultLoading(false);
    }
  }

  async function handleUseDefaultTemplate() {
    setTemplateDefaultLoading(true);
    setTemplateError("");
    setTemplateSuccess("");
    try {
      const response = await fetch("/defaults/template_rapport_psychologie.docx");
      const blob = await response.blob();
      const file = new File([blob], "template_rapport_psychologie.docx", {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      });
      const data = await configApi.uploadTemplate(file);
      setTemplateSuccess(data.message ?? "Template par défaut installé.");
      fetchDocuments();
    } catch (err: unknown) {
      setTemplateError(getErrorMessage(err, "Erreur lors de l'installation du Template par défaut."));
    } finally {
      setTemplateDefaultLoading(false);
    }
  }

  const isPsychologie = domaine === "psychologie";

  /* ---------------------------------------------------------------- */
  /* Render                                                            */
  /* ---------------------------------------------------------------- */

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Configuration</h1>
      <p className={styles.subtitle}>
        Gérez le module RAG, les fichiers de configuration et consultez les documents indexés.
      </p>

      {/* ---- Section 1: Module RAG ---- */}
      <section className={styles.section} aria-labelledby="rag-title">
        <h2 className={styles.sectionTitle} id="rag-title">
          <span className={styles.sectionIcon} aria-hidden="true">🧠</span>
          Module RAG
        </h2>

        {ragLoading ? (
          <div className={styles.loading}>
            <span className={styles.spinner} aria-hidden="true" />
            Chargement des versions…
          </div>
        ) : ragError && ragVersions.length === 0 ? (
          <p className={styles.error} role="alert">{ragError}</p>
        ) : ragVersions.length === 0 ? (
          <p className={styles.emptyState}>Aucune version RAG disponible.</p>
        ) : (
          <>
            <div className={styles.versionList}>
              {ragVersions.map((v) => {
                const isCurrent = installedVersion === v.version;
                return (
                  <div
                    key={v.version}
                    className={`${styles.versionCard} ${isCurrent ? styles.installed : ""}`}
                  >
                    <div className={styles.versionInfo}>
                      <div className={styles.versionNumber}>
                        v{v.version}
                        {isCurrent && (
                          <span className={styles.installedBadge}>Installée</span>
                        )}
                      </div>
                      <div className={styles.versionDesc}>{v.description}</div>
                    </div>
                    <button
                      className={`${styles.button} ${styles.buttonSmall}`}
                      onClick={() => handleInstallRag(v.version)}
                      disabled={installingVersion !== null}
                    >
                      {installingVersion === v.version
                        ? "Installation…"
                        : isCurrent
                          ? "Réinstaller"
                          : "Installer"}
                    </button>
                  </div>
                );
              })}
            </div>
            {ragError && <p className={styles.error} role="alert">{ragError}</p>}
            {ragSuccess && <p className={styles.success} role="status">{ragSuccess}</p>}
          </>
        )}
      </section>

      {/* ---- Section 2: TPE ---- */}
      <section className={styles.section} aria-labelledby="tpe-title">
        <h2 className={styles.sectionTitle} id="tpe-title">
          <span className={styles.sectionIcon} aria-hidden="true">📋</span>
          TPE (Trame d&apos;entretien)
        </h2>

        {isPsychologie && (
          <div className={styles.defaultSuggestion}>
            <span className={styles.suggestionIcon} aria-hidden="true">💡</span>
            <div>
              <strong>Fichier exemple disponible</strong>
              <p>
                Un TPE par défaut pour le domaine psychologie est disponible
                (TPE_psychologie.md).
              </p>
              <div className={styles.defaultActions}>
                <button
                  className={`${styles.button} ${styles.buttonSmall}`}
                  onClick={handleUseDefaultTpe}
                  disabled={tpeDefaultLoading || tpeUploading}
                >
                  {tpeDefaultLoading ? "Installation…" : "Utiliser le TPE par défaut"}
                </button>
              </div>
            </div>
          </div>
        )}

        <div className={styles.uploadArea}>
          <div className={styles.fileInputRow}>
            <input
              type="file"
              className={styles.fileInput}
              accept=".tpl,.txt,.md"
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setTpeFile(e.target.files?.[0] ?? null)
              }
              aria-label="Sélectionner un fichier TPE"
            />
            <button
              className={styles.button}
              onClick={handleUploadTpe}
              disabled={!tpeFile || tpeUploading}
            >
              {tpeUploading ? "Upload…" : "Uploader le TPE"}
            </button>
          </div>
          {tpeError && <p className={styles.error} role="alert">{tpeError}</p>}
          {tpeSuccess && <p className={styles.success} role="status">{tpeSuccess}</p>}
        </div>
      </section>

      {/* ---- Section 3: Template Rapport ---- */}
      <section className={styles.section} aria-labelledby="template-title">
        <h2 className={styles.sectionTitle} id="template-title">
          <span className={styles.sectionIcon} aria-hidden="true">📄</span>
          Template Rapport
        </h2>

        {isPsychologie && (
          <div className={styles.defaultSuggestion}>
            <span className={styles.suggestionIcon} aria-hidden="true">💡</span>
            <div>
              <strong>Fichier exemple disponible</strong>
              <p>
                Un template de rapport par défaut pour le domaine psychologie est
                disponible (template_rapport_psychologie.docx).
              </p>
              <div className={styles.defaultActions}>
                <button
                  className={`${styles.button} ${styles.buttonSmall}`}
                  onClick={handleUseDefaultTemplate}
                  disabled={templateDefaultLoading || templateUploading}
                >
                  {templateDefaultLoading
                    ? "Installation…"
                    : "Utiliser le template par défaut"}
                </button>
              </div>
            </div>
          </div>
        )}

        <div className={styles.uploadArea}>
          <div className={styles.fileInputRow}>
            <input
              type="file"
              className={styles.fileInput}
              accept=".docx"
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setTemplateFile(e.target.files?.[0] ?? null)
              }
              aria-label="Sélectionner un fichier Template Rapport (.docx)"
            />
            <button
              className={styles.button}
              onClick={handleUploadTemplate}
              disabled={!templateFile || templateUploading}
            >
              {templateUploading ? "Upload…" : "Uploader le Template"}
            </button>
          </div>
          {templateError && <p className={styles.error} role="alert">{templateError}</p>}
          {templateSuccess && (
            <p className={styles.success} role="status">{templateSuccess}</p>
          )}
        </div>
      </section>

      {/* ---- Section 4: Documents RAG ---- */}
      <section className={styles.section} aria-labelledby="docs-title">
        <h2 className={styles.sectionTitle} id="docs-title">
          <span className={styles.sectionIcon} aria-hidden="true">📚</span>
          Documents RAG
        </h2>

        {docsLoading ? (
          <div className={styles.loading}>
            <span className={styles.spinner} aria-hidden="true" />
            Chargement des documents…
          </div>
        ) : docsError ? (
          <p className={styles.error} role="alert">{docsError}</p>
        ) : documents.length === 0 ? (
          <p className={styles.emptyState}>
            Aucun document indexé dans la base RAG.
          </p>
        ) : (
          <div className={styles.documentList}>
            {documents.map((doc) => (
              <div key={doc.doc_id} className={styles.documentItem}>
                <span className={styles.documentName}>{doc.filename.replace(/\.tpl$/i, ".md")}</span>
                <div className={styles.documentMeta}>
                  <span className={styles.badge}>{doc.doc_type}</span>
                  <span>{doc.chunk_count} chunks</span>
                  <span className={styles.badge}>{doc.collection}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
