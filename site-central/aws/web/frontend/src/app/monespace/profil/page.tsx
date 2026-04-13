"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { apiChangePassword, apiDeleteAccount, ApiError } from "@/lib/api";
import styles from "./profil.module.css";

export default function ProfilPage() {
  const { user, accessToken, logout } = useAuth();
  const router = useRouter();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pwdError, setPwdError] = useState("");
  const [pwdSuccess, setPwdSuccess] = useState("");
  const [isChangingPwd, setIsChangingPwd] = useState(false);

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handlePasswordSubmit(e: FormEvent) {
    e.preventDefault();
    setPwdError("");
    setPwdSuccess("");

    if (!currentPassword) { setPwdError("Le mot de passe actuel est requis"); return; }
    if (!newPassword) { setPwdError("Le nouveau mot de passe est requis"); return; }
    if (newPassword.length < 8) { setPwdError("Le nouveau mot de passe doit contenir au moins 8 caractères"); return; }
    if (newPassword !== confirmPassword) { setPwdError("Les mots de passe ne correspondent pas"); return; }

    setIsChangingPwd(true);
    try {
      if (!accessToken) throw new Error("Non authentifié");
      await apiChangePassword(accessToken, currentPassword, newPassword);
      setPwdSuccess("Mot de passe modifié avec succès");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      if (err instanceof ApiError) {
        setPwdError(err.message);
      } else {
        setPwdError("Erreur lors du changement de mot de passe");
      }
    } finally {
      setIsChangingPwd(false);
    }
  }

  async function handleDeleteAccount() {
    setIsDeleting(true);
    try {
      if (!accessToken) throw new Error("Non authentifié");
      await apiDeleteAccount(accessToken);
      await logout();
      router.push("/");
    } catch {
      setShowDeleteConfirm(false);
    } finally {
      setIsDeleting(false);
    }
  }

  if (!user) return null;

  return (
    <>
      {/* Profile Info */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Informations du profil</h2>
        <div className={styles.infoGrid}>
          <span className={styles.infoLabel}>Email</span>
          <span className={styles.infoValue} style={{ color: "var(--color-text-muted)", fontStyle: "italic" }}>{user.email} (non modifiable)</span>
          <span className={styles.infoLabel}>Nom</span>
          <span className={styles.infoValue}>{user.nom}</span>
          <span className={styles.infoLabel}>Prénom</span>
          <span className={styles.infoValue}>{user.prenom}</span>
          <span className={styles.infoLabel}>Adresse</span>
          <span className={styles.infoValue}>{user.adresse}</span>
          <span className={styles.infoLabel}>Ville</span>
          <span className={styles.infoValue}>{user.ville || "—"}</span>
          <span className={styles.infoLabel}>Code postal</span>
          <span className={styles.infoValue}>{user.code_postal || "—"}</span>
          <span className={styles.infoLabel}>Téléphone</span>
          <span className={styles.infoValue}>{user.telephone || "—"}</span>
          <span className={styles.infoLabel}>Domaine</span>
          <span className={styles.infoValue}>{user.domaine}</span>
        </div>
      </section>

      {/* Change Password */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Changer le mot de passe</h2>
        {pwdSuccess && <div className={styles.successMessage} role="status">{pwdSuccess}</div>}
        {pwdError && <div className={styles.errorMessage} role="alert">{pwdError}</div>}

        <form onSubmit={handlePasswordSubmit} noValidate>
          <div className={styles.fieldGroup}>
            <label htmlFor="currentPassword" className={styles.label}>
              Mot de passe actuel<span className={styles.required}>*</span>
            </label>
            <input id="currentPassword" type="password" className={styles.input}
              value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="current-password" />
          </div>
          <div className={styles.fieldGroup}>
            <label htmlFor="newPassword" className={styles.label}>
              Nouveau mot de passe<span className={styles.required}>*</span>
            </label>
            <input id="newPassword" type="password" className={styles.input}
              value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password" />
          </div>
          <div className={styles.fieldGroup}>
            <label htmlFor="confirmPassword" className={styles.label}>
              Confirmer le nouveau mot de passe<span className={styles.required}>*</span>
            </label>
            <input id="confirmPassword" type="password" className={styles.input}
              value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password" />
          </div>
          <button type="submit" className={styles.submitBtn} disabled={isChangingPwd}>
            {isChangingPwd ? "Modification…" : "Modifier le mot de passe"}
          </button>
        </form>
      </section>

      {/* Delete Account */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Supprimer le compte</h2>
        <p style={{ fontSize: "0.9rem", color: "var(--color-text-muted)", marginBottom: 16 }}>
          Cette action est irréversible. Toutes vos données seront supprimées.
        </p>
        <button type="button" className={styles.dangerBtn} onClick={() => setShowDeleteConfirm(true)}>
          Supprimer mon compte
        </button>
      </section>

      {showDeleteConfirm && (
        <div className={styles.confirmOverlay} onClick={() => setShowDeleteConfirm(false)}
          role="dialog" aria-modal="true" aria-labelledby="delete-dialog-title">
          <div className={styles.confirmDialog} onClick={(e) => e.stopPropagation()}>
            <h3 id="delete-dialog-title" className={styles.confirmTitle}>Confirmer la suppression</h3>
            <p className={styles.confirmText}>
              Êtes-vous sûr de vouloir supprimer votre compte ? Cette action est définitive et toutes vos données seront perdues.
            </p>
            <div className={styles.confirmActions}>
              <button type="button" className={styles.cancelBtn} onClick={() => setShowDeleteConfirm(false)}>Annuler</button>
              <button type="button" className={styles.dangerBtn} disabled={isDeleting} onClick={handleDeleteAccount}>
                {isDeleting ? "Suppression…" : "Confirmer la suppression"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
