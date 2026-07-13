"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import styles from "./setup.module.css";
import { authApi, configApi, getErrorMessage } from "@/lib/api";

const DOMAINES = [
  { value: "psychologie", label: "Psychologie" },
  { value: "psychiatrie", label: "Psychiatrie" },
  { value: "medecine_legale", label: "Médecine légale" },
  { value: "batiment", label: "Bâtiment" },
  { value: "comptabilite", label: "Comptabilité" },
];

export default function SetupPage() {
  const router = useRouter();

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [domaine, setDomaine] = useState("");
  const [ragAvailable, setRagAvailable] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    checkRagStatus();
  }, []);

  async function checkRagStatus() {
    try {
      const data = await configApi.getRagVersions();
      const versions = data.versions ?? [];
      setRagAvailable(versions.length > 0);
    } catch {
      setRagAvailable(false);
    }
  }

  function validate(): string | null {
    if (!password || password.length < 4) {
      return "Le mot de passe doit contenir au moins 4 caractères.";
    }
    if (password !== confirmPassword) {
      return "Les mots de passe ne correspondent pas.";
    }
    if (!domaine) {
      return "Veuillez sélectionner un domaine d'expertise.";
    }
    return null;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    try {
      await authApi.setup(password, domaine);
      setSuccess(true);

      if (ragAvailable === false) {
        setTimeout(() => router.push("/config"), 2000);
      } else {
        setTimeout(() => router.push("/"), 2000);
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err, "Une erreur est survenue lors de la configuration."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1 className={styles.title}>Configuration initiale</h1>
        <p className={styles.subtitle}>
          Définissez votre mot de passe local et sélectionnez votre domaine
          d&apos;expertise pour commencer.
        </p>

        {ragAvailable === false && (
          <div className={styles.warning} role="alert">
            <span className={styles.warningIcon} aria-hidden="true">⚠</span>
            <div>
              <strong>Module RAG non configuré</strong>
              <p>
                L&apos;accès aux fonctionnalités d&apos;expertise sera bloqué
                tant que le module RAG n&apos;est pas installé. Après la
                configuration initiale, vous serez redirigé vers la page de
                configuration pour installer le module RAG.
              </p>
            </div>
          </div>
        )}

        {success ? (
          <div className={styles.successMessage} role="status">
            <span className={styles.successIcon} aria-hidden="true">✓</span>
            <div>
              <strong>Configuration réussie !</strong>
              <p>
                {ragAvailable === false
                  ? "Redirection vers la page de configuration RAG…"
                  : "Redirection vers la page d'accueil…"}
              </p>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className={styles.form} noValidate>
            <div className={styles.field}>
              <label htmlFor="password" className={styles.label}>
                Mot de passe
              </label>
              <input
                id="password"
                type="password"
                className={styles.input}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimum 4 caractères"
                minLength={4}
                required
                autoComplete="new-password"
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="confirmPassword" className={styles.label}>
                Confirmer le mot de passe
              </label>
              <input
                id="confirmPassword"
                type="password"
                className={styles.input}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Retapez le mot de passe"
                required
                autoComplete="new-password"
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="domaine" className={styles.label}>
                Domaine d&apos;expertise
              </label>
              <select
                id="domaine"
                className={styles.select}
                value={domaine}
                onChange={(e) => setDomaine(e.target.value)}
                required
              >
                <option value="" disabled>
                  — Sélectionnez un domaine —
                </option>
                {DOMAINES.map((d) => (
                  <option key={d.value} value={d.value}>
                    {d.label}
                  </option>
                ))}
              </select>
            </div>

            {error && (
              <p className={styles.error} role="alert">
                {error}
              </p>
            )}

            <button
              type="submit"
              className={styles.button}
              disabled={loading}
            >
              {loading ? "Configuration en cours…" : "Configurer"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
