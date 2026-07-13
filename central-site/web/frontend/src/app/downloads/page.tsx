"use client";

import { useState, useEffect } from "react";
import { apiGetDownloadInfo, type DownloadInfo } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import styles from "./downloads.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function DownloadsPage() {
  const { accessToken, loading: authLoading } = useAuth();
  const [downloadInfo, setDownloadInfo] = useState<DownloadInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (authLoading) return; // Wait for auth context to initialize

    async function load() {
      if (!accessToken) {
        setError("Veuillez vous connecter pour accéder aux téléchargements.");
        setLoading(false);
        return;
      }
      try {
        const info = await apiGetDownloadInfo(accessToken);
        setDownloadInfo(info);
      } catch {
        setError("Impossible de charger les informations de téléchargement.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [accessToken, authLoading]);

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Téléchargements</h1>
      <p className={styles.subtitle}>
        Téléchargez le Site Client et la documentation associée.
      </p>

      {loading && <p>Chargement…</p>}
      {error && <p style={{ color: "var(--color-error, #dc2626)" }}>{error}</p>}

      <div className={styles.card}>
        <div className={styles.cardIcon}>💻</div>
        <h2 className={styles.cardTitle}>Site Client Judi-expert</h2>
        {downloadInfo?.version && (
          <p style={{ fontSize: "0.85rem", fontWeight: 500, color: "var(--color-primary)", marginBottom: 8 }}>
            Version : {downloadInfo.version}
          </p>
        )}
        <p className={styles.cardDesc}>
          {downloadInfo
            ? downloadInfo.description
            : "Package d'installation du Site Client. Contient l'ensemble des conteneurs Docker nécessaires."}
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
              : downloadInfo?.download_url ?? "#"
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
        🔒 Le Site Client fonctionne entièrement sur votre PC.
        Aucune donnée d&apos;expertise ne transite par nos serveurs.
      </div>
    </div>
  );
}
