"use client";

import { useState, useEffect } from "react";
import { loadStripe } from "@stripe/stripe-js";
import { useAuth } from "@/contexts/AuthContext";
import { apiListTickets, apiPurchaseTicket, type TicketItem, ApiError } from "@/lib/api";
import styles from "./tickets.module.css";

const stripePromise = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
  ? loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY)
  : null;

export default function TicketsPage() {
  const { user, accessToken } = useAuth();
  const [tickets, setTickets] = useState<TicketItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [isPurchasing, setIsPurchasing] = useState(false);
  const [purchaseMsg, setPurchaseMsg] = useState("");
  const [purchaseError, setPurchaseError] = useState("");
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    async function load() {
      if (!accessToken) return;
      try {
        const data = await apiListTickets(accessToken);
        setTickets(data);
      } catch {
        setLoadError("Impossible de charger vos tickets.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [accessToken]);

  async function handlePurchase() {
    setPurchaseMsg("");
    setPurchaseError("");
    if (!accessToken) { setPurchaseError("Vous devez être connecté"); return; }

    setIsPurchasing(true);
    try {
      const result = await apiPurchaseTicket(accessToken);

      // Redirect to Stripe Checkout
      if (stripePromise) {
        setPurchaseMsg("Redirection vers Stripe Checkout…");
        const stripe = await stripePromise;
        if (stripe) {
          // The backend returns a full checkout URL — redirect directly
          window.location.href = result.checkout_url;
          return;
        }
      }
      // Fallback: direct redirect to checkout URL
      window.location.href = result.checkout_url;
    } catch (err) {
      if (err instanceof ApiError) {
        setPurchaseError(err.message);
      } else {
        setPurchaseError("Erreur lors de la création de la session de paiement");
      }
    } finally {
      setIsPurchasing(false);
    }
  }

  if (!user) return null;

  return (
    <>
      <div className={styles.header}>
        <h2 className={styles.sectionTitle}>Mes tickets</h2>
        <button type="button" className={styles.buyBtn} disabled={isPurchasing} onClick={handlePurchase}>
          {isPurchasing ? "Chargement…" : "Acheter un ticket"}
        </button>
      </div>

      {purchaseMsg && <div className={styles.successMessage} role="status">{purchaseMsg}</div>}
      {purchaseError && <div className={styles.errorMessage} role="alert">{purchaseError}</div>}
      {loadError && <div className={styles.errorMessage} role="alert">{loadError}</div>}

      {loading ? (
        <p>Chargement de vos tickets…</p>
      ) : tickets.length === 0 ? (
        <p className={styles.emptyState}>
          Vous n&apos;avez pas encore de tickets. Achetez votre premier ticket pour créer un dossier d&apos;expertise.
        </p>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Code ticket</th>
              <th>Domaine</th>
              <th>Date</th>
              <th>Montant</th>
              <th>Statut</th>
            </tr>
          </thead>
          <tbody>
            {tickets.map((t) => (
              <tr key={t.id}>
                <td>{t.ticket_code}</td>
                <td>{t.domaine}</td>
                <td>{new Date(t.created_at).toLocaleDateString("fr-FR")}</td>
                <td>{Number(t.montant).toFixed(2)} €</td>
                <td>
                  <span className={t.statut === "actif" ? styles.statusActif : styles.statusUtilise}>
                    {t.statut === "actif" ? "Actif" : "Utilisé"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
