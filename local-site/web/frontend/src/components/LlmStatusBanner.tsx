"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import styles from "./LlmStatusBanner.module.css";

interface LlmUpdateStatus {
  status: "idle" | "downloading" | "ready" | "error";
  progress: number;
  current_model?: string | null;
  error_message?: string | null;
}

export default function LlmStatusBanner() {
  const [llmStatus, setLlmStatus] = useState<LlmUpdateStatus | null>(null);

  useEffect(() => {
    fetchLlmStatus();
  }, []);

  async function fetchLlmStatus() {
    try {
      const { data } = await axios.get<LlmUpdateStatus>("/api/llm/update-status");
      if (data.status === "downloading" || data.status === "ready") {
        setLlmStatus(data);
      }
    } catch {
      // Ignore errors — don't show banner
    }
  }

  if (!llmStatus) return null;

  if (llmStatus.status === "downloading") {
    return (
      <div className={styles.banner} role="status" aria-live="polite">
        <span className={styles.icon} aria-hidden="true">⬇️</span>
        <span className={styles.text}>
          Une nouvelle version du modèle IA est en cours de téléchargement
        </span>
        {llmStatus.progress > 0 && (
          <span className={styles.progress}>({llmStatus.progress}%)</span>
        )}
      </div>
    );
  }

  if (llmStatus.status === "ready") {
    return (
      <div className={`${styles.banner} ${styles.bannerReady}`} role="status" aria-live="polite">
        <span className={styles.icon} aria-hidden="true">✅</span>
        <span className={styles.text}>
          Nouveau modèle prêt — sera activé au prochain redémarrage
        </span>
      </div>
    );
  }

  return null;
}
