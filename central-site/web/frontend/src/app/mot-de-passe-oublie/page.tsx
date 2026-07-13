"use client";

import { useState, useCallback, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import ReCaptchaWidget from "@/components/ReCaptchaWidget";
import styles from "./forgot.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function ForgotPasswordPage() {
  const [step, setStep] = useState<"request" | "confirm">("request");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);
  const router = useRouter();

  const handleCaptchaVerify = useCallback((token: string) => {
    setCaptchaToken(token);
  }, []);

  const handleCaptchaExpire = useCallback(() => {
    setCaptchaToken(null);
  }, []);

  async function handleRequestCode(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError("Veuillez saisir une adresse email valide");
      return;
    }
    if (!captchaToken) {
      setError("Veuillez valider le captcha");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), captcha_token: captchaToken }),
      });
      if (!res.ok) throw new Error();
      setStep("confirm");
      setSuccess("Un code de vérification a été envoyé à votre adresse email.");
    } catch {
      // Message identique pour ne pas révéler si l'email existe
      setStep("confirm");
      setSuccess("Un code de vérification a été envoyé à votre adresse email.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleConfirmReset(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!code.trim()) {
      setError("Veuillez saisir le code reçu par email");
      return;
    }
    if (newPassword.length < 8) {
      setError("Le mot de passe doit contenir au moins 8 caractères");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Les mots de passe ne correspondent pas");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/confirm-forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          code: code.trim(),
          new_password: newPassword,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        setError(data?.detail || "Erreur lors de la réinitialisation. Veuillez réessayer.");
        return;
      }

      setSuccess("Mot de passe réinitialisé avec succès ! Redirection...");
      setCode("");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => router.push("/connexion"), 2000);
    } catch {
      setError("Erreur lors de la réinitialisation. Veuillez réessayer.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (step === "request") {
    return (
      <div className={styles.container}>
        <h1 className={styles.title}>Mot de passe oublié</h1>
        <p className={styles.subtitle}>
          Saisissez votre email pour recevoir un code de réinitialisation
        </p>

        <form className={styles.form} onSubmit={handleRequestCode} noValidate>
          {error && <div className={styles.errorMessage} role="alert">{error}</div>}

          <div className={styles.fieldGroup}>
            <label htmlFor="email" className={styles.label}>Email</label>
            <input id="email" type="email" className={styles.input}
              value={email} onChange={(e) => setEmail(e.target.value)}
              required autoComplete="email" placeholder="votre@email.fr" />
          </div>

          <div className={styles.captchaBox}>
            <ReCaptchaWidget onVerify={handleCaptchaVerify} onExpire={handleCaptchaExpire} />
          </div>

          <button type="submit" className={styles.submitBtn} disabled={isSubmitting}>
            {isSubmitting ? "Envoi en cours…" : "Envoyer le code"}
          </button>
        </form>

        <p className={styles.backLink}>
          <Link href="/connexion">← Retour à la connexion</Link>
        </p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Réinitialisation du mot de passe</h1>
      <p className={styles.subtitle}>
        Saisissez le code reçu par email et votre nouveau mot de passe
      </p>

      <form className={styles.form} onSubmit={handleConfirmReset} noValidate>
        {error && <div className={styles.errorMessage} role="alert">{error}</div>}
        {success && <div className={styles.successMessage} role="status">{success}</div>}

        <div className={styles.fieldGroup}>
          <label htmlFor="code" className={styles.label}>Code de vérification</label>
          <input id="code" type="text" className={styles.input}
            value={code} onChange={(e) => setCode(e.target.value)}
            required autoComplete="one-time-code" placeholder="123456"
            inputMode="numeric" />
        </div>

        <div className={styles.fieldGroup}>
          <label htmlFor="new-password" className={styles.label}>Nouveau mot de passe</label>
          <input id="new-password" type="password" className={styles.input}
            value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
            required autoComplete="new-password"
            placeholder="Min. 8 caractères, majuscule, chiffre, spécial" />
        </div>

        <div className={styles.fieldGroup}>
          <label htmlFor="confirm-password" className={styles.label}>Confirmer le mot de passe</label>
          <input id="confirm-password" type="password" className={styles.input}
            value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
            required autoComplete="new-password" placeholder="Confirmez votre mot de passe" />
        </div>

        <button type="submit" className={styles.submitBtn} disabled={isSubmitting}>
          {isSubmitting ? "Réinitialisation…" : "Réinitialiser le mot de passe"}
        </button>
      </form>

      <p className={styles.backLink}>
        <Link href="/connexion">← Retour à la connexion</Link>
      </p>
    </div>
  );
}
