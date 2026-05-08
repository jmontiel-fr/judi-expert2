"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import {
  apiListExperts,
  apiGetTicketStats,
  apiGetAdminTicketConfig,
  apiUpdateAdminTicketConfig,
  apiListCorpus,
  apiGetCorpusContenu,
  apiGetCorpusUrls,
  apiAdminUploadDocument,
  apiAdminAddUrl,
  apiAdminChatbotStatus,
  apiAdminChatbotRefresh,
  ApiError,
  type ExpertItem,
  type TicketStats,
  type MonthStat,
  type TicketPriceInfo,
  type CorpusDomain,
  type ContenuItem,
  type UrlItem,
  type ChatbotStatus,
} from "@/lib/api";
import styles from "./admin.module.css";

const DOMAINES = ["Tous", "psychologie", "psychiatrie", "medecine_legale", "batiment", "comptabilite"];

type Tab = "stats" | "tickets" | "experts" | "news" | "corpus" | "chatbot";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR");
}

function formatEuro(n: number): string {
  return n.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/* ------------------------------------------------------------------ */
/*  TicketsConfigTab                                                   */
/* ------------------------------------------------------------------ */

function TicketsConfigTab({ accessToken }: { accessToken: string | null }) {
  const [config, setConfig] = useState<TicketPriceInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [prixHt, setPrixHt] = useState("");
  const [tvaRate, setTvaRate] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    async function load() {
      if (!accessToken) return;
      try {
        const data = await apiGetAdminTicketConfig(accessToken);
        setConfig(data);
        setPrixHt(String(data.prix_ht));
        setTvaRate(String(data.tva_rate));
      } catch {
        setError("Impossible de charger la configuration des tickets.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [accessToken]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!accessToken) return;
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      const data = await apiUpdateAdminTicketConfig(accessToken, {
        prix_ht: parseFloat(prixHt),
        tva_rate: parseFloat(tvaRate),
      });
      setConfig(data);
      setPrixHt(String(data.prix_ht));
      setTvaRate(String(data.tva_rate));
      setEditing(false);
      setSuccess("Configuration mise à jour avec succès.");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Erreur lors de la mise à jour.");
      }
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (config) {
      setPrixHt(String(config.prix_ht));
      setTvaRate(String(config.tva_rate));
    }
    setEditing(false);
    setError("");
    setSuccess("");
  };

  if (loading) return <p>Chargement de la configuration…</p>;

  return (
    <>
      {error && <p className={styles.formError}>{error}</p>}
      {success && <p className={styles.formSuccess}>{success}</p>}

      {config && !editing && (
        <div className={styles.formSection}>
          <h3 className={styles.sectionTitle}>Prix actuel du ticket</h3>
          <p style={{ fontSize: "1.05rem", marginBottom: 16 }}>
            Prix HT : {formatEuro(config.prix_ht)} € | TVA : {Number(config.tva_rate).toFixed(0)}% | Prix TTC : {formatEuro(config.prix_ttc)} €
          </p>
          <button type="button" className={styles.actionBtn} onClick={() => { setEditing(true); setSuccess(""); }}>
            Modifier le prix
          </button>
        </div>
      )}

      {editing && (
        <div className={styles.formSection}>
          <h3 className={styles.formTitle}>Modifier le prix du ticket</h3>
          <form onSubmit={handleSave}>
            <div className={styles.formGroup}>
              <label className={styles.formLabel} htmlFor="prix-ht">Prix HT (€)</label>
              <input
                id="prix-ht"
                type="number"
                step="0.01"
                min="0"
                className={styles.formInput}
                value={prixHt}
                onChange={(e) => setPrixHt(e.target.value)}
                required
              />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel} htmlFor="tva-rate">Taux de TVA (%)</label>
              <input
                id="tva-rate"
                type="number"
                step="0.01"
                min="0"
                max="100"
                className={styles.formInput}
                value={tvaRate}
                onChange={(e) => setTvaRate(e.target.value)}
                required
              />
            </div>
            {prixHt && tvaRate && (
              <p style={{ fontSize: "0.9rem", color: "var(--color-text-muted)", marginBottom: 12 }}>
                Prix TTC calculé : {formatEuro(parseFloat(prixHt) * (1 + parseFloat(tvaRate) / 100))} €
              </p>
            )}
            <div className={styles.formActions}>
              <button type="submit" className={styles.submitBtn} disabled={saving}>
                {saving ? "Enregistrement…" : "Enregistrer"}
              </button>
              <button type="button" className={styles.cancelBtn} onClick={handleCancel}>
                Annuler
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  ExpertsTab                                                         */
/* ------------------------------------------------------------------ */

function ExpertsTab({ experts }: { experts: ExpertItem[] }) {
  const [search, setSearch] = useState("");

  const filtered = experts.filter((e) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      e.nom.toLowerCase().includes(q) ||
      e.prenom.toLowerCase().includes(q) ||
      e.email.toLowerCase().includes(q)
    );
  });

  return (
    <>
      <div className={styles.searchBar}>
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Rechercher par nom, prénom ou email…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Rechercher un expert"
        />
        <span className={styles.searchCount}>{filtered.length} expert(s)</span>
      </div>

      {filtered.length === 0 ? (
        <p className={styles.emptyState}>Aucun expert trouvé.</p>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Nom</th>
              <th>Prénom</th>
              <th>Email</th>
              <th>Domaine</th>
              <th>Date d&apos;inscription</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((e) => (
              <tr key={e.id}>
                <td>{e.nom}</td>
                <td>{e.prenom}</td>
                <td>{e.email}</td>
                <td>{e.domaine}</td>
                <td>{formatDate(e.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  StatsTab                                                           */
/* ------------------------------------------------------------------ */

function StatsTab({ accessToken }: { accessToken: string | null }) {
  const [domaine, setDomaine] = useState("Tous");
  const [stats, setStats] = useState<TicketStats | null>(null);
  const [loading, setLoading] = useState(true);

  const loadStats = useCallback(async () => {
    if (!accessToken) return;
    setLoading(true);
    try {
      const data = await apiGetTicketStats(accessToken, domaine);
      setStats(data);
    } catch {
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, [accessToken, domaine]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  if (loading) return <p className={styles.loading}>Chargement des statistiques…</p>;
  if (!stats) return <p className={styles.emptyState}>Impossible de charger les statistiques.</p>;

  return (
    <>
      <div className={styles.filterBar}>
        <label className={styles.filterLabel} htmlFor="stats-domaine">Domaine :</label>
        <select
          id="stats-domaine"
          className={styles.filterSelect}
          value={domaine}
          onChange={(e) => setDomaine(e.target.value)}
        >
          {DOMAINES.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </div>

      <div className={styles.statsSection}>
        <h3 className={styles.sectionTitle}>Aujourd&apos;hui</h3>
        <table className={styles.table}>
          <thead>
            <tr><th>Tickets vendus</th><th>Montant</th></tr>
          </thead>
          <tbody>
            <tr><td>{stats.today_count}</td><td>{formatEuro(stats.today_amount)} €</td></tr>
          </tbody>
        </table>
      </div>

      <div className={styles.statsSection}>
        <h3 className={styles.sectionTitle}>Mois en cours</h3>
        <table className={styles.table}>
          <thead>
            <tr><th>Tickets vendus</th><th>Montant</th></tr>
          </thead>
          <tbody>
            <tr><td>{stats.month_count}</td><td>{formatEuro(stats.month_amount)} €</td></tr>
          </tbody>
        </table>
      </div>

      {stats.past_months.length > 0 && (
        <div className={styles.statsSection}>
          <h3 className={styles.sectionTitle}>Mois précédents</h3>
          <table className={styles.table}>
            <thead>
              <tr><th>Mois</th><th>Tickets</th><th>Montant</th></tr>
            </thead>
            <tbody>
              {stats.past_months.map((m: MonthStat) => (
                <tr key={m.month}>
                  <td>{m.month}</td>
                  <td>{m.count}</td>
                  <td>{formatEuro(m.amount)} €</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  CorpusTab                                                          */
/* ------------------------------------------------------------------ */

function CorpusTab({ accessToken }: { accessToken: string | null }) {
  const [domains, setDomains] = useState<CorpusDomain[]>([]);
  const [selected, setSelected] = useState<CorpusDomain | null>(null);
  const [contenu, setContenu] = useState<ContenuItem[]>([]);
  const [urls, setUrls] = useState<UrlItem[]>([]);
  const [loadingContent, setLoadingContent] = useState(false);

  // Upload PDF state
  const [showUpload, setShowUpload] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploadSuccess, setUploadSuccess] = useState("");

  // Bulk upload state
  const [showBulkUpload, setShowBulkUpload] = useState(false);
  const [bulkFiles, setBulkFiles] = useState<FileList | null>(null);
  const [bulkUploading, setBulkUploading] = useState(false);
  const [bulkProgress, setBulkProgress] = useState("");

  // Add URL state
  const [showAddUrl, setShowAddUrl] = useState(false);
  const [urlType, setUrlType] = useState<"pdf_externe" | "site_web">("pdf_externe");
  const [urlNom, setUrlNom] = useState("");
  const [urlUrl, setUrlUrl] = useState("");
  const [urlDesc, setUrlDesc] = useState("");
  const [addingUrl, setAddingUrl] = useState(false);
  const [urlError, setUrlError] = useState("");
  const [urlSuccess, setUrlSuccess] = useState("");

  // Crawl state
  const [crawling, setCrawling] = useState(false);
  const [crawlResult, setCrawlResult] = useState<{ message: string; errors: string[] } | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await apiListCorpus();
        setDomains(data);
      } catch {
        /* ignore */
      }
    }
    load();
  }, []);

  const selectDomain = useCallback(async (domain: CorpusDomain) => {
    setSelected(domain);
    setLoadingContent(true);
    setShowUpload(false);
    setShowAddUrl(false);
    setUploadError("");
    setUploadSuccess("");
    setUrlError("");
    setUrlSuccess("");
    try {
      const [c, u] = await Promise.all([
        apiGetCorpusContenu(domain.nom),
        apiGetCorpusUrls(domain.nom),
      ]);
      setContenu(c);
      setUrls(u);
    } catch {
      setContenu([]);
      setUrls([]);
    } finally {
      setLoadingContent(false);
    }
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!accessToken || !selected || !uploadFile) return;
    setUploadError("");
    setUploadSuccess("");
    setUploading(true);
    try {
      await apiAdminUploadDocument(accessToken, selected.nom, uploadFile);
      setUploadSuccess("Document uploadé avec succès.");
      setUploadFile(null);
      setShowUpload(false);
      // Refresh content
      const c = await apiGetCorpusContenu(selected.nom);
      setContenu(c);
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Erreur lors de l'upload.");
    } finally {
      setUploading(false);
    }
  };

  const handleAddUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!accessToken || !selected) return;
    setUrlError("");
    setUrlSuccess("");
    setAddingUrl(true);
    try {
      await apiAdminAddUrl(accessToken, selected.nom, {
        nom: urlNom,
        url: urlUrl,
        description: urlDesc,
        type: urlType,
      });
      setUrlSuccess("URL ajoutée avec succès.");
      setUrlNom("");
      setUrlUrl("");
      setUrlDesc("");
      setShowAddUrl(false);
      // Refresh URLs
      const u = await apiGetCorpusUrls(selected.nom);
      setUrls(u);
    } catch (err) {
      setUrlError(err instanceof ApiError ? err.message : "Erreur lors de l'ajout.");
    } finally {
      setAddingUrl(false);
    }
  };

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

  const handleCrawlUrls = async () => {
    if (!selected) return;
    setCrawling(true);
    setCrawlResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/corpus/${selected.nom}/urls/crawl`, { method: "POST" });
      const data = await res.json();
      setCrawlResult({ message: data.message || "Terminé", errors: data.errors || [] });
    } catch {
      setCrawlResult({ message: "Erreur réseau", errors: [] });
    } finally {
      setCrawling(false);
    }
  };

  const handleBulkUpload = async () => {
    if (!accessToken || !selected || !bulkFiles || bulkFiles.length === 0) return;
    setBulkUploading(true);
    setUploadError("");
    setUploadSuccess("");
    let uploaded = 0;
    const errors: string[] = [];

    for (let i = 0; i < bulkFiles.length; i++) {
      const file = bulkFiles[i];
      setBulkProgress(`Upload ${i + 1}/${bulkFiles.length} : ${file.name}…`);
      try {
        await apiAdminUploadDocument(accessToken, selected.nom, file);
        uploaded++;
      } catch (err) {
        errors.push(`${file.name}: ${err instanceof ApiError ? err.message : "erreur"}`);
      }
    }

    setBulkProgress("");
    setBulkUploading(false);
    setShowBulkUpload(false);
    setBulkFiles(null);

    if (errors.length > 0) {
      setUploadError(`${uploaded} uploadé(s), ${errors.length} erreur(s) : ${errors.join(", ")}`);
    } else {
      setUploadSuccess(`${uploaded} document(s) uploadé(s) avec succès.`);
    }

    // Refresh content
    const c = await apiGetCorpusContenu(selected.nom);
    setContenu(c);
  };

  return (
    <>
      <div className={styles.corpusDomainList}>
        {domains.map((d) => (
          <button
            key={d.nom}
            type="button"
            className={`${styles.corpusDomainBtn} ${selected?.nom === d.nom ? styles.corpusDomainBtnActive : ""}`}
            onClick={() => selectDomain(d)}
          >
            {d.nom}
            <span className={`${styles.badge} ${d.actif ? styles.badgeActive : styles.badgeInactive}`}>
              {d.actif ? "actif" : "inactif"}
            </span>
          </button>
        ))}
      </div>

      {selected && (
        <>
          {loadingContent ? (
            <p className={styles.loading}>Chargement du contenu…</p>
          ) : (
            <>
              <div className={styles.corpusActions}>
                <button type="button" className={styles.actionBtn} onClick={() => { setShowUpload(!showUpload); setShowAddUrl(false); }}>
                  Uploader un PDF
                </button>
                <button type="button" className={styles.actionBtn} onClick={() => { setShowBulkUpload(!showBulkUpload); setShowUpload(false); setShowAddUrl(false); }}>
                  📁 Uploader plusieurs PDFs
                </button>
                <button type="button" className={styles.actionBtn} onClick={() => { setShowAddUrl(!showAddUrl); setShowUpload(false); }}>
                  Ajouter une URL
                </button>
                <button type="button" className={styles.actionBtn} onClick={handleCrawlUrls} disabled={crawling}>
                  {crawling ? "Crawling…" : "🔄 Pré-crawling URLs"}
                </button>
                <p style={{ fontSize: "0.75rem", color: "#6b7280", margin: "4px 0 0", gridColumn: "1 / -1" }}>
                  Le pré-crawling télécharge le contenu textuel de chaque URL de référence pour l&apos;injecter dans le RAG des applications locales.
                </p>
              </div>

              {crawlResult && (
                <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 8, padding: 12, marginBottom: 12, fontSize: "0.85rem" }}>
                  <p style={{ fontWeight: 600, marginBottom: 4 }}>{crawlResult.message}</p>
                  {crawlResult.errors.length > 0 && (
                    <details>
                      <summary style={{ cursor: "pointer", color: "#d97706" }}>{crawlResult.errors.length} erreur(s)</summary>
                      <ul style={{ margin: "4px 0", paddingLeft: 16, fontSize: "0.8rem" }}>
                        {crawlResult.errors.map((e: string, i: number) => <li key={i}>{e}</li>)}
                      </ul>
                    </details>
                  )}
                </div>
              )}

              {uploadError && <p className={styles.formError}>{uploadError}</p>}
              {uploadSuccess && <p className={styles.formSuccess}>{uploadSuccess}</p>}
              {urlError && <p className={styles.formError}>{urlError}</p>}
              {urlSuccess && <p className={styles.formSuccess}>{urlSuccess}</p>}

              {showUpload && (
                <div className={styles.formSection}>
                  <h3 className={styles.formTitle}>Uploader un document PDF</h3>
                  <form onSubmit={handleUpload}>
                    <div className={styles.formGroup}>
                      <label className={styles.formLabel} htmlFor="upload-file">Fichier PDF</label>
                      <input
                        id="upload-file"
                        type="file"
                        accept=".pdf"
                        className={styles.formInput}
                        onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                        required
                      />
                    </div>
                    <div className={styles.formActions}>
                      <button type="submit" className={styles.submitBtn} disabled={uploading || !uploadFile}>
                        {uploading ? "Upload en cours…" : "Uploader"}
                      </button>
                      <button type="button" className={styles.cancelBtn} onClick={() => setShowUpload(false)}>
                        Annuler
                      </button>
                    </div>
                  </form>
                </div>
              )}

              {showBulkUpload && (
                <div className={styles.formSection}>
                  <h3 className={styles.formTitle}>Uploader plusieurs documents PDF</h3>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel} htmlFor="bulk-files">Sélectionner les fichiers PDF</label>
                    <input
                      id="bulk-files"
                      type="file"
                      accept=".pdf"
                      multiple
                      className={styles.formInput}
                      onChange={(e) => setBulkFiles(e.target.files)}
                    />
                  </div>
                  {bulkFiles && bulkFiles.length > 0 && (
                    <p style={{ fontSize: "0.85rem", color: "#374151", marginBottom: 8 }}>
                      {bulkFiles.length} fichier(s) sélectionné(s)
                    </p>
                  )}
                  {bulkProgress && (
                    <p style={{ fontSize: "0.85rem", color: "#2563eb", marginBottom: 8 }}>⏳ {bulkProgress}</p>
                  )}
                  <div className={styles.formActions}>
                    <button
                      type="button"
                      className={styles.submitBtn}
                      onClick={handleBulkUpload}
                      disabled={bulkUploading || !bulkFiles || bulkFiles.length === 0}
                    >
                      {bulkUploading ? "Upload en cours…" : "Uploader tout"}
                    </button>
                    <button type="button" className={styles.cancelBtn} onClick={() => setShowBulkUpload(false)}>
                      Annuler
                    </button>
                  </div>
                </div>
              )}

              {showAddUrl && (
                <div className={styles.formSection}>
                  <h3 className={styles.formTitle}>Ajouter une URL</h3>
                  <form onSubmit={handleAddUrl}>
                    <div className={styles.formGroup}>
                      <label className={styles.formLabel} htmlFor="url-type">Type</label>
                      <select
                        id="url-type"
                        className={styles.filterSelect}
                        value={urlType}
                        onChange={(e) => setUrlType(e.target.value as "pdf_externe" | "site_web")}
                      >
                        <option value="pdf_externe">PDF externe</option>
                        <option value="site_web">Site web</option>
                      </select>
                    </div>
                    <div className={styles.formGroup}>
                      <label className={styles.formLabel} htmlFor="url-nom">Nom</label>
                      <input
                        id="url-nom"
                        type="text"
                        className={styles.formInput}
                        value={urlNom}
                        onChange={(e) => setUrlNom(e.target.value)}
                        required
                      />
                    </div>
                    <div className={styles.formGroup}>
                      <label className={styles.formLabel} htmlFor="url-url">URL</label>
                      <input
                        id="url-url"
                        type="url"
                        className={styles.formInput}
                        value={urlUrl}
                        onChange={(e) => setUrlUrl(e.target.value)}
                        required
                      />
                    </div>
                    <div className={styles.formGroup}>
                      <label className={styles.formLabel} htmlFor="url-desc">Description</label>
                      <input
                        id="url-desc"
                        type="text"
                        className={styles.formInput}
                        value={urlDesc}
                        onChange={(e) => setUrlDesc(e.target.value)}
                      />
                    </div>
                    <div className={styles.formActions}>
                      <button type="submit" className={styles.submitBtn} disabled={addingUrl}>
                        {addingUrl ? "Ajout en cours…" : "Ajouter"}
                      </button>
                      <button type="button" className={styles.cancelBtn} onClick={() => setShowAddUrl(false)}>
                        Annuler
                      </button>
                    </div>
                  </form>
                </div>
              )}

              {contenu.length > 0 && (
                <div className={styles.formSection}>
                  <h3 className={styles.formTitle}>Documents</h3>
                  {contenu.map((c, i) => (
                    <div key={i} className={styles.contentItem}>
                      <div className={styles.contentItemName}>{c.nom}</div>
                      {c.description && <div className={styles.contentItemDesc}>{c.description}</div>}
                      <div className={styles.contentItemType}>{c.type} — {formatDate(c.date_ajout)}</div>
                    </div>
                  ))}
                </div>
              )}

              {urls.length > 0 && (
                <div className={styles.formSection}>
                  <h3 className={styles.formTitle}>URLs</h3>
                  {urls.map((u, i) => (
                    <div key={i} className={styles.contentItem}>
                      <div className={styles.contentItemName}>{u.nom}</div>
                      {u.description && <div className={styles.contentItemDesc}>{u.description}</div>}
                      <a href={u.url} target="_blank" rel="noopener noreferrer" className={styles.urlLink}>{u.url}</a>
                      <div className={styles.contentItemType}>{u.type} — {formatDate(u.date_ajout)}</div>
                    </div>
                  ))}
                </div>
              )}

              {contenu.length === 0 && urls.length === 0 && (
                <p className={styles.emptyState}>Aucun contenu pour ce domaine.</p>
              )}
            </>
          )}
        </>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  ChatbotTab                                                         */
/* ------------------------------------------------------------------ */

function ChatbotTab({ accessToken }: { accessToken: string | null }) {
  const [status, setStatus] = useState<ChatbotStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const loadStatus = useCallback(async () => {
    if (!accessToken) return;
    try {
      const data = await apiAdminChatbotStatus(accessToken);
      setStatus(data);
    } catch {
      setError("Impossible de charger le statut du chatbot.");
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => { loadStatus(); }, [loadStatus]);

  const handleRefresh = async () => {
    if (!accessToken) return;
    setRefreshing(true);
    setMessage("");
    setError("");
    try {
      const result = await apiAdminChatbotRefresh(accessToken);
      setMessage(`${result.message} (${result.total_chunks} chunks)`);
      await loadStatus();
    } catch {
      setError("Erreur lors du rafraîchissement du chatbot.");
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) return <p>Chargement…</p>;

  return (
    <>
      <h2 className={styles.sectionTitle}>Chatbot RAG</h2>
      <p style={{ marginBottom: 16, color: "var(--color-text-muted)" }}>
        Le chatbot utilise un index RAG basé sur les documents du site (FAQ, CGU, mentions légales, méthodologie, confidentialité).
        Rafraîchissez l&apos;index après toute modification de ces documents.
      </p>

      {error && <p style={{ color: "var(--color-error, #dc2626)", marginBottom: 12 }}>{error}</p>}
      {message && <p style={{ color: "var(--color-success, #16a34a)", marginBottom: 12 }}>{message}</p>}

      <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 12, padding: 24, marginBottom: 16 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
          <div>
            <p style={{ fontSize: "0.85rem", color: "var(--color-text-muted)", marginBottom: 4 }}>Dernier rafraîchissement</p>
            <p style={{ fontWeight: 600 }}>
              {status?.last_refresh
                ? new Date(status.last_refresh).toLocaleString("fr-FR")
                : "Jamais"}
            </p>
          </div>
          <div>
            <p style={{ fontSize: "0.85rem", color: "var(--color-text-muted)", marginBottom: 4 }}>Chunks indexés</p>
            <p style={{ fontWeight: 600 }}>{status?.points_count ?? 0}</p>
          </div>
        </div>

        <div style={{ marginBottom: 20 }}>
          <p style={{ fontSize: "0.85rem", color: "var(--color-text-muted)", marginBottom: 8 }}>Documents disponibles</p>
          <ul style={{ listStyle: "none", display: "flex", gap: 8, flexWrap: "wrap" }}>
            {status?.available_docs?.map((doc) => (
              <li key={doc} style={{ background: "#ebf8ff", padding: "4px 10px", borderRadius: 6, fontSize: "0.82rem" }}>
                {doc}
              </li>
            ))}
            {(!status?.available_docs || status.available_docs.length === 0) && (
              <li style={{ color: "var(--color-text-muted)", fontSize: "0.85rem" }}>Aucun document trouvé</li>
            )}
          </ul>
        </div>

        <button
          type="button"
          onClick={handleRefresh}
          disabled={refreshing}
          style={{
            padding: "10px 24px",
            background: "var(--color-primary)",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            fontWeight: 600,
            cursor: refreshing ? "not-allowed" : "pointer",
            opacity: refreshing ? 0.6 : 1,
          }}
        >
          {refreshing ? "Rafraîchissement en cours…" : "🔄 Rafraîchir l'index"}
        </button>
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  AdminPage (default export)                                         */
/* ------------------------------------------------------------------ */

export default function AdminPage() {
  const router = useRouter();
  const { user, isAdmin, accessToken, loading } = useAuth();
  const [tab, setTab] = useState<Tab>("stats");
  const [experts, setExperts] = useState<ExpertItem[]>([]);
  const [loadingData, setLoadingData] = useState(true);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/connexion");
      return;
    }
    if (!isAdmin) {
      router.replace("/");
      return;
    }
  }, [user, isAdmin, loading, router]);

  useEffect(() => {
    async function fetchData() {
      if (!accessToken || !isAdmin) return;
      try {
        const exp = await apiListExperts(accessToken);
        setExperts(exp);
      } catch {
        /* ignore */
      } finally {
        setLoadingData(false);
      }
    }
    fetchData();
  }, [accessToken, isAdmin]);

  if (loading || (!user && !loading)) {
    return <div className={styles.container}><p className={styles.loading}>Chargement…</p></div>;
  }

  if (!isAdmin) return null;

  const tabs: { key: Tab; label: string }[] = [
    { key: "stats", label: "Statistiques" },
    { key: "tickets", label: "Tickets" },
    { key: "experts", label: "Experts" },
    { key: "news", label: "News" },
    { key: "corpus", label: "Corpus" },
    { key: "chatbot", label: "Chatbot" },
  ];

  const handleTabClick = (t: Tab) => {
    if (t === "news") {
      router.push("/admin/news");
      return;
    }
    setTab(t);
  };

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Administration</h1>
      <p className={styles.subtitle}>Gestion du Site Central</p>

      <nav className={styles.tabNav}>
        {tabs.map((t) => (
          <button
            key={t.key}
            type="button"
            className={`${styles.tabBtn} ${tab === t.key && t.key !== "news" ? styles.tabBtnActive : ""}`}
            onClick={() => handleTabClick(t.key)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {loadingData && tab !== "tickets" ? (
        <p className={styles.loading}>Chargement des données…</p>
      ) : (
        <>
          {tab === "stats" && <StatsTab accessToken={accessToken} />}
          {tab === "tickets" && <TicketsConfigTab accessToken={accessToken} />}
          {tab === "experts" && <ExpertsTab experts={experts} />}
          {tab === "corpus" && <CorpusTab accessToken={accessToken} />}
          {tab === "chatbot" && <ChatbotTab accessToken={accessToken} />}
        </>
      )}
    </div>
  );
}
