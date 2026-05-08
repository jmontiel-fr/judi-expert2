"use client";

import { useState, useCallback, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { NewPasswordRequiredError, apiSetNewPassword } from "@/lib/api";
import ReCaptchaWidget from "@/components/ReCaptchaWidget";
import styles from "./connexion.module.css";

interface FormErrors {
  email?: string;
  password?: string;
  newPassword?: string;
  confirmPassword?: string;
}

export default function ConnexionPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // New password challenge state
  const [needsNewPassword, setNeedsNewPassword] = useState(false);
  const [cognitoSession, setCognitoSession] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const handleCaptchaVerify = useCallback((token: string) => {
    setCaptchaToken(token);
  }, []);

  const handleCaptchaExpire = useCallback(() => {
    setCaptchaToken(null);
  }, []);

  function validate(): FormErrors {
    const errs: FormErrors = {};
    if (!email.trim()) {
      errs.email = "L'email est requis";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errs.email = "Format d'email invalide";
    }
    if (!password) {
      errs.password = "Le mot de passe est requis";
    }
    return errs;
  }

  function validateNewPassword(): FormErrors {
    const errs: FormErrors = {};
    if (!newPassword) {
      errs.newPassword = "Le nouveau mot de passe est requis";
    } else if (newPassword.length < 8) {
      errs.newPassword = "Minimum 8 caractères";
    }
    if (newPassword !== confirmPassword) {
      errs.confirmPassword = "Les mots de passe ne correspondent pas";
    }
    return errs;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitError("");

    const validationErrors = validate();
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) return;

    if (!captchaToken) {
      setSubmitError("Veuillez valider le captcha");
      return;
    }

    setIsSubmitting(true);
    try {
      await login(email.trim(), password, captchaToken);
      router.push("/");
    } catch (err) {
      if (err instanceof NewPasswordRequiredError) {
        setCognitoSession(err.session);
        setNeedsNewPassword(true);
        setSubmitError("");
      } else if (err instanceof Error && err.message === "USER_NOT_CONFIRMED") {
        router.push(`/confirmation?email=${encodeURIComponent(email.trim())}`);
      } else {
        setSubmitError("Identifiants invalides");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleNewPasswordSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitError("");

    const validationErrors = validateNewPassword();
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) return;

    setIsSubmitting(true);
    try {
      await apiSetNewPassword(email.trim(), newPassword, cognitoSession);
      // Re-login with new password
      await login(email.trim(), newPassword, captchaToken || "");
      router.push("/");
    } catch {
      setSubmitError("Impossible de changer le mot de passe. Veuillez réessayer.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (needsNewPassword) {
    return (
      <div className={styles.container}>
        <h1 className={styles.title}>Changement de mot de passe</h1>
        <p className={styles.subtitle}>Vous devez définir un nouveau mot de passe pour continuer.</p>

        <form className={styles.form} onSubmit={handleNewPasswordSubmit} noValidate>
          {submitError && (
            <div className={styles.errorMessage} role="alert">{submitError}</div>
          )}

          <div className={styles.fieldGroup}>
            <label htmlFor="newPassword" className={styles.label}>
              Nouveau mot de passe<span className={styles.required}>*</span>
            </label>
            <input id="newPassword" type="password"
              className={`${styles.input} ${errors.newPassword ? styles.inputError : ""}`}
              value={newPassword}
              onChange={(e) => { setNewPassword(e.target.value); setErrors((p) => ({ ...p, newPassword: undefined })); }}
              required autoComplete="new-password" aria-invalid={!!errors.newPassword}
              aria-describedby={errors.newPassword ? "new-password-error" : undefined} />
            {errors.newPassword && <p id="new-password-error" className={styles.fieldError}>{errors.newPassword}</p>}
          </div>

          <div className={styles.fieldGroup}>
            <label htmlFor="confirmPassword" className={styles.label}>
              Confirmer le mot de passe<span className={styles.required}>*</span>
            </label>
            <input id="confirmPassword" type="password"
              className={`${styles.input} ${errors.confirmPassword ? styles.inputError : ""}`}
              value={confirmPassword}
              onChange={(e) => { setConfirmPassword(e.target.value); setErrors((p) => ({ ...p, confirmPassword: undefined })); }}
              required autoComplete="new-password" aria-invalid={!!errors.confirmPassword}
              aria-describedby={errors.confirmPassword ? "confirm-password-error" : undefined} />
            {errors.confirmPassword && <p id="confirm-password-error" className={styles.fieldError}>{errors.confirmPassword}</p>}
          </div>

          <button type="submit" className={styles.submitBtn} disabled={isSubmitting}>
            {isSubmitting ? "Enregistrement…" : "Définir le nouveau mot de passe"}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Connexion</h1>
      <p className={styles.subtitle}>Accédez à votre espace Judi-expert</p>

      <form className={styles.form} onSubmit={handleSubmit} noValidate>
        {submitError && (
          <div className={styles.errorMessage} role="alert">{submitError}</div>
        )}

        <div className={styles.fieldGroup}>
          <label htmlFor="email" className={styles.label}>
            Email<span className={styles.required}>*</span>
          </label>
          <input id="email" type="email"
            className={`${styles.input} ${errors.email ? styles.inputError : ""}`}
            value={email}
            onChange={(e) => { setEmail(e.target.value); if (errors.email) setErrors((p) => ({ ...p, email: undefined })); }}
            required autoComplete="email" aria-invalid={!!errors.email}
            aria-describedby={errors.email ? "email-error" : undefined} />
          {errors.email && <p id="email-error" className={styles.fieldError}>{errors.email}</p>}
        </div>

        <div className={styles.fieldGroup}>
          <label htmlFor="password" className={styles.label}>
            Mot de passe<span className={styles.required}>*</span>
          </label>
          <input id="password" type="password"
            className={`${styles.input} ${errors.password ? styles.inputError : ""}`}
            value={password}
            onChange={(e) => { setPassword(e.target.value); if (errors.password) setErrors((p) => ({ ...p, password: undefined })); }}
            required autoComplete="current-password" aria-invalid={!!errors.password}
            aria-describedby={errors.password ? "password-error" : undefined} />
          {errors.password && <p id="password-error" className={styles.fieldError}>{errors.password}</p>}
        </div>

        <div className={styles.captchaBox}>
          <ReCaptchaWidget onVerify={handleCaptchaVerify} onExpire={handleCaptchaExpire} />
        </div>

        <button type="submit" className={styles.submitBtn} disabled={isSubmitting}>
          {isSubmitting ? "Connexion en cours…" : "Se connecter"}
        </button>

        <p className={styles.forgotPassword}>
          <Link href="/mot-de-passe-oublie">Mot de passe oublié ?</Link>
        </p>
      </form>

      <p className={styles.registerLink}>
        Pas encore de compte ? <Link href="/inscription">S&apos;inscrire</Link>
      </p>
    </div>
  );
}
