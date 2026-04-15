"use client";

import { useState, useEffect } from "react";
import { apiListCorpus, type CorpusDomain } from "@/lib/api";
import styles from "./corpus.module.css";

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
        <p>Chargement…</p>
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
        Consultez les corpus disponibles pour chaque domaine d&apos;expertise et leurs versions.
      </p>

      <div className={styles.grid}>
        {corpus.map((domain) => (
          <div key={domain.nom} className={styles.card}>
            <div className={styles.cardHeader}>
              <span className={styles.domainName}>{domain.nom}</span>
              <span className={`${styles.badge} ${domain.actif ? styles.badgeActive : styles.badgeInactive}`}>
                {domain.actif ? "Actif" : "Inactif"}
              </span>
            </div>

            {domain.versions.length > 0 ? (
              <>
                <p className={styles.versionsTitle}>Versions disponibles</p>
                {domain.versions.map((v) => (
                  <div key={v.version} className={styles.versionItem}>
                    <p className={styles.versionTag}>v{v.version}</p>
                    <p className={styles.versionDesc}>{v.description}</p>
                  </div>
                ))}
              </>
            ) : (
              <p className={styles.noVersions}>Aucune version disponible pour le moment.</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
