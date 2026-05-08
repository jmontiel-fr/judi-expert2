"use client";

import { useState, useEffect, type FormEvent, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { apiConfirmSignUp, apiResendCode, ApiError } from "@/lib/api";
import styles from "./confirmation.module.css";

function ConfirmationForm() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [resendMsg, setResendMsg] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const emailParam = searchParams.get("email");
    if (emailParam) setEmail(emailParam);
  }, [searchParams]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!email.trim()) { setError("L'email est requis"); return; }
    if (!code.trim()) { setError("Le code de confirmation est requis"); return; }

    setIsSubmitting(true);
    try {
      await apiConfirmSignUp(email.trim(), code.trim());
      setSuccess("Compte confirmé avec succès !");
      setTimeout(() => router.push("/connexion"), 2000);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Erreur lors de la confirmation. Veuillez réessayer.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleResend() {
    if (!email.trim()) { setError("Saisissez votre email pour renvoyer le code"); return; }
    setResendMsg("");
    setError("");
    try {
      await apiResendCode(email.trim());
      setResendMsg("Un nouveau code a été envoyé à votre adresse email.");
    } catch {
      setResendMsg("Impossible de renvoyer le code. Veuillez réessayer.");
    }
  }

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Confirmation du compte</h1>
      <p className={styles.subtitle}>
        Saisissez le code de confirmation reçu par email pour activer votre compte.
      </p>

      <form className={styles.form} onSubmit={handleSubmit} noValidate>
        {error && <div className={styles.errorMessage} role="alert">{error}</div>}
        {success && <div className={styles.successMessage} role="status">{success}</div>}
        {resendMsg && <div className={styles.infoMessage}>{resendMsg}</div>}

        <div className={styles.fieldGroup}>
          <label htmlFor="email" className={styles.label}>
            Email<span className={styles.required}>*</span>
          </label>
          <input
            id="email"
            type="email"
            className={styles.input}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            placeholder="votre@email.fr"
          />
        </div>

        <div className={styles.fieldGroup}>
          <label htmlFor="code" className={styles.label}>
            Code de confirmation<span className={styles.required}>*</span>
          </label>
          <input
            id="code"
            type="text"
            className={styles.input}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            required
            autoComplete="one-time-code"
            placeholder="123456"
            maxLength={6}
          />
        </div>

        <button type="submit" className={styles.submitBtn} disabled={isSubmitting}>
          {isSubmitting ? "Vérification…" : "Confirmer mon compte"}
        </button>

        <button type="button" className={styles.resendBtn} onClick={handleResend}>
          Renvoyer le code
        </button>
      </form>

      <p className={styles.loginLink}>
        Déjà confirmé ? <Link href="/connexion">Se connecter</Link>
      </p>
    </div>
  );
}

export default function ConfirmationPage() {
  return (
    <Suspense fallback={<div style={{ textAlign: "center", padding: 40 }}>Chargement…</div>}>
      <ConfirmationForm />
    </Suspense>
  );
}
