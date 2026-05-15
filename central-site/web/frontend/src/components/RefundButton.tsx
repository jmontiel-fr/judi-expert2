"use client";

import { useState, useCallback } from "react";
import { apiRefundTicket, ApiError } from "@/lib/api";

/**
 * Ticket data required by the RefundButton component.
 * Only the fields relevant to refund visibility and action are needed.
 */
export interface RefundTicket {
  id: number;
  statut: string;
  stripe_payment_id: string | null;
}

interface RefundButtonProps {
  ticket: RefundTicket;
  accessToken: string;
  onRefundSuccess?: () => void;
}

/**
 * Displays a "Re-créditer" button for eligible tickets.
 *
 * Visibility rules:
 * - ticket.statut === "actif"
 * - ticket.stripe_payment_id exists (non-null, non-empty)
 * - ticket.stripe_payment_id does not start with "pending-"
 *
 * Validates: Requirements 4.1, 4.2, 4.4, 4.5
 */
export default function RefundButton({ ticket, accessToken, onRefundSuccess }: RefundButtonProps) {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [isError, setIsError] = useState(false);

  // Visibility check: only show for active tickets with a valid stripe_payment_id
  const isVisible =
    ticket.statut === "actif" &&
    !!ticket.stripe_payment_id &&
    !ticket.stripe_payment_id.startsWith("pending-");

  const handleRefund = useCallback(async () => {
    // Confirmation dialog before proceeding
    const confirmed = window.confirm(
      "Êtes-vous sûr de vouloir re-créditer ce ticket ? Cette action est irréversible."
    );
    if (!confirmed) return;

    setLoading(true);
    setMessage(null);
    setIsError(false);

    try {
      const result = await apiRefundTicket(accessToken, ticket.id);
      setMessage(result.message || "Remboursement effectué avec succès.");
      setIsError(false);
      if (onRefundSuccess) {
        onRefundSuccess();
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setMessage(err.message);
      } else {
        setMessage("Erreur inattendue lors du remboursement.");
      }
      setIsError(true);
    } finally {
      setLoading(false);
    }
  }, [accessToken, ticket.id, onRefundSuccess]);

  if (!isVisible) {
    return null;
  }

  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
      <button
        type="button"
        onClick={handleRefund}
        disabled={loading}
        aria-label={`Re-créditer le ticket #${ticket.id}`}
        style={{
          padding: "6px 12px",
          fontSize: "0.85rem",
          fontWeight: 500,
          color: "#fff",
          backgroundColor: loading ? "#9ca3af" : "#dc2626",
          border: "none",
          borderRadius: 6,
          cursor: loading ? "not-allowed" : "pointer",
          transition: "background-color 0.2s",
        }}
      >
        {loading ? "Remboursement…" : "Re-créditer"}
      </button>
      {message && (
        <span
          style={{
            fontSize: "0.8rem",
            color: isError ? "#dc2626" : "#16a34a",
            maxWidth: 250,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
          title={message}
          role="status"
          aria-live="polite"
        >
          {message}
        </span>
      )}
    </div>
  );
}
