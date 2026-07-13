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
  dac_available: boolean;
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
          Note technique — Sélection du profil et répartition mémoire
        </summary>
        <div className={styles.strategyContent}>
          <h4>Répartition de la RAM</h4>
          <p>
            Le modèle LLM n&apos;est pas le seul composant à utiliser la mémoire.
            Voici la consommation estimée des autres services :
          </p>
          <table className={styles.memTable}>
            <thead>
              <tr><th>Composant</th><th>RAM réservée</th></tr>
            </thead>
            <tbody>
              <tr><td>Système d&apos;exploitation (Windows)</td><td>~2,5 Go</td></tr>
              <tr><td>Marge utilisateur (navigateur + bureautique)</td><td>~3 Go</td></tr>
              <tr><td>Docker Desktop</td><td>~0,5 Go</td></tr>
              <tr><td>Qdrant (base vectorielle RAG)</td><td>≤ 1 Go</td></tr>
              <tr><td>Backend (FastAPI)</td><td>≤ 512 Mo</td></tr>
              <tr><td>Frontend (Next.js)</td><td>≤ 512 Mo</td></tr>
              <tr><td>OCR (Tesseract)</td><td>≤ 512 Mo</td></tr>
              <tr><td><strong>Total hors LLM</strong></td><td><strong>~7 Go</strong></td></tr>
            </tbody>
          </table>
          <p>
            La <strong>RAM disponible pour le LLM</strong> = RAM totale de votre PC − 7 Go.
            C&apos;est sur cette base que le profil optimal est sélectionné automatiquement.
          </p>

          <h4>Choix du modèle LLM</h4>
          <p>
            Le modèle est adapté à la RAM disponible pour garantir la stabilité.
            Les modèles 7B (Mistral) offrent la meilleure qualité en français juridique mais
            nécessitent plus de mémoire. Les modèles plus petits (Qwen 3B / 1.5B) sont utilisés
            quand la RAM est insuffisante pour un modèle 7B.
          </p>
          <ul>
            <li><strong>≥ 32 Go</strong> → Mistral 7B (q4_0, 4,7 Go) — qualité maximale, contexte 8K tokens</li>
            <li><strong>16 – 32 Go</strong> → Mistral 7B (q3_K_M, 3,6 Go) — même qualité, quantization allégée</li>
            <li><strong>8 – 16 Go</strong> → Qwen 2.5 3B (q4_0, 2 Go) — bon compromis sur RAM limitée</li>
            <li><strong>&lt; 8 Go</strong> → Qwen 2.5 1.5B (q4_0, 1 Go) — fonctionnel mais qualité réduite</li>
          </ul>

          <h4>Marge utilisateur</h4>
          <p>
            Une marge de <strong>3 Go</strong> est réservée pour que vous puissiez utiliser
            simultanément un navigateur web et une suite bureautique (Word, LibreOffice, etc.)
            sans ralentissement. Si vous constatez des lenteurs, fermez les applications
            non essentielles ou passez au profil inférieur.
          </p>

          <h4>Forcer un profil</h4>
          <p>
            Vous pouvez forcer un profil différent via le sélecteur ci-dessus.
            Un avertissement s&apos;affiche si le profil choisi nécessite plus de RAM que disponible,
            car cela peut provoquer des ralentissements ou des erreurs mémoire.
            Le modèle sera téléchargé automatiquement si nécessaire.
          </p>

          <h4>Service DAC (Document d&apos;Analyse Contradictoire)</h4>
          <p>
            Le DAC analyse le rapport d&apos;expertise final (PRE) en le croisant avec le corpus
            métier (ex : ebook de psychologie) via le RAG. Ce service nécessite un modèle 7B
            avec un contexte suffisant pour traiter des documents longs.
          </p>
          <ul>
            <li><strong>High / Medium</strong> → DAC disponible (Mistral 7B)</li>
            <li><strong>Low / Minimal</strong> → DAC non disponible (modèle trop petit pour une analyse contradictoire fiable)</li>
          </ul>

          <h4>Impact CPU / GPU sur la vitesse</h4>
          <p>
            La RAM détermine <strong>quel modèle</strong> peut tourner, mais c&apos;est le
            <strong> CPU (ou GPU)</strong> qui détermine <strong>à quelle vitesse</strong> il génère les réponses.
          </p>
          <table className={styles.memTable}>
            <thead>
              <tr><th>Configuration</th><th>Vitesse estimée</th><th>Temps par étape</th></tr>
            </thead>
            <tbody>
              <tr><td>CPU 4 cœurs / 2 GHz</td><td>~4 tokens/s</td><td>2–5 min</td></tr>
              <tr><td>CPU 6 cœurs / 3 GHz</td><td>~9 tokens/s</td><td>45 s – 2 min</td></tr>
              <tr><td>CPU 8 cœurs / 4 GHz</td><td>~16 tokens/s</td><td>20 – 50 s</td></tr>
              <tr><td>GPU NVIDIA RTX 3060 (12 Go VRAM)</td><td>~40 tokens/s</td><td>10 – 20 s</td></tr>
              <tr><td>GPU NVIDIA RTX 4070 (12 Go VRAM)</td><td>~60 tokens/s</td><td>5 – 15 s</td></tr>
            </tbody>
          </table>
          <p>
            <strong>GPU :</strong> si un GPU NVIDIA compatible est détecté avec suffisamment de VRAM
            (≥ taille du modèle), Ollama l&apos;utilise automatiquement. Le modèle est alors chargé
            en VRAM au lieu de la RAM, libérant de la mémoire pour les autres services.
            Aucune configuration manuelle n&apos;est nécessaire (NVIDIA Container Toolkit requis).
          </p>
          <p>
            <strong>CPU seul :</strong> le modèle tourne en RAM classique. La vitesse dépend du
            nombre de cœurs physiques et de la fréquence. Les modèles plus petits (3B, 1.5B)
            sont aussi plus rapides en inférence — un Qwen 3B sur CPU génère environ 2× plus vite
            qu&apos;un Mistral 7B sur le même processeur.
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
                <th>DAC</th>
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
                    <td>{profile.dac_available ? "✅" : "❌"}</td>
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
