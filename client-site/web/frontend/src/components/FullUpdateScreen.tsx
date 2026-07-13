"use client";

import styles from "./UpdateScreen.module.css";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FullUpdateScreenProps {
  /** URL to download the new installer */
  downloadUrl: string;
  /** Target version (semver) */
  targetVersion: string;
  /** Optional release notes to display */
  releaseNotes?: string | null;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Full-screen blocking modal displayed when a full reinstallation is required.
 *
 * Unlike UpdateScreen (which handles image-only updates in-place), this screen
 * instructs the expert to download and run the new installer manually.
 * This is necessary when non-container files changed (docker-compose.yml,
 * .env, scripts, etc.).
 *
 * Requirements: 3.3, 4.3
 */
export default function FullUpdateScreen({ downloadUrl, targetVersion, releaseNotes }: FullUpdateScreenProps) {
  return (
    <div className={styles.overlay} role="dialog" aria-modal="true" aria-label="Nouvelle version disponible">
      <div className={styles.modal}>
        {/* Header */}
        <div className={styles.header}>
          <span className={styles.icon} aria-hidden="true">📦</span>
          <h2 className={styles.title}>Nouvelle version disponible</h2>
          <p className={styles.subtitle}>Version {targetVersion}</p>
        </div>

        {/* Content */}
        <div className={styles.progressSection}>
          <p style={{ textAlign: "center", marginBottom: "1rem", color: "#333" }}>
            Cette mise à jour nécessite une <strong>réinstallation complète</strong>.
          </p>
          <p style={{ textAlign: "center", marginBottom: "1.5rem", color: "#555", fontSize: "0.9rem" }}>
            Téléchargez le nouvel installateur et exécutez-le. Vos données (dossiers, configuration) seront automatiquement préservées.
          </p>

          {releaseNotes && (
            <div style={{ background: "#f8f9fa", borderRadius: "8px", padding: "12px 16px", marginBottom: "1.5rem" }}>
              <p style={{ fontSize: "0.85rem", color: "#666", marginBottom: "4px" }}>Notes de version :</p>
              <p style={{ fontSize: "0.9rem", color: "#333" }}>{releaseNotes}</p>
            </div>
          )}

          <a
            href={downloadUrl}
            className={styles.retryButton}
            style={{ display: "block", textAlign: "center", textDecoration: "none" }}
            download
          >
            Télécharger l&apos;installateur V{targetVersion}
          </a>
        </div>
      </div>
    </div>
  );
}
