"use client";

import { useState, useEffect, useCallback, useRef, ChangeEvent } from "react";
import styles from "./config.module.css";
import {
  configApi,
  getErrorMessage,
  type RAGVersion,
  type DocumentItem,
} from "@/lib/api";

/* ------------------------------------------------------------------ */
/* CorpusManager sub-component                                         */
/* ------------------------------------------------------------------ */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function CorpusManager({ domaine, onUpdate }: { domaine: string; onUpdate: () => void }) {
  const [loading, setLoading] = useState(false);
  const [action, setAction] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [corpusDocs, setCorpusDocs] = useState<Array<{ filename: string; type: string; source: string }>>([]);
  const [addFile, setAddFile] = useState<File | null>(null);
  const [newUrl, setNewUrl] = useState("");

  // Données du Site Central
  const [centralDocs, setCentralDocs] = useState<Array<{ nom: string; description: string; type: string }>>([]);
  const [centralUrls, setCentralUrls] = useState<Array<{ nom: string; description: string; url: string }>>([]);

  // Popup state
  const [showPopup, setShowPopup] = useState(false);
  const [popupTitle, setPopupTitle] = useState("");
  const [popupLogs, setPopupLogs] = useState<string[]>([]);
  const [popupDone, setPopupDone] = useState(false);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchCorpusList = useCallback(async () => {
    try {
      const token = localStorage.getItem("token");
      const [listRes, contenuRes, urlsRes] = await Promise.all([
        fetch(`${API_URL}/api/config/corpus/list`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_URL}/api/config/corpus/central-contenu`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_URL}/api/config/corpus/central-urls`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      if (listRes.ok) {
        const data = await listRes.json();
        setCorpusDocs(data.documents ?? []);
      }
      if (contenuRes.ok) {
        const data = await contenuRes.json();
        setCentralDocs(data.documents ?? []);
      }
      if (urlsRes.ok) {
        const data = await urlsRes.json();
        setCentralUrls(data.urls ?? []);
      }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchCorpusList(); }, [fetchCorpusList]);

  // Timer for popup
  useEffect(() => {
    if (showPopup && !popupDone) {
      setElapsed(0);
      intervalRef.current = setInterval(() => setElapsed((p) => p + 1), 1000);
    } else {
      if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [showPopup, popupDone]);

  function formatTime(s: number): string {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m > 0 ? `${m}min ${sec.toString().padStart(2, "0")}s` : `${sec}s`;
  }

  async function handleAction(endpoint: string, actionName: string, title: string) {
    const controller = new AbortController();
    setAbortController(controller);
    setShowPopup(true);
    setPopupTitle(title);
    setPopupLogs(["Démarrage…"]);
    setPopupDone(false);
    setLoading(true);
    setAction(actionName);
    setMessage("");
    setError("");

    try {
      const token = localStorage.getItem("token");

      // Pour initialize et reset, utiliser SSE (streaming)
      if (endpoint === "initialize" || endpoint === "reset") {
        const res = await fetch(`${API_URL}/api/config/corpus/${endpoint}`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        });

        if (!res.ok) {
          const data = await res.json();
          setPopupLogs((prev) => [...prev, `✕ Erreur : ${data.detail || "Erreur inconnue"}`]);
          setError(data.detail || "Erreur");
          setPopupDone(true);
          return;
        }

        // Lire le stream SSE
        const reader = res.body?.getReader();
        const decoder = new TextDecoder();
        if (reader) {
          let buffer = "";
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n\n");
            buffer = lines.pop() || "";
            for (const line of lines) {
              if (line.startsWith("data: ")) {
                try {
                  const data = JSON.parse(line.slice(6));
                  if (data.log) {
                    setPopupLogs((prev) => [...prev, data.log]);
                  }
                  if (data.done) {
                    setMessage(`${data.indexed ?? 0} documents indexés`);
                    fetchCorpusList();
                    onUpdate();
                  }
                } catch { /* ignore parse errors */ }
              }
            }
          }
        }
      } else {
        // Pour rebuild et autres, appel classique
        setPopupLogs((prev) => [...prev, `Appel ${endpoint}…`]);
        const res = await fetch(`${API_URL}/api/config/corpus/${endpoint}`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        });
        const data = await res.json();
        if (res.ok) {
          setPopupLogs((prev) => [
            ...prev,
            `✔ ${data.message || "Opération réussie"}`,
            `Documents indexés : ${data.indexed ?? 0}`,
            ...(data.errors?.length ? data.errors.map((e: string) => `⚠ ${e}`) : []),
          ]);
          setMessage(data.message || "Opération réussie");
          fetchCorpusList();
          onUpdate();
        } else {
          setPopupLogs((prev) => [...prev, `✕ Erreur : ${data.detail || "Erreur inconnue"}`]);
          setError(data.detail || "Erreur");
        }
      }
    } catch (err: unknown) {
      if ((err as Error).name === "AbortError") {
        setPopupLogs((prev) => [...prev, "⏹ Opération interrompue par l'utilisateur"]);
      } else {
        setPopupLogs((prev) => [...prev, "✕ Erreur réseau"]);
        setError("Erreur réseau");
      }
    } finally {
      setPopupDone(true);
      setLoading(false);
      setAction("");
      setAbortController(null);
    }
  }

  function handleStop() {
    if (abortController) {
      abortController.abort();
    }
  }

  async function handleAddDocument() {
    if (!addFile) return;
    setLoading(true);
    setAction("add");
    setMessage("");
    setError("");
    try {
      const token = localStorage.getItem("token");
      const formData = new FormData();
      formData.append("file", addFile);
      const res = await fetch(`${API_URL}/api/config/corpus/add`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setMessage(data.message || "Document ajouté");
        setAddFile(null);
        fetchCorpusList();
        onUpdate();
      } else {
        setError(data.detail || "Erreur");
      }
    } catch {
      setError("Erreur réseau");
    } finally {
      setLoading(false);
      setAction("");
    }
  }

  async function handleRemoveDocument(filename: string) {
    if (!confirm(`Supprimer "${filename}" du corpus ?`)) return;
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_URL}/api/config/corpus/${encodeURIComponent(filename)}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setMessage(`"${filename}" supprimé`);
        fetchCorpusList();
        onUpdate();
      } else {
        const data = await res.json();
        setError(data.detail || "Erreur");
      }
    } catch {
      setError("Erreur réseau");
    }
  }

  async function handleAddUrl() {
    if (!newUrl.trim()) return;
    setLoading(true);
    setMessage("");
    setError("");
    try {
      const token = localStorage.getItem("token");
      // Créer un fichier texte avec l'URL comme contenu et nom
      const urlFilename = newUrl.replace(/https?:\/\//, "").replace(/[^a-zA-Z0-9.-]/g, "_").slice(0, 60) + ".url.txt";
      const blob = new Blob([newUrl], { type: "text/plain" });
      const file = new File([blob], urlFilename, { type: "text/plain" });
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_URL}/api/config/corpus/add`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setMessage(`URL ajoutée : ${newUrl}`);
        setNewUrl("");
        fetchCorpusList();
        onUpdate();
      } else {
        setError(data.detail || "Erreur");
      }
    } catch {
      setError("Erreur réseau");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      {/* Popup modal */}
      {showPopup && (
        <div className={styles.overlay} onClick={() => popupDone && setShowPopup(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ margin: "0 0 12px", fontSize: "1.1rem" }}>
              {!popupDone && <span style={{ marginRight: 8 }}>⏳</span>}
              {popupDone && <span style={{ marginRight: 8 }}>✔</span>}
              {popupTitle}
            </h3>
            <p style={{ fontSize: "0.85rem", color: "#6b7280", marginBottom: 12 }}>
              {popupDone ? `Terminé en ${formatTime(elapsed)}` : `En cours… ${formatTime(elapsed)}`}
            </p>
            <div style={{
              background: "#1e293b", color: "#e2e8f0", padding: 12, borderRadius: 8,
              fontSize: "0.8rem", fontFamily: "monospace", maxHeight: 200, overflowY: "auto",
              marginBottom: 16,
            }}>
              {popupLogs.map((log, i) => (
                <div key={i}>{log}</div>
              ))}
            </div>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              {!popupDone && (
                <button className={styles.button} onClick={handleStop} style={{ backgroundColor: "#dc2626" }}>
                  ⏹ Stop
                </button>
              )}
              {popupDone && (
                <button className={styles.button} onClick={() => setShowPopup(false)}>
                  Fermer
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className={styles.defaultActions} style={{ marginBottom: 16, gap: 8, display: "flex", flexWrap: "wrap" }}>
        <button
          className={styles.button}
          onClick={() => handleAction("initialize", "initialize", "Initialisation du corpus")}
          disabled={loading}
        >
          {action === "initialize" ? "Initialisation…" : "Initialiser le corpus"}
        </button>
        <button
          className={`${styles.button} ${styles.buttonSmall}`}
          onClick={() => handleAction("rebuild", "rebuild", "Reconstruction du RAG")}
          disabled={loading}
        >
          {action === "rebuild" ? "Reconstruction…" : "Rebuilder le RAG"}
        </button>
        <button
          className={`${styles.button} ${styles.buttonSmall}`}
          onClick={() => handleAction("reset", "reset", "Reset to original")}
          disabled={loading}
          style={{ backgroundColor: "#dc2626" }}
        >
          {action === "reset" ? "Réinitialisation…" : "Reset to original"}
        </button>
      </div>

      {message && !showPopup && <p className={styles.success} role="status">{message}</p>}
      {error && !showPopup && <p className={styles.error} role="alert">{error}</p>}

      {/* Corpus en 2 colonnes (miroir du Site Central) */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginTop: 16 }}>
        {/* Colonne 1 : URLs de référence */}
        <div>
          <p style={{ fontWeight: 600, marginBottom: 8 }}>🔗 URLs de référence</p>
          {centralUrls.length === 0 && corpusDocs.filter((d) => d.type === "url").length === 0 ? (
            <p style={{ fontSize: "0.85rem", color: "#6b7280" }}>Aucune URL (Site Central indisponible ?)</p>
          ) : (
            <div className={styles.documentList}>
              {centralUrls.map((urlItem) => (
                <div key={urlItem.nom} className={styles.documentItem}>
                  <span className={styles.documentName}>{urlItem.nom}</span>
                  {urlItem.description && (
                    <p style={{ fontSize: "0.75rem", color: "#6b7280", margin: "2px 0 4px" }}>{urlItem.description}</p>
                  )}
                  <a href={urlItem.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: "0.75rem", color: "#2563eb" }}>
                    {urlItem.url} ↗
                  </a>
                </div>
              ))}
              {/* URLs custom ajoutées par l'expert */}
              {corpusDocs.filter((d) => d.type === "url" && d.source === "custom").map((doc) => (
                <div key={doc.filename} className={styles.documentItem}>
                  <span className={styles.documentName}>{doc.filename}</span>
                  <div className={styles.documentMeta}>
                    <span className={styles.badge}>custom</span>
                    <button
                      onClick={() => handleRemoveDocument(doc.filename)}
                      style={{ background: "none", border: "none", color: "#dc2626", cursor: "pointer", fontSize: "0.8rem" }}
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          {/* Ajouter une URL */}
          <div style={{ marginTop: 12 }}>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                type="text"
                placeholder="https://..."
                value={newUrl}
                onChange={(e) => setNewUrl(e.target.value)}
                style={{ flex: 1, padding: "6px 10px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: "0.85rem" }}
              />
              <button
                className={`${styles.button} ${styles.buttonSmall}`}
                onClick={handleAddUrl}
                disabled={!newUrl.trim() || loading}
                style={{ whiteSpace: "nowrap" }}
              >
                + URL
              </button>
            </div>
          </div>
        </div>

        {/* Colonne 2 : Documents */}
        <div>
          <p style={{ fontWeight: 600, marginBottom: 8 }}>📄 Documents de référence</p>
          {centralDocs.length === 0 && corpusDocs.filter((d) => d.type === "document" || d.type === "custom").length === 0 ? (
            <p style={{ fontSize: "0.85rem", color: "#6b7280" }}>Aucun document</p>
          ) : (
            <div className={styles.documentList}>
              {/* Documents du Site Central */}
              {centralDocs.map((doc) => {
                const isIndexed = corpusDocs.some((d) => d.filename.includes(doc.nom.replace("/", "_")));
                return (
                  <div key={doc.nom} className={styles.documentItem}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <span style={{ fontSize: "0.75rem" }}>{isIndexed ? "✔" : "⚠"}</span>
                      <span className={styles.documentName}>{doc.nom.replace("documents/", "")}</span>
                    </div>
                    {doc.description && (
                      <p style={{ fontSize: "0.75rem", color: "#6b7280", margin: "2px 0 0" }}>{doc.description}</p>
                    )}
                    {!isIndexed && (
                      <span style={{ fontSize: "0.7rem", color: "#d97706" }}>Non téléchargé</span>
                    )}
                  </div>
                );
              })}
              {/* Documents custom ajoutés par l'expert */}
              {corpusDocs.filter((d) => (d.type === "document" || d.type === "custom") && d.source === "custom").map((doc) => (
                <div key={doc.filename} className={styles.documentItem}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: "0.75rem" }}>✔</span>
                    <span className={styles.documentName}>{doc.filename}</span>
                  </div>
                  <div className={styles.documentMeta}>
                    <span className={styles.badge}>custom</span>
                    <button
                      onClick={() => handleRemoveDocument(doc.filename)}
                      style={{ background: "none", border: "none", color: "#dc2626", cursor: "pointer", fontSize: "0.8rem" }}
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          {/* Ajouter un document */}
          <div style={{ marginTop: 12 }}>
            <div className={styles.fileInputRow}>
              <input
                type="file"
                className={styles.fileInput}
                accept=".pdf,.md,.txt,.docx"
                onChange={(e: ChangeEvent<HTMLInputElement>) => setAddFile(e.target.files?.[0] ?? null)}
                aria-label="Ajouter un document au corpus"
              />
              <button
                className={`${styles.button} ${styles.buttonSmall}`}
                onClick={handleAddDocument}
                disabled={!addFile || loading}
              >
                + Doc
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

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
      // Télécharger le TPE par défaut via le backend local (proxy vers Site Central)
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_URL}/api/config/defaults/tpe`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "TPE par défaut non disponible" }));
        throw new Error(err.detail);
      }
      const blob = await response.blob();
      const file = new File([blob], "TPE_psychologie.md", { type: "text/markdown" });
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
      // Télécharger le template par défaut via le backend local (proxy vers Site Central)
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_URL}/api/config/defaults/template`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Template par défaut non disponible" }));
        throw new Error(err.detail);
      }
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

      {/* ---- Section 4: Gestion du Corpus ---- */}
      <section className={styles.section} aria-labelledby="corpus-title">
        <h2 className={styles.sectionTitle} id="corpus-title">
          <span className={styles.sectionIcon} aria-hidden="true">📚</span>
          Corpus RAG
        </h2>

        <CorpusManager domaine={domaine} onUpdate={fetchDocuments} />
      </section>

      {/* ---- Section 5: Documents RAG (indexés) ---- */}
      <section className={styles.section} aria-labelledby="docs-title">
        <h2 className={styles.sectionTitle} id="docs-title">
          <span className={styles.sectionIcon} aria-hidden="true">🔍</span>
          Documents indexés (RAG)
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
