"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import styles from "./forgot.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError("Veuillez saisir une adresse email valide");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });
      if (!res.ok) throw new Error();
      setSuccess(
        "Si un compte existe avec cet email, un lien de réinitialisation a été envoyé."
      );
      setEmail("");
    } catch {
      // Message identique pour ne pas révéler si l'email existe
      setSuccess(
        "Si un compte existe avec cet email, un lien de réinitialisation a été envoyé."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Mot de passe oublié</h1>
      <p className={styles.subtitle}>
        Saisissez votre email pour recevoir un lien de réinitialisation
      </p>

      <form className={styles.form} onSubmit={handleSubmit} noValidate>
        {error && <div className={styles.errorMessage} role="alert">{error}</div>}
        {success && <div className={styles.successMessage} role="status">{success}</div>}

        <div className={styles.fieldGroup}>
          <label htmlFor="email" className={styles.label}>Email</label>
          <input id="email" type="email" className={styles.input}
            value={email} onChange={(e) => setEmail(e.target.value)}
            required autoComplete="email" placeholder="votre@email.fr" />
        </div>

        <button type="submit" className={styles.submitBtn} disabled={isSubmitting}>
          {isSubmitting ? "Envoi en cours…" : "Envoyer le lien"}
        </button>
      </form>

      <p className={styles.backLink}>
        <Link href="/connexion">← Retour à la connexion</Link>
      </p>
    </div>
  );
}
