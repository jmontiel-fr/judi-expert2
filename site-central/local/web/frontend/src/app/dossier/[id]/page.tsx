"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import styles from "./dossier.module.css";
import {
  dossiersApi,
  getErrorMessage,
  isStepAccessible,
  type DossierDetail,
} from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Constants                                                           */
/* ------------------------------------------------------------------ */

const STEP_NAMES: Record<number, string> = {
  0: "Extraction",
  1: "PEMEC",
  2: "Upload",
  3: "REF",
};

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/* ------------------------------------------------------------------ */
/* Main component                                                      */
/* ------------------------------------------------------------------ */

export default function DossierDetailPage() {
  const params = useParams();
  const dossierId = params.id as string;

  const [dossier, setDossier] = useState<DossierDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchDossier = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await dossiersApi.get(dossierId);
      setDossier(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err, "Impossible de charger le dossier."));
    } finally {
      setLoading(false);
    }
  }, [dossierId]);

  useEffect(() => {
    fetchDossier();
  }, [fetchDossier]);

  /* ---------------------------------------------------------------- */
  /* Render                                                            */
  /* ---------------------------------------------------------------- */

  return (
    <div className={styles.container}>
      {/* Back link */}
      <Link href="/" className={styles.backLink}>
        <span className={styles.backArrow} aria-hidden="true">←</span>
        Retour aux dossiers
      </Link>

      {/* Loading */}
      {loading && (
        <div className={styles.loading}>
          <span className={styles.spinner} aria-hidden="true" />
          Chargement du dossier…
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <p className={styles.error} role="alert">{error}</p>
      )}

      {/* Dossier detail */}
      {!loading && !error && dossier && (
        <>
          {/* Dossier header */}
          <div className={styles.header}>
            <h1 className={styles.title}>{dossier.nom}</h1>
            <div className={styles.meta}>
              <span className={`${styles.badge} ${styles.badgeDomaine}`}>
                {dossier.domaine}
              </span>
              <span
                className={`${styles.badge} ${
                  dossier.statut === "actif"
                    ? styles.badgeActif
                    : styles.badgeArchive
                }`}
              >
                {dossier.statut === "actif" ? "Actif" : "Archivé"}
              </span>
              <span>Créé le {formatDate(dossier.created_at)}</span>
            </div>
          </div>

          {/* Steps section */}
          <h2 className={styles.sectionTitle}>Étapes du dossier</h2>
          <div className={styles.stepList} role="list">
            {[...dossier.steps]
              .sort((a, b) => a.step_number - b.step_number)
              .map((step) => {
                const accessible = isStepAccessible(step.step_number, dossier.steps);
                const stepLabel = `Étape ${step.step_number} — ${STEP_NAMES[step.step_number] ?? `Step${step.step_number}`}`;

                const statusClass =
                  step.statut === "valide"
                    ? styles.statusValide
                    : step.statut === "realise"
                      ? styles.statusRealise
                      : styles.statusInitial;

                const statusLabel =
                  step.statut === "valide"
                    ? "Validé"
                    : step.statut === "realise"
                      ? "Réalisé"
                      : "Initial";

                const cardContent = (
                  <>
                    <div className={styles.stepInfo}>
                      <div className={styles.stepHeader}>
                        <span className={styles.stepNumber}>{step.step_number}</span>
                        <span className={styles.stepName}>
                          {STEP_NAMES[step.step_number] ?? `Step${step.step_number}`}
                        </span>
                      </div>
                      <div className={styles.stepDates}>
                        {step.executed_at && (
                          <span>Exécuté : {formatDateTime(step.executed_at)}</span>
                        )}
                        {step.validated_at && (
                          <span>Validé : {formatDateTime(step.validated_at)}</span>
                        )}
                      </div>
                    </div>
                    <div className={styles.stepRight}>
                      <span className={`${styles.statusBadge} ${statusClass}`}>
                        {statusLabel}
                      </span>
                      {accessible ? (
                        <span className={styles.accessArrow} aria-hidden="true">→</span>
                      ) : (
                        <span className={styles.lockIcon} aria-hidden="true" title="Étape verrouillée">🔒</span>
                      )}
                    </div>
                  </>
                );

                if (accessible) {
                  return (
                    <Link
                      key={step.step_number}
                      href={`/dossier/${dossier.id}/step/${step.step_number}`}
                      className={`${styles.stepCard} ${styles.stepCardAccessible}`}
                      role="listitem"
                      aria-label={`${stepLabel} — ${statusLabel}`}
                    >
                      {cardContent}
                    </Link>
                  );
                }

                return (
                  <div
                    key={step.step_number}
                    className={`${styles.stepCard} ${styles.stepCardLocked}`}
                    role="listitem"
                    aria-label={`${stepLabel} — ${statusLabel} — Verrouillé`}
                  >
                    {cardContent}
                  </div>
                );
              })}
          </div>
        </>
      )}
    </div>
  );
}
