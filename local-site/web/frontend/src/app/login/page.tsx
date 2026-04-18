"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import styles from "./login.module.css";
import { authApi, getErrorMessage } from "@/lib/api";

const SITE_CENTRAL_URL = process.env.NEXT_PUBLIC_SITE_CENTRAL_URL || "http://localhost:3001";

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Pré-remplir l'email si déjà connu (connexion précédente)
  useEffect(() => {
    authApi.info().then((data) => {
      if (data.email) setEmail(data.email);
    }).catch(() => {});
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (!email.trim()) {
      setError("Veuillez saisir votre email.");
      return;
    }
    if (!password) {
      setError("Veuillez saisir votre mot de passe.");
      return;
    }

    setLoading(true);
    try {
      await authApi.login(email.trim(), password);
      router.push("/");
    } catch (err: unknown) {
      setError(getErrorMessage(err, "Une erreur est survenue lors de la connexion."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1 className={styles.title}>Connexion</h1>

        <div className={styles.notice}>
          Utilisez les identifiants de votre compte sur le{" "}
          <a
            href={`${SITE_CENTRAL_URL}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            site central Judi-Expert ↗
          </a>.
          Pas encore inscrit ?{" "}
          <a
            href={`${SITE_CENTRAL_URL}/inscription`}
            target="_blank"
            rel="noopener noreferrer"
          >
            Créer un compte ↗
          </a>
        </div>

        <form onSubmit={handleSubmit} className={styles.form} noValidate>
          <div className={styles.field}>
            <label htmlFor="email" className={styles.label}>
              Email
            </label>
            <input
              id="email"
              type="email"
              className={styles.input}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="votre@email.fr"
              required
              autoComplete="email"
              autoFocus
            />
          </div>

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
              placeholder="Votre mot de passe"
              required
              autoComplete="current-password"
            />
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
            {loading ? "Connexion en cours…" : "Se connecter"}
          </button>
        </form>
      </div>
    </div>
  );
}
