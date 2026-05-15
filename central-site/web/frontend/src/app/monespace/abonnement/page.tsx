"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import {
  apiGetSubscriptionStatus,
  apiTerminateSubscription,
  ApiError,
  type SubscriptionStatus,
} from "@/lib/api";
import styles from "./abonnement.module.css";

/** Labels lisibles pour chaque statut d'abonnement. */
const STATUS_LABELS: Record<SubscriptionStatus["status"], string> = {
  active: "Actif",
  blocked: "Bloqué",
  terminating: "En cours de résiliation",
};

/** Classe CSS du badge selon le statut. */
function badgeClass(status: SubscriptionStatus["status"]): string {
  switch (status) {
    case "active":
      return styles.statusActive;
    case "blocked":
      return styles.statusBlocked;
    case "terminating":
      return styles.statusTerminating;
    default:
      return "";
  }
}

export default function AbonnementPage() {
  const { accessToken } = useAuth();

  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [showConfirm, setShowConfirm] = useState(false);
  const [isTerminating, setIsTerminating] = useState(false);

  useEffect(() => {
    if (!accessToken) return;

    apiGetSubscriptionStatus(accessToken)
      .then((data) => {
        setSubscription(data);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          // Pas d'abonnement actif
          setSubscription(null);
        } else {
          setError("Impossible de charger les informations d'abonnement.");
        }
      })
      .finally(() => setLoading(false));
  }, [accessToken]);

  async function handleTerminate() {
    if (!accessToken) return;

    setIsTerminating(true);
    setError("");
    setSuccess("");

    try {
      const result = await apiTerminateSubscription(accessToken);
      setSuccess(result.message);
      // Mettre à jour l'état local pour refléter la résiliation programmée
      setSubscription((prev) =>
        prev
          ? { ...prev, status: "terminating", termination_date: result.termination_date }
          : prev
      );
      setShowConfirm(false);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Erreur lors de la résiliation. Veuillez réessayer.");
      }
      setShowConfirm(false);
    } finally {
      setIsTerminating(false);
    }
  }

  if (loading) {
    return <p className={styles.emptyState}>Chargement…</p>;
  }

  if (!subscription) {
    return (
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Abonnement</h2>
        <p className={styles.emptyState}>Aucun abonnement actif.</p>
      </section>
    );
  }

  return (
    <>
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Mon abonnement</h2>

        {success && (
          <div className={styles.successMessage} role="status">
            {success}
          </div>
        )}
        {error && (
          <div className={styles.errorMessage} role="alert">
            {error}
          </div>
        )}

        {/* Statut */}
        <div className={styles.statusRow}>
          <span className={styles.statusLabel}>Statut :</span>
          <span className={`${styles.statusBadge} ${badgeClass(subscription.status)}`}>
            {STATUS_LABELS[subscription.status]}
          </span>
        </div>

        {/* Date de fin de période */}
        {subscription.current_period_end && (
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Fin de période en cours</span>
            <span className={styles.infoValue}>
              {new Date(subscription.current_period_end).toLocaleDateString("fr-FR", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </span>
          </div>
        )}

        {/* Date de fin effective si résiliation programmée */}
        {subscription.status === "terminating" && subscription.termination_date && (
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Date de fin effective</span>
            <span className={styles.infoValue}>
              {new Date(subscription.termination_date).toLocaleDateString("fr-FR", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </span>
          </div>
        )}

        {/* Bouton de résiliation — visible uniquement si abonnement actif */}
        {subscription.status === "active" && (
          <button
            type="button"
            className={styles.terminateBtn}
            onClick={() => setShowConfirm(true)}
          >
            Résilier mon abonnement
          </button>
        )}
      </section>

      {/* Modal de confirmation */}
      {showConfirm && (
        <div
          className={styles.confirmOverlay}
          onClick={() => setShowConfirm(false)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="terminate-dialog-title"
        >
          <div className={styles.confirmDialog} onClick={(e) => e.stopPropagation()}>
            <h3 id="terminate-dialog-title" className={styles.confirmTitle}>
              Confirmer la résiliation
            </h3>
            <p className={styles.confirmText}>
              Êtes-vous sûr de vouloir résilier votre abonnement ? Vous conserverez
              l&apos;accès aux services jusqu&apos;à la fin de la période de facturation
              en cours.
            </p>
            <div className={styles.confirmActions}>
              <button
                type="button"
                className={styles.cancelBtn}
                onClick={() => setShowConfirm(false)}
              >
                Annuler
              </button>
              <button
                type="button"
                className={styles.terminateBtn}
                disabled={isTerminating}
                onClick={handleTerminate}
              >
                {isTerminating ? "Résiliation…" : "Confirmer la résiliation"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
