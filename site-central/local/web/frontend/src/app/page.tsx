"use client";

import { useState, useEffect, useCallback, FormEvent } from "react";
import Link from "next/link";
import styles from "./home.module.css";
import {
  dossiersApi,
  getErrorMessage,
  type DossierListItem,
} from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

/* ------------------------------------------------------------------ */
/* Main component                                                      */
/* ------------------------------------------------------------------ */

export default function HomePage() {
  const [dossiers, setDossiers] = useState<DossierListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  /* Modal state */
  const [showModal, setShowModal] = useState(false);
  const [nom, setNom] = useState("");
  const [ticketId, setTicketId] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  /* ---------------------------------------------------------------- */
  /* Data fetching                                                     */
  /* ---------------------------------------------------------------- */

  const fetchDossiers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await dossiersApi.list();
      setDossiers(data.dossiers ?? []);
    } catch (err: unknown) {
      setError(getErrorMessage(err, "Impossible de charger les dossiers."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDossiers();
  }, [fetchDossiers]);

  /* ---------------------------------------------------------------- */
  /* Create dossier                                                    */
  /* ---------------------------------------------------------------- */

  function openModal() {
    setNom("");
    setTicketId("");
    setCreateError("");
    setShowModal(true);
  }

  function closeModal() {
    if (!creating) setShowModal(false);
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreateError("");

    if (!nom.trim()) {
      setCreateError("Le nom du dossier est requis.");
      return;
    }
    if (!ticketId.trim()) {
      setCreateError("Le code du ticket est requis.");
      return;
    }

    setCreating(true);
    try {
      await dossiersApi.create(nom.trim(), ticketId.trim());
      setShowModal(false);
      fetchDossiers();
    } catch (err: unknown) {
      setCreateError(getErrorMessage(err, "Erreur lors de la création du dossier."));
    } finally {
      setCreating(false);
    }
  }

  /* ---------------------------------------------------------------- */
  /* Render                                                            */
  /* ---------------------------------------------------------------- */

  return (
    <div className={styles.container}>
      {/* Page header */}
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Dossiers</h1>
          <p className={styles.subtitle}>
            Gérez vos dossiers d&apos;expertise judiciaire.
          </p>
        </div>
        <button
          className={styles.createButton}
          onClick={openModal}
          type="button"
        >
          <span className={styles.createButtonIcon} aria-hidden="true">
            +
          </span>
          Nouveau dossier
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className={styles.loading}>
          <span className={styles.spinner} aria-hidden="true" />
          Chargement des dossiers…
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      {/* Empty state */}
      {!loading && !error && dossiers.length === 0 && (
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon} aria-hidden="true">
            📂
          </div>
          <p className={styles.emptyTitle}>Aucun dossier</p>
          <p className={styles.emptyText}>
            Créez votre premier dossier d&apos;expertise en cliquant sur
            &quot;Nouveau dossier&quot;.
          </p>
        </div>
      )}

      {/* Dossier list */}
      {!loading && !error && dossiers.length > 0 && (
        <div className={styles.dossierList} role="list">
          {dossiers.map((d) => (
            <Link
              key={d.id}
              href={`/dossier/${d.id}`}
              className={styles.dossierCard}
              role="listitem"
            >
              <div className={styles.dossierInfo}>
                <div className={styles.dossierName}>{d.nom}</div>
                <div className={styles.dossierMeta}>
                  <span
                    className={`${styles.badge} ${styles.badgeDomaine}`}
                  >
                    {d.domaine}
                  </span>
                  <span
                    className={`${styles.badge} ${
                      d.statut === "actif"
                        ? styles.badgeActif
                        : styles.badgeArchive
                    }`}
                  >
                    {d.statut === "actif" ? "Actif" : "Archivé"}
                  </span>
                  <span>{formatDate(d.created_at)}</span>
                </div>
              </div>
              {d.steps && d.steps.length > 0 && (
                <div
                  className={styles.stepProgress}
                  title={`Étapes : ${d.steps.map((s) => s.statut).join(", ")}`}
                  aria-label={`Progression : ${d.steps.filter((s) => s.statut === "valide").length}/${d.steps.length} étapes validées`}
                >
                  {d.steps
                    .sort((a, b) => a.step_number - b.step_number)
                    .map((s) => (
                      <span
                        key={s.step_number}
                        className={`${styles.stepDot} ${
                          s.statut === "valide"
                            ? styles.stepDotValide
                            : s.statut === "realise"
                              ? styles.stepDotRealise
                              : styles.stepDotInitial
                        }`}
                      />
                    ))}
                </div>
              )}
            </Link>
          ))}
        </div>
      )}

      {/* Create dossier modal */}
      {showModal && (
        <div
          className={styles.overlay}
          onClick={closeModal}
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
        >
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h2 className={styles.modalTitle} id="modal-title">
              Nouveau dossier
            </h2>
            <p className={styles.modalSubtitle}>
              Saisissez le nom du dossier et le code du ticket d&apos;expertise.
            </p>

            <form onSubmit={handleCreate} className={styles.form} noValidate>
              <div className={styles.field}>
                <label htmlFor="dossier-nom" className={styles.label}>
                  Nom du dossier
                </label>
                <input
                  id="dossier-nom"
                  type="text"
                  className={styles.input}
                  value={nom}
                  onChange={(e) => setNom(e.target.value)}
                  placeholder="Ex : Expertise Dupont 2026"
                  required
                  autoFocus
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="dossier-ticket" className={styles.label}>
                  Code du ticket
                </label>
                <input
                  id="dossier-ticket"
                  type="text"
                  className={styles.input}
                  value={ticketId}
                  onChange={(e) => setTicketId(e.target.value)}
                  placeholder="Ex : TKT-2026-ABCD"
                  required
                />
              </div>

              {createError && (
                <p className={styles.error} role="alert">
                  {createError}
                </p>
              )}

              <div className={styles.modalActions}>
                <button
                  type="button"
                  className={`${styles.button} ${styles.buttonSecondary}`}
                  onClick={closeModal}
                  disabled={creating}
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  className={styles.button}
                  disabled={creating}
                >
                  {creating ? "Création…" : "Créer le dossier"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
