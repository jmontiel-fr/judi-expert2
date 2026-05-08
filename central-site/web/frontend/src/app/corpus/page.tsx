"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  apiListCorpus,
  apiGetCorpusContenu,
  apiGetCorpusUrls,
  getCorpusFileUrl,
  type CorpusDomain,
  type ContenuItem,
  type UrlItem,
} from "@/lib/api";
import styles from "./corpus.module.css";

/* ------------------------------------------------------------------ */
/* Domain accordion item                                               */
/* ------------------------------------------------------------------ */

function DomainAccordion({
  domain,
  defaultOpen,
}: {
  domain: CorpusDomain;
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [documents, setDocuments] = useState<ContenuItem[]>([]);
  const [urls, setUrls] = useState<UrlItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);

  // Admin action popup
  const [showPopup, setShowPopup] = useState(false);
  const [popupTitle, setPopupTitle] = useState("");
  const [popupLogs, setPopupLogs] = useState<string[]>([]);
  const [popupDone, setPopupDone] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

  /** Remplace .tpl par .md dans les noms affichés. */
  const displayName = (nom: string) => nom.replace(/\.tpl$/i, ".md");

  const loadContent = useCallback(async () => {
    if (loaded || loading) return;
    setLoading(true);
    try {
      const [docs, u] = await Promise.all([
        apiGetCorpusContenu(domain.nom),
        apiGetCorpusUrls(domain.nom),
      ]);
      setDocuments(docs);
      setUrls(u);
      setLoaded(true);
    } catch {
      setLoaded(true);
    } finally {
      setLoading(false);
    }
  }, [domain.nom, loaded, loading]);

  useEffect(() => {
    if (open && domain.actif && !loaded) loadContent();
  }, [open, domain.actif, loaded, loadContent]);

  const toggle = () => setOpen((prev) => !prev);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

  async function handleAdminAction(endpoint: string, title: string) {
    setShowPopup(true);
    setPopupTitle(title);
    setPopupLogs(["Démarrage…"]);
    setPopupDone(false);
    try {
      setPopupLogs((prev) => [...prev, `Appel ${endpoint}…`]);
      const res = await fetch(`${API_BASE}/api/corpus/${domain.nom}/${endpoint}`, { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        setPopupLogs((prev) => [
          ...prev,
          `✔ ${data.message || "Terminé"}`,
          ...(data.errors?.length ? data.errors.map((e: string) => `⚠ ${e}`) : []),
        ]);
      } else {
        setPopupLogs((prev) => [...prev, `✕ Erreur : ${data.detail || "Erreur"}`]);
      }
    } catch {
      setPopupLogs((prev) => [...prev, "✕ Erreur réseau"]);
    } finally {
      setPopupDone(true);
    }
  }

  return (
    <div className={styles.accordion}>
      <button
        type="button"
        className={styles.accordionHeader}
        onClick={toggle}
        aria-expanded={open}
      >
        <span className={`${styles.arrow} ${open ? styles.arrowOpen : ""}`}>
          ▶
        </span>
        <span className={styles.domainName}>{domain.nom}</span>
        <span
          className={`${styles.badge} ${domain.actif ? styles.badgeActive : styles.badgeInactive}`}
        >
          {domain.actif ? "Actif" : "Inactif"}
        </span>
        {domain.versions.map((v) => (
          <span key={v.version} className={styles.versionChip}>
            v{v.version}
          </span>
        ))}
      </button>

      {open && (
        <div className={styles.accordionBody}>
          {!domain.actif ? (
            <p className={styles.inactiveMsg}>
              Corpus en cours de préparation
            </p>
          ) : loading ? (
            <div className={styles.spinner}>
              <span className={styles.spinnerDot} />
              Chargement…
            </div>
          ) : (
            <>
              {/* Admin buttons */}
              <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
                <button className={styles.typeBtn} onClick={() => handleAdminAction("urls/crawl", "Pré-crawling des URLs")}>
                  🔄 Pré-crawling URLs
                </button>
              </div>

              {/* Popup */}
              {showPopup && (
                <div style={{
                  position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
                  display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
                }} onClick={() => popupDone && setShowPopup(false)}>
                  <div style={{
                    background: "white", borderRadius: 12, padding: 24, maxWidth: 520, width: "90%",
                    boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
                  }} onClick={(e) => e.stopPropagation()}>
                    <h3 style={{ margin: "0 0 12px", fontSize: "1.1rem" }}>
                      {!popupDone ? "⏳ " : "✔ "}{popupTitle}
                    </h3>
                    <p style={{ fontSize: "0.85rem", color: "#6b7280", marginBottom: 12 }}>
                      {popupDone ? `Terminé en ${formatTime(elapsed)}` : `En cours… ${formatTime(elapsed)}`}
                    </p>
                    <div style={{
                      background: "#1e293b", color: "#e2e8f0", padding: 12, borderRadius: 8,
                      fontSize: "0.8rem", fontFamily: "monospace", maxHeight: 200, overflowY: "auto", marginBottom: 16,
                    }}>
                      {popupLogs.map((log, i) => <div key={i}>{log}</div>)}
                    </div>
                    {popupDone && (
                      <button className={styles.typeBtn} onClick={() => setShowPopup(false)}>Fermer</button>
                    )}
                  </div>
                </div>
              )}

              <div className={styles.contentGrid}>
              {/* Column 1: Templates + URLs */}
              <div className={styles.contentCol}>
                {/* Templates (TPE, TRE) */}
                {documents.filter((d) => d.type === "template").length > 0 && (
                  <>
                    <p className={styles.colTitle}>📋 Templates (TPE / TRE)</p>
                    {documents
                      .filter((d) => d.type === "template")
                      .map((doc) => (
                        <div key={doc.nom} className={styles.card}>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span className={`${styles.badge} ${styles.badgeActive}`}>Template</span>
                            <p className={styles.cardName} style={{ margin: 0 }}>{displayName(doc.nom)}</p>
                          </div>
                          {doc.description && (
                            <p className={styles.cardDesc}>{doc.description}</p>
                          )}
                          <button
                            type="button"
                            className={styles.typeBtn}
                            onClick={() =>
                              window.open(
                                getCorpusFileUrl(domain.nom, doc.nom),
                                "_blank",
                                "noopener,noreferrer",
                              )
                            }
                          >
                            Télécharger ↓
                          </button>
                        </div>
                      ))}
                  </>
                )}

                {/* URLs de référence */}
                <p className={styles.colTitle} style={{ marginTop: 24 }}>🔗 URLs de référence</p>
                {urls.length === 0 ? (
                  <p className={styles.emptyList}>Aucune URL</p>
                ) : (
                  urls.map((urlItem) => (
                    <div key={urlItem.nom} className={styles.card}>
                      <p className={styles.cardName}>{urlItem.nom}</p>
                      {urlItem.description && (
                        <p className={styles.cardDesc}>{urlItem.description}</p>
                      )}
                      <button
                        type="button"
                        className={styles.typeBtn}
                        onClick={() =>
                          window.open(
                            urlItem.url,
                            "_blank",
                            "noopener,noreferrer",
                          )
                        }
                      >
                        Ouvrir ↗
                      </button>
                    </div>
                  ))
                )}
              </div>

              {/* Column 2: Documents de référence */}
              <div className={styles.contentCol}>
                <p className={styles.colTitle}>📄 Documents de référence</p>
                {documents.filter((d) => d.type !== "template").length === 0 ? (
                  <p className={styles.emptyList}>Aucun document de référence</p>
                ) : (
                  documents
                    .filter((d) => d.type !== "template")
                    .map((doc) => (
                      <div key={doc.nom} className={styles.card}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span className={styles.badge} style={{ backgroundColor: "#6366f1", color: "white" }}>Document</span>
                          <p className={styles.cardName} style={{ margin: 0 }}>{displayName(doc.nom)}</p>
                        </div>
                        {doc.description && (
                          <p className={styles.cardDesc}>{doc.description}</p>
                        )}
                        <button
                          type="button"
                          className={styles.typeBtn}
                          onClick={() =>
                            window.open(
                              getCorpusFileUrl(domain.nom, doc.nom),
                              "_blank",
                              "noopener,noreferrer",
                            )
                          }
                        >
                          Télécharger ↓
                        </button>
                      </div>
                    ))
                )}
              </div>
            </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main page                                                           */
/* ------------------------------------------------------------------ */

export default function CorpusPage() {
  const [corpus, setCorpus] = useState<CorpusDomain[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const data = await apiListCorpus();
        setCorpus(data);
      } catch {
        setError("Impossible de charger les corpus. Veuillez réessayer.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className={styles.container}>
        <h1 className={styles.title}>Corpus par domaine</h1>
        <div className={styles.spinner}>
          <span className={styles.spinnerDot} />
          Chargement…
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <h1 className={styles.title}>Corpus par domaine</h1>
        <p style={{ color: "var(--color-error, #dc2626)" }}>{error}</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Corpus par domaine</h1>
      <p className={styles.subtitle}>
        Consultez les corpus disponibles pour chaque domaine d&apos;expertise.
      </p>
      <div className={styles.accordionList}>
        {corpus.map((domain, i) => (
          <DomainAccordion
            key={domain.nom}
            domain={domain}
            defaultOpen={i === 0}
          />
        ))}
      </div>
    </div>
  );
}
