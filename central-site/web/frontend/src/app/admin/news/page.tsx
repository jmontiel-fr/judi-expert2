"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import {
  apiAdminListNews,
  apiAdminCreateNews,
  apiAdminGetNews,
  apiAdminUpdateNews,
  apiAdminToggleVisibility,
  apiAdminDeleteNews,
  type NewsItem,
  type NewsDetail,
} from "@/lib/api";
import styles from "./admin-news.module.css";

type Mode = "list" | "create" | "view" | "edit";

export default function AdminNewsPage() {
  const { accessToken, isAdmin } = useAuth();
  const router = useRouter();

  const [mode, setMode] = useState<Mode>("list");
  const [newsList, setNewsList] = useState<NewsItem[]>([]);
  const [selected, setSelected] = useState<NewsDetail | null>(null);
  const [titre, setTitre] = useState("");
  const [contenu, setContenu] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isAdmin) {
      router.push("/");
      return;
    }
    loadNews();
  }, [accessToken, isAdmin]);

  async function loadNews() {
    if (!accessToken) return;
    try {
      const data = await apiAdminListNews(accessToken);
      setNewsList(data);
    } catch {
      setError("Erreur lors du chargement des news");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!accessToken || !titre.trim() || !contenu.trim()) return;
    try {
      await apiAdminCreateNews(accessToken, {
        titre: titre.trim(),
        contenu: contenu.trim(),
      });
      setTitre("");
      setContenu("");
      setMode("list");
      await loadNews();
    } catch {
      setError("Erreur lors de la création");
    }
  }

  async function handleView(id: number) {
    if (!accessToken) return;
    try {
      const detail = await apiAdminGetNews(accessToken, id);
      setSelected(detail);
      setMode("view");
    } catch {
      setError("Erreur lors du chargement");
    }
  }

  async function handleEdit(id: number) {
    if (!accessToken) return;
    try {
      const detail = await apiAdminGetNews(accessToken, id);
      setSelected(detail);
      setTitre(detail.titre);
      setContenu(detail.contenu);
      setMode("edit");
    } catch {
      setError("Erreur lors du chargement");
    }
  }

  async function handleSaveEdit(e: FormEvent) {
    e.preventDefault();
    if (!accessToken || !selected) return;
    try {
      await apiAdminUpdateNews(accessToken, selected.id, {
        titre: titre.trim(),
        contenu: contenu.trim(),
      });
      setMode("list");
      setSelected(null);
      setTitre("");
      setContenu("");
      await loadNews();
    } catch {
      setError("Erreur lors de la mise à jour");
    }
  }

  async function handleToggleVisibility(id: number) {
    if (!accessToken) return;
    try {
      await apiAdminToggleVisibility(accessToken, id);
      await loadNews();
    } catch {
      setError("Erreur lors du changement de visibilité");
    }
  }

  async function handleDelete(id: number) {
    if (!accessToken) return;
    if (!confirm("Supprimer cette news ?")) return;
    try {
      await apiAdminDeleteNews(accessToken, id);
      await loadNews();
    } catch {
      setError("Erreur lors de la suppression");
    }
  }

  if (loading) return <div className={styles.container}><p>Chargement...</p></div>;

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Gestion des News</h1>
      {error && <div className={styles.errorMsg}>{error}</div>}

      {mode === "list" && (
        <>
          <button type="button" className={styles.addBtn} onClick={() => { setMode("create"); setError(""); }}>
            + Ajouter une News
          </button>
          {newsList.length === 0 && <p className={styles.empty}>Aucune news.</p>}
          <div className={styles.list}>
            {newsList.map((n) => (
              <div key={n.id} className={styles.newsRow}>
                <span className={styles.newsDate}>
                  {new Date(n.created_at).toLocaleDateString("fr-FR")}
                </span>
                <span className={styles.newsTitre}>{n.titre}</span>
                <span className={n.visible ? styles.badgeVisible : styles.badgeHidden}>
                  {n.visible ? "Visible" : "Masqué"}
                </span>
                <div className={styles.actions}>
                  <button type="button" className={styles.actionBtn} onClick={() => handleView(n.id)}>Voir</button>
                  <button type="button" className={styles.actionBtn} onClick={() => handleEdit(n.id)}>Modifier</button>
                  <button type="button" className={styles.actionBtn} onClick={() => handleToggleVisibility(n.id)}>
                    {n.visible ? "Masquer" : "Rendre visible"}
                  </button>
                  <button type="button" className={styles.deleteBtn} onClick={() => handleDelete(n.id)}>Supprimer</button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {mode === "view" && selected && (
        <div className={styles.detailCard}>
          <button type="button" className={styles.backBtn} onClick={() => { setMode("list"); setSelected(null); }}>
            ← Retour
          </button>
          <h2 className={styles.detailTitle}>{selected.titre}</h2>
          <p className={styles.detailDate}>{new Date(selected.created_at).toLocaleDateString("fr-FR")}</p>
          <div className={styles.detailContent}>{selected.contenu}</div>
        </div>
      )}

      {(mode === "create" || mode === "edit") && (
        <form className={styles.form} onSubmit={mode === "create" ? handleCreate : handleSaveEdit}>
          <button type="button" className={styles.backBtn} onClick={() => { setMode("list"); setSelected(null); setTitre(""); setContenu(""); }}>
            ← Retour
          </button>
          <h2 className={styles.formTitle}>{mode === "create" ? "Nouvelle News" : "Modifier la News"}</h2>
          <div className={styles.fieldGroup}>
            <label htmlFor="titre" className={styles.label}>Titre</label>
            <input id="titre" type="text" className={styles.input} value={titre}
              onChange={(e) => setTitre(e.target.value)} required />
          </div>
          <div className={styles.fieldGroup}>
            <label htmlFor="contenu" className={styles.label}>Contenu</label>
            <textarea id="contenu" className={styles.textarea} value={contenu}
              onChange={(e) => setContenu(e.target.value)} required rows={10} />
          </div>
          <button type="submit" className={styles.submitBtn}>
            {mode === "create" ? "Créer" : "Enregistrer"}
          </button>
        </form>
      )}
    </div>
  );
}
