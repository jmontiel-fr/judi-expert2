"use client";

import { useState, useCallback, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import ReCaptchaWidget from "@/components/ReCaptchaWidget";
import styles from "./connexion.module.css";

interface FormErrors {
  email?: string;
  password?: string;
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
    } catch {
      // Uniform error message — never reveal if email or password is wrong (Exigence 14.3)
      setSubmitError("Identifiants invalides");
    } finally {
      setIsSubmitting(false);
    }
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
