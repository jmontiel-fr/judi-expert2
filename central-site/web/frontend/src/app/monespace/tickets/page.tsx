"use client";

import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { loadStripe } from "@stripe/stripe-js";
import { useAuth } from "@/contexts/AuthContext";
import {
  apiListTickets,
  apiPurchaseTicket,
  apiDeleteTicket,
  apiGetTicketPrice,
  type TicketItem,
  type TicketPriceInfo,
  ApiError,
} from "@/lib/api";
import styles from "./tickets.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

const stripePromise = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
  ? loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY)
  : null;

function formatEuro(n: number): string {
  return n.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
    timeZone: "Europe/Paris",
    timeZoneName: "short",
  });
}

function computeStatutLabel(t: TicketItem): { label: string; className: string } {
  if (t.statut === "utilisé") {
    return { label: "Utilisé", className: styles.statusUtilise };
  }
  if (t.expires_at && new Date(t.expires_at) < new Date()) {
    return { label: "Périmé", className: styles.statusPerime };
  }
  return { label: "Valide", className: styles.statusActif };
}

export default function TicketsPage() {
  const { user, accessToken } = useAuth();
  const [tickets, setTickets] = useState<TicketItem[]>([]);
  const [priceInfo, setPriceInfo] = useState<TicketPriceInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [isPurchasing, setIsPurchasing] = useState(false);
  const [purchaseMsg, setPurchaseMsg] = useState("");
  const [purchaseError, setPurchaseError] = useState("");
  const [loadError, setLoadError] = useState("");
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    if (!accessToken) return;
    try {
      const [ticketData, price] = await Promise.all([
        apiListTickets(accessToken),
        apiGetTicketPrice(),
      ]);
      setTickets(ticketData);
      setPriceInfo(price);
    } catch {
      setLoadError("Impossible de charger vos tickets.");
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => { loadData(); }, [loadData]);

  // Confirm ticket after Stripe Checkout return
  const searchParams = useSearchParams();
  useEffect(() => {
    const success = searchParams.get("success");
    const ticketCode = searchParams.get("ticket_code");
    if (success === "true" && ticketCode && accessToken) {
      fetch(`${API_BASE}/api/tickets/confirm?ticket_code=${encodeURIComponent(ticketCode)}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${accessToken}`,
        },
      })
        .then(() => {
          setPurchaseMsg("Paiement confirmé — ticket activé !");
          loadData();
        })
        .catch(() => {});
      // Clean URL
      window.history.replaceState({}, "", "/monespace/tickets");
    }
  }, [searchParams, accessToken, loadData]);

  async function handlePurchase() {
    setPurchaseMsg("");
    setPurchaseError("");
    if (!accessToken) { setPurchaseError("Vous devez être connecté"); return; }

    setIsPurchasing(true);
    try {
      const result = await apiPurchaseTicket(accessToken);
      // Always redirect to Stripe Checkout (dev with test keys, prod with live keys)
      setPurchaseMsg("Redirection vers Stripe Checkout…");
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

  function handleCopyToken(ticket: TicketItem) {
    if (!ticket.ticket_token) return;
    navigator.clipboard.writeText(ticket.ticket_token).then(() => {
      setCopiedId(ticket.id);
      setTimeout(() => setCopiedId(null), 2000);
    });
  }

  async function handleDelete(ticketId: number) {
    if (!accessToken) return;
    if (!confirm("Supprimer ce ticket ?")) return;
    try {
      await apiDeleteTicket(accessToken, ticketId);
      setTickets((prev) => prev.filter((t) => t.id !== ticketId));
    } catch (err) {
      if (err instanceof ApiError) {
        setPurchaseError(err.message);
      }
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

      {priceInfo && (
        <div className={styles.priceInfo} role="status">
          Prix du ticket : {formatEuro(priceInfo.prix_ht)} € HT
          (TVA {formatEuro(priceInfo.tva_rate)}%)
          = {formatEuro(priceInfo.prix_ttc)} € TTC
        </div>
      )}

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
              <th>Statut</th>
              <th>Date d&apos;achat</th>
              <th>Expiration</th>
              <th>Domaine</th>
              <th>Montant</th>
              <th>Token</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tickets.map((t) => {
              const { label, className } = computeStatutLabel(t);
              const isUsable = label === "Valide";
              return (
                <tr key={t.id} className={!isUsable ? styles.rowInactive : ""}>
                  <td>
                    <span className={className}>{label}</span>
                  </td>
                  <td>{formatDate(t.created_at)}</td>
                  <td>{t.expires_at ? formatDate(t.expires_at) : "—"}</td>
                  <td>{t.domaine}</td>
                  <td>{formatEuro(Number(t.montant))} €</td>
                  <td>
                    {isUsable && t.ticket_token ? (
                      <button
                        type="button"
                        className={styles.copyBtn}
                        onClick={() => handleCopyToken(t)}
                        title="Copier le token pour l'application locale"
                      >
                        {copiedId === t.id ? "✓ Copié" : "Copier"}
                      </button>
                    ) : (
                      <span className={styles.tokenNA}>—</span>
                    )}
                  </td>
                  <td>
                    <button
                      type="button"
                      className={styles.deleteBtn}
                      onClick={() => handleDelete(t.id)}
                      title="Supprimer ce ticket"
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </>
  );
}
