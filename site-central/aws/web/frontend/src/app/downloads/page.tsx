"use client";

import { useState, useEffect } from "react";
import { apiGetDownloadInfo, type DownloadInfo } from "@/lib/api";
import styles from "./downloads.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function DownloadsPage() {
  const [downloadInfo, setDownloadInfo] = useState<DownloadInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const info = await apiGetDownloadInfo();
        setDownloadInfo(info);
      } catch {
        setError("Impossible de charger les informations de téléchargement.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Téléchargements</h1>
      <p className={styles.subtitle}>
        Téléchargez l&apos;application locale et la documentation associée.
      </p>

      {loading && <p>Chargement…</p>}
      {error && <p style={{ color: "var(--color-error, #dc2626)" }}>{error}</p>}

      <div className={styles.card}>
        <div className={styles.cardIcon}>💻</div>
        <h2 className={styles.cardTitle}>Application Locale Judi-expert</h2>
        <p className={styles.cardDesc}>
          {downloadInfo
            ? downloadInfo.description
            : "Package d'installation de l'Application Locale. Contient l'ensemble des conteneurs Docker nécessaires."}
        </p>
        {downloadInfo?.file_size && (
          <p style={{ fontSize: "0.85rem", color: "var(--color-text-muted)", marginBottom: 12 }}>
            Taille : {downloadInfo.file_size}
          </p>
        )}
        <a
          href={
            downloadInfo?.download_url?.startsWith("/")
              ? `${API_BASE}${downloadInfo.download_url}`
              : downloadInfo?.download_url ?? `${API_BASE}/api/downloads/app/file`
          }
          className={styles.downloadBtn}
        >
          ⬇ Télécharger l&apos;application
        </a>
      </div>

      <div className={styles.card}>
        <div className={styles.cardIcon}>📄</div>
        <h2 className={styles.cardTitle}>Document de méthodologie</h2>
        <p className={styles.cardDesc}>
          Document présentant la solution Judi-expert, son usage de l&apos;IA
          comme assistant à l&apos;expert, et sa conformité aux exigences réglementaires.
        </p>
        <a href={`${API_BASE}/api/downloads/methodologie`} className={styles.downloadBtn}>
          ⬇ Télécharger la méthodologie (PDF)
        </a>
      </div>

      <div className={styles.notice}>
        🔒 L&apos;application locale fonctionne entièrement sur votre PC.
        Aucune donnée d&apos;expertise ne transite par nos serveurs.
      </div>
    </div>
  );
}
