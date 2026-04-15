"use client";

import { useState, useCallback, type FormEvent } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { apiSubmitContact } from "@/lib/api";
import ReCaptchaWidget from "@/components/ReCaptchaWidget";
import styles from "./contact.module.css";

const DOMAINES = [
  "psychologie", "psychiatrie", "médecine légale", "bâtiment", "comptabilité", "général",
] as const;

const OBJETS = ["Problème", "Demande d'amélioration", "Autre"] as const;

interface FormData { domaine: string; objet: string; message: string; bloquant: boolean; urgent: boolean; }
interface FormErrors { domaine?: string; objet?: string; message?: string; }

export default function ContactPage() {
  const { accessToken } = useAuth();
  const [formData, setFormData] = useState<FormData>({ domaine: "", objet: "", message: "", bloquant: false, urgent: false });
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState("");
  const [submitSuccess, setSubmitSuccess] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);

  const handleCaptchaVerify = useCallback((token: string) => {
    setCaptchaToken(token);
  }, []);

  const handleCaptchaExpire = useCallback(() => {
    setCaptchaToken(null);
  }, []);

  function updateField(field: keyof FormData, value: string | boolean) {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (field in errors) {
      setErrors((prev) => { const next = { ...prev }; delete next[field as keyof FormErrors]; return next; });
    }
  }

  function validate(): FormErrors {
    const errs: FormErrors = {};
    if (!formData.domaine) errs.domaine = "Veuillez sélectionner un domaine";
    if (!formData.objet) errs.objet = "Veuillez sélectionner un objet";
    if (!formData.message.trim()) errs.message = "Le message est requis";
    return errs;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitError("");
    setSubmitSuccess("");

    const validationErrors = validate();
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) return;

    if (!captchaToken) {
      setSubmitError("Veuillez valider le captcha");
      return;
    }

    setIsSubmitting(true);
    try {
      await apiSubmitContact(
        {
          domaine: formData.domaine,
          objet: formData.objet,
          message: formData.message.trim(),
          bloquant: formData.bloquant,
          urgent: formData.urgent,
          captcha_token: captchaToken,
        },
        accessToken,
      );
      setSubmitSuccess("Votre message a été envoyé avec succès. Nous vous répondrons dans les meilleurs délais.");
      setFormData({ domaine: "", objet: "", message: "", bloquant: false, urgent: false });
      setCaptchaToken(null);
    } catch {
      setSubmitError("Erreur lors de l'envoi du message. Veuillez réessayer.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Contactez-nous</h1>
      <p className={styles.subtitle}>Une question ou une suggestion ? Envoyez-nous un message.</p>

      <form className={styles.form} onSubmit={handleSubmit} noValidate>
        {submitError && <div className={styles.errorMessage} role="alert">{submitError}</div>}
        {submitSuccess && <div className={styles.successMessage} role="status">{submitSuccess}</div>}

        <div className={styles.fieldGroup}>
          <label htmlFor="domaine" className={styles.label}>Domaine<span className={styles.required}>*</span></label>
          <select id="domaine" className={`${styles.select} ${errors.domaine ? styles.inputError : ""}`}
            value={formData.domaine} onChange={(e) => updateField("domaine", e.target.value)}
            required aria-invalid={!!errors.domaine} aria-describedby={errors.domaine ? "domaine-error" : undefined}>
            <option value="">— Sélectionnez un domaine —</option>
            {DOMAINES.map((d) => <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>)}
          </select>
          {errors.domaine && <p id="domaine-error" className={styles.fieldError}>{errors.domaine}</p>}
        </div>

        <div className={styles.fieldGroup}>
          <label htmlFor="objet" className={styles.label}>Objet<span className={styles.required}>*</span></label>
          <select id="objet" className={`${styles.select} ${errors.objet ? styles.inputError : ""}`}
            value={formData.objet} onChange={(e) => updateField("objet", e.target.value)}
            required aria-invalid={!!errors.objet} aria-describedby={errors.objet ? "objet-error" : undefined}>
            <option value="">— Sélectionnez un objet —</option>
            {OBJETS.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
          {errors.objet && <p id="objet-error" className={styles.fieldError}>{errors.objet}</p>}
        </div>

        <div className={styles.fieldGroup}>
          <label htmlFor="message" className={styles.label}>Message<span className={styles.required}>*</span></label>
          <textarea id="message" className={`${styles.textarea} ${errors.message ? styles.inputError : ""}`}
            value={formData.message} onChange={(e) => updateField("message", e.target.value)}
            required placeholder="Décrivez votre demande..."
            aria-invalid={!!errors.message} aria-describedby={errors.message ? "message-error" : undefined} />
          {errors.message && <p id="message-error" className={styles.fieldError}>{errors.message}</p>}
        </div>

        <div className={styles.checkboxRow}>
          <label className={styles.checkboxLabel}>
            <input type="checkbox" checked={formData.bloquant}
              onChange={(e) => setFormData((prev) => ({ ...prev, bloquant: e.target.checked }))} />
            Bloquant
          </label>
          <label className={styles.checkboxLabel}>
            <input type="checkbox" checked={formData.urgent}
              onChange={(e) => setFormData((prev) => ({ ...prev, urgent: e.target.checked }))} />
            Urgent
          </label>
        </div>

        <div className={styles.captchaBox}>
          <ReCaptchaWidget onVerify={handleCaptchaVerify} onExpire={handleCaptchaExpire} />
        </div>

        <button type="submit" className={styles.submitBtn} disabled={isSubmitting}>
          {isSubmitting ? "Envoi en cours…" : "Envoyer"}
        </button>
      </form>
    </div>
  );
}
