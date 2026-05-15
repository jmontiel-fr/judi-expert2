"use client";

import { useState, useCallback, type FormEvent } from "react";
import { apiUpdateBillingProfile, ApiError, type BillingProfileData } from "@/lib/api";

/**
 * Initial billing profile data passed to the form.
 */
export interface BillingProfile {
  entreprise: string | null;
  company_address: string | null;
  billing_email: string | null;
  siret: string | null;
}

interface ProfileBillingFormProps {
  initialData: BillingProfile;
  accessToken: string;
  onSuccess?: () => void;
}

/** Validates that SIRET is exactly 14 digits. */
function isValidSiret(value: string): boolean {
  return /^\d{14}$/.test(value);
}

/**
 * ProfileBillingForm — Formulaire de profil facturation.
 *
 * Tous les experts sont traités en B2B dans les métadonnées Stripe.
 * Champs : entreprise (optionnel), adresse entreprise, email facturation, SIRET (optionnel).
 * Note : Le SIRET permet l'émission de factures professionnelles complètes.
 * S'il n'est pas renseigné, il sera affiché comme "non attribué".
 */
export default function ProfileBillingForm({
  initialData,
  accessToken,
  onSuccess,
}: ProfileBillingFormProps) {
  const [entreprise, setEntreprise] = useState(initialData.entreprise || "");
  const [companyAddress, setCompanyAddress] = useState(
    initialData.company_address || ""
  );
  const [billingEmail, setBillingEmail] = useState(
    initialData.billing_email || ""
  );
  const [siret, setSiret] = useState(initialData.siret || "");

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [isError, setIsError] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  /** Client-side validation. Returns true if valid. */
  function validate(): boolean {
    const errors: Record<string, string> = {};

    // SIRET is optional, but if provided must be 14 digits
    if (siret.trim() && !isValidSiret(siret.trim())) {
      errors.siret = "Le SIRET doit contenir exactement 14 chiffres";
    }

    // Billing email format check (basic)
    if (billingEmail.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(billingEmail.trim())) {
      errors.billing_email = "Format d'email invalide";
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      setMessage(null);
      setIsError(false);

      if (!validate()) {
        return;
      }

      setLoading(true);

      const payload: BillingProfileData = {
        entreprise: entreprise.trim() || null,
        company_address: companyAddress.trim() || null,
        billing_email: billingEmail.trim() || null,
        siret: siret.trim() || null,
      };

      try {
        await apiUpdateBillingProfile(accessToken, payload);
        setMessage("Profil de facturation mis à jour avec succès.");
        setIsError(false);
        if (onSuccess) {
          onSuccess();
        }
      } catch (err) {
        if (err instanceof ApiError) {
          setMessage(err.message);
        } else {
          setMessage("Erreur inattendue lors de la mise à jour.");
        }
        setIsError(true);
      } finally {
        setLoading(false);
      }
    },
    [entreprise, companyAddress, billingEmail, siret, accessToken, onSuccess]
  );

  return (
    <form onSubmit={handleSubmit} noValidate aria-label="Formulaire profil facturation">
      <div
        style={{
          border: "1px solid var(--color-border, #e5e7eb)",
          borderRadius: 8,
          padding: 16,
          marginBottom: 20,
          backgroundColor: "var(--color-bg-subtle, #f9fafb)",
        }}
      >
        <h3
          style={{
            fontSize: "0.9rem",
            fontWeight: 600,
            marginBottom: 14,
            color: "var(--color-text, #1f2937)",
          }}
        >
          Informations de facturation
        </h3>

        {/* Entreprise */}
        <div style={{ marginBottom: 14 }}>
          <label
            htmlFor="entreprise"
            style={{ display: "block", fontSize: "0.85rem", fontWeight: 500, marginBottom: 4 }}
          >
            Entreprise
          </label>
          <input
            id="entreprise"
            type="text"
            value={entreprise}
            onChange={(e) => setEntreprise(e.target.value)}
            placeholder="Nom de l'entreprise (optionnel)"
            style={{
              width: "100%",
              padding: "8px 12px",
              fontSize: "0.9rem",
              border: "1px solid var(--color-border, #d1d5db)",
              borderRadius: 6,
              boxSizing: "border-box",
            }}
          />
        </div>

        {/* Company address */}
        <div style={{ marginBottom: 14 }}>
          <label
            htmlFor="company_address"
            style={{ display: "block", fontSize: "0.85rem", fontWeight: 500, marginBottom: 4 }}
          >
            Adresse entreprise
          </label>
          <input
            id="company_address"
            type="text"
            value={companyAddress}
            onChange={(e) => setCompanyAddress(e.target.value)}
            placeholder="Adresse de facturation"
            style={{
              width: "100%",
              padding: "8px 12px",
              fontSize: "0.9rem",
              border: "1px solid var(--color-border, #d1d5db)",
              borderRadius: 6,
              boxSizing: "border-box",
            }}
          />
        </div>

        {/* Billing email */}
        <div style={{ marginBottom: 14 }}>
          <label
            htmlFor="billing_email"
            style={{ display: "block", fontSize: "0.85rem", fontWeight: 500, marginBottom: 4 }}
          >
            Email de facturation
          </label>
          <input
            id="billing_email"
            type="email"
            value={billingEmail}
            onChange={(e) => setBillingEmail(e.target.value)}
            placeholder="Email pour les factures"
            aria-invalid={!!fieldErrors.billing_email}
            aria-describedby={fieldErrors.billing_email ? "err-billing_email" : undefined}
            style={{
              width: "100%",
              padding: "8px 12px",
              fontSize: "0.9rem",
              border: `1px solid ${fieldErrors.billing_email ? "#dc2626" : "var(--color-border, #d1d5db)"}`,
              borderRadius: 6,
              boxSizing: "border-box",
            }}
          />
          {fieldErrors.billing_email && (
            <p id="err-billing_email" style={{ color: "#dc2626", fontSize: "0.8rem", marginTop: 4 }} role="alert">
              {fieldErrors.billing_email}
            </p>
          )}
        </div>

        {/* SIRET */}
        <div style={{ marginBottom: 0 }}>
          <label
            htmlFor="siret"
            style={{ display: "block", fontSize: "0.85rem", fontWeight: 500, marginBottom: 4 }}
          >
            SIRET
          </label>
          <input
            id="siret"
            type="text"
            value={siret}
            onChange={(e) => setSiret(e.target.value)}
            maxLength={14}
            placeholder="14 chiffres (optionnel)"
            aria-invalid={!!fieldErrors.siret}
            aria-describedby="siret-hint"
            style={{
              width: "100%",
              padding: "8px 12px",
              fontSize: "0.9rem",
              border: `1px solid ${fieldErrors.siret ? "#dc2626" : "var(--color-border, #d1d5db)"}`,
              borderRadius: 6,
              boxSizing: "border-box",
            }}
          />
          <p
            id="siret-hint"
            style={{ fontSize: "0.75rem", color: "var(--color-text-muted, #6b7280)", marginTop: 3 }}
          >
            Le SIRET permet l&apos;émission de factures professionnelles complètes.
            S&apos;il n&apos;est pas renseigné, il sera affiché comme &quot;non attribué&quot;.
          </p>
          {fieldErrors.siret && (
            <p style={{ color: "#dc2626", fontSize: "0.8rem", marginTop: 2 }} role="alert">
              {fieldErrors.siret}
            </p>
          )}
        </div>
      </div>

      {/* Submit button */}
      <button
        type="submit"
        disabled={loading}
        style={{
          padding: "10px 20px",
          fontSize: "0.9rem",
          fontWeight: 600,
          color: "#fff",
          backgroundColor: loading ? "#9ca3af" : "#2563eb",
          border: "none",
          borderRadius: 6,
          cursor: loading ? "not-allowed" : "pointer",
          transition: "background-color 0.2s",
        }}
      >
        {loading ? "Enregistrement…" : "Enregistrer"}
      </button>

      {/* Status message */}
      {message && (
        <p
          style={{
            marginTop: 12,
            fontSize: "0.85rem",
            color: isError ? "#dc2626" : "#16a34a",
            fontWeight: 500,
          }}
          role="status"
          aria-live="polite"
        >
          {message}
        </p>
      )}
    </form>
  );
}
