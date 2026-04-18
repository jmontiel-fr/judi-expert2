"use client";

import { useState, useEffect, useCallback } from "react";
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
            <div className={styles.contentGrid}>
              {/* Documents column */}
              <div className={styles.contentCol}>
                <p className={styles.colTitle}>📄 Documents</p>
                {documents.length === 0 ? (
                  <p className={styles.emptyList}>Aucun document</p>
                ) : (
                  documents.map((doc) => (
                    <div key={doc.nom} className={styles.card}>
                      <p className={styles.cardName}>{displayName(doc.nom)}</p>
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

              {/* URLs column */}
              <div className={styles.contentCol}>
                <p className={styles.colTitle}>🔗 URLs de référence</p>
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
            </div>
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
