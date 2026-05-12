"use client";

import { useState } from "react";
import styles from "./PerformanceSection.module.css";

/* ------------------------------------------------------------------ */
/* TypeScript interfaces                                               */
/* ------------------------------------------------------------------ */

export interface HardwareInfo {
  cpu_model: string;
  cpu_freq_ghz: number;
  cpu_cores: number;
  ram_total_gb: number;
  gpu_name: string | null;
  gpu_vram_gb: number | null;
}

export interface ProfileInfo {
  name: string;
  display_name: string;
  ram_range: string;
  ctx_max: number;
  model: string;
  rag_chunks: number;
  tokens_per_sec: number;
  step_durations: Record<string, string>;
}

export interface PerformanceProfileResponse {
  active_profile: ProfileInfo;
  is_override: boolean;
  auto_detected_profile: string;
  all_profiles: ProfileInfo[];
  hardware_info: HardwareInfo;
}

export interface ModelDownloadStatus {
  needed: boolean;
  in_progress: boolean;
  progress_percent: number | null;
  error: string | null;
}

/* ------------------------------------------------------------------ */
/* Props                                                               */
/* ------------------------------------------------------------------ */

interface PerformanceSectionProps {
  hardwareInfo: HardwareInfo;
  activeProfile: ProfileInfo;
  isOverride: boolean;
  allProfiles: ProfileInfo[];
  autoDetectedProfile: string;
  downloadStatus: ModelDownloadStatus | null;
  onOverrideChange: (profileName: string | null) => void;
  overrideLoading: boolean;
}

/* ------------------------------------------------------------------ */
/* RAM threshold helper                                                */
/* ------------------------------------------------------------------ */

function getMinRamForProfile(profileName: string): number {
  switch (profileName) {
    case "high": return 32;
    case "medium": return 16;
    case "low": return 8;
    case "minimal": return 0;
    default: return 0;
  }
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function PerformanceSection({
  hardwareInfo,
  activeProfile,
  isOverride,
  allProfiles,
  autoDetectedProfile,
  downloadStatus,
  onOverrideChange,
  overrideLoading,
}: PerformanceSectionProps) {
  const [selectedOverride, setSelectedOverride] = useState<string>(
    isOverride ? activeProfile.name : "__auto__"
  );
  const [strategyOpen, setStrategyOpen] = useState(false);

  const showRamWarning =
    selectedOverride !== "__auto__" &&
    getMinRamForProfile(selectedOverride) > hardwareInfo.ram_total_gb;

  function handleOverrideSelect(value: string) {
    setSelectedOverride(value);
    if (value === "__auto__") {
      onOverrideChange(null);
    } else {
      onOverrideChange(value);
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.cardsGrid}>
        {/* ---- Carte: Matériel détecté ---- */}
        <div className={styles.card}>
          <h3 className={styles.cardTitle}>
            <span className={styles.cardIcon} aria-hidden="true">🖥️</span>
            Matériel détecté
          </h3>
          <div className={styles.infoList}>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Processeur</span>
              <span className={styles.infoValue}>{hardwareInfo.cpu_model}</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Fréquence</span>
              <span className={styles.infoValue}>{hardwareInfo.cpu_freq_ghz.toFixed(1)} GHz</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Cœurs physiques</span>
              <span className={styles.infoValue}>{hardwareInfo.cpu_cores}</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>RAM totale</span>
              <span className={styles.infoValue}>{hardwareInfo.ram_total_gb.toFixed(1)} Go</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>GPU</span>
              {hardwareInfo.gpu_name ? (
                <span className={styles.infoValue}>{hardwareInfo.gpu_name}</span>
              ) : (
                <span className={`${styles.infoValue} ${styles.gpuAbsent}`}>
                  Aucun GPU détecté
                </span>
              )}
            </div>
            {hardwareInfo.gpu_name && hardwareInfo.gpu_vram_gb && (
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>VRAM GPU</span>
                <span className={styles.infoValue}>{hardwareInfo.gpu_vram_gb.toFixed(1)} Go</span>
              </div>
            )}
          </div>
        </div>

        {/* ---- Carte: Profil actif ---- */}
        <div className={styles.card}>
          <h3 className={styles.cardTitle}>
            <span className={styles.cardIcon} aria-hidden="true">⚡</span>
            Profil actif
          </h3>
          <p className={styles.profileName}>
            {activeProfile.display_name}
            <span
              className={`${styles.profileBadge} ${isOverride ? styles.badgeManual : styles.badgeAuto}`}
            >
              {isOverride ? "Manuel" : "Auto"}
            </span>
          </p>
          <div className={styles.infoList}>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Modèle LLM</span>
              <span className={styles.infoValue}>{activeProfile.model}</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>CTX_MAX</span>
              <span className={styles.infoValue}>{activeProfile.ctx_max.toLocaleString("fr-FR")} tokens</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Chunks RAG</span>
              <span className={styles.infoValue}>{activeProfile.rag_chunks}</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Vitesse estimée</span>
              <span className={styles.infoValue}>{activeProfile.tokens_per_sec.toFixed(1)} tokens/s</span>
            </div>
          </div>

          {/* Override selector */}
          <div className={styles.overrideSection}>
            <label className={styles.overrideLabel} htmlFor="profile-override-select">
              Changer le profil :
            </label>
            <select
              id="profile-override-select"
              className={styles.overrideSelect}
              value={selectedOverride}
              onChange={(e) => handleOverrideSelect(e.target.value)}
              disabled={overrideLoading}
              aria-label="Sélectionner un profil de performance"
            >
              <option value="__auto__">Automatique</option>
              {allProfiles.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.display_name} ({p.ram_range})
                </option>
              ))}
            </select>
            {overrideLoading && (
              <span className={styles.overrideSpinner} aria-hidden="true" />
            )}
          </div>

          {/* RAM warning */}
          {showRamWarning && (
            <p className={styles.ramWarning} role="alert">
              ⚠️ Ce profil nécessite plus de RAM que disponible. Risque d&apos;instabilité.
            </p>
          )}
        </div>
      </div>

      {/* ---- Model download progress ---- */}
      {downloadStatus && downloadStatus.in_progress && (
        <div className={styles.downloadProgress} role="status" aria-live="polite">
          <div className={styles.downloadHeader}>
            <span className={styles.downloadIcon} aria-hidden="true">⬇️</span>
            <span>Téléchargement du modèle en cours…</span>
          </div>
          {downloadStatus.progress_percent != null && (
            <div className={styles.progressBarContainer}>
              <div
                className={styles.progressBar}
                style={{ width: `${Math.min(downloadStatus.progress_percent, 100)}%` }}
                role="progressbar"
                aria-valuenow={downloadStatus.progress_percent}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>
          )}
          {downloadStatus.progress_percent != null && (
            <span className={styles.downloadPercent}>
              {downloadStatus.progress_percent.toFixed(0)}%
            </span>
          )}
        </div>
      )}

      {downloadStatus && downloadStatus.error && (
        <p className={styles.downloadError} role="alert">
          ❌ Erreur de téléchargement du modèle : {downloadStatus.error}
        </p>
      )}

      {/* ---- Note explicative collapsable ---- */}
      <details
        className={styles.strategyDetails}
        open={strategyOpen}
        onToggle={(e) => setStrategyOpen((e.target as HTMLDetailsElement).open)}
      >
        <summary className={styles.strategySummary}>
          <span className={styles.strategyIcon} aria-hidden="true">ℹ️</span>
          Comment le profil est-il sélectionné ?
        </summary>
        <div className={styles.strategyContent}>
          <p>
            Le profil de performance est déterminé automatiquement en fonction de la
            <strong> RAM totale</strong> détectée sur votre machine. La RAM est la contrainte
            principale car le modèle LLM doit tenir entièrement en mémoire pendant l&apos;inférence.
          </p>
          <ul>
            <li><strong>≥ 32 Go</strong> → Profil « Haute performance » (modèle 7B, contexte large)</li>
            <li><strong>16 – 32 Go</strong> → Profil « Standard » (modèle 7B, contexte modéré)</li>
            <li><strong>8 – 16 Go</strong> → Profil « Économique » (modèle 3B, contexte réduit)</li>
            <li><strong>&lt; 8 Go</strong> → Profil « Minimal » (modèle 3B, contexte minimal)</li>
          </ul>
          <p>
            La <strong>vitesse estimée</strong> (tokens/s) est calculée à partir du nombre de cœurs
            CPU et de la fréquence, mais ne modifie pas le choix du profil — elle sert uniquement
            à estimer les durées de traitement affichées dans la table ci-dessous.
          </p>
          <p>
            Vous pouvez forcer un profil différent via le sélecteur « Changer le profil ».
            Un avertissement s&apos;affiche si le profil choisi nécessite plus de RAM que disponible,
            car cela peut provoquer des ralentissements ou des erreurs mémoire.
          </p>
        </div>
      </details>

      {/* ---- Reference table ---- */}
      <div className={styles.referenceTable}>
        <h3 className={styles.tableTitle}>Profils disponibles</h3>
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Profil</th>
                <th>RAM</th>
                <th>Modèle</th>
                <th>CTX_MAX</th>
                <th>Chunks RAG</th>
                <th>Step 1</th>
                <th>Step 2</th>
                <th>Step 3</th>
                <th>Step 4</th>
                <th>Step 5</th>
              </tr>
            </thead>
            <tbody>
              {allProfiles.map((profile) => {
                const isAutoDetected = profile.name === autoDetectedProfile;
                return (
                  <tr
                    key={profile.name}
                    className={isAutoDetected ? styles.detectedRow : undefined}
                  >
                    <td>
                      <span className={styles.profileCellName}>
                        {profile.display_name}
                        {isAutoDetected && (
                          <span className={styles.detectedBadge} title="Profil détecté automatiquement">
                            ★
                          </span>
                        )}
                      </span>
                    </td>
                    <td>{profile.ram_range}</td>
                    <td className={styles.modelCell}>{profile.model}</td>
                    <td>{profile.ctx_max.toLocaleString("fr-FR")}</td>
                    <td>{profile.rag_chunks}</td>
                    <td className={styles.durationCell}>{profile.step_durations?.step1 ?? "—"}</td>
                    <td className={styles.durationCell}>{profile.step_durations?.step2 ?? "—"}</td>
                    <td className={styles.durationCell}>{profile.step_durations?.step3 ?? "—"}</td>
                    <td className={styles.durationCell}>{profile.step_durations?.step4 ?? "—"}</td>
                    <td className={styles.durationCell}>{profile.step_durations?.step5 ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className={styles.tableNote}>
          ★ = profil détecté automatiquement • Les durées sont des estimations ± variables selon la complexité du dossier.
        </p>
      </div>
    </div>
  );
}
