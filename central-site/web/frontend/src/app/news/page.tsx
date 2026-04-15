"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { apiListNews, apiGetNews, type NewsItem, type NewsDetail } from "@/lib/api";
import styles from "./news.module.css";

export default function NewsPage() {
  const { accessToken } = useAuth();
  const [newsList, setNewsList] = useState<NewsItem[]>([]);
  const [selected, setSelected] = useState<NewsDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadNews();
  }, [accessToken]);

  async function loadNews() {
    try {
      const data = await apiListNews(accessToken);
      setNewsList(data);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }

  async function handleView(id: number) {
    try {
      const detail = await apiGetNews(id, accessToken);
      setSelected(detail);
      // Marquer comme lu dans la liste locale
      setNewsList((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch {
      // silently fail
    }
  }

  if (loading) return <div className={styles.container}><p>Chargement...</p></div>;

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Actualités</h1>

      {selected && (
        <div className={styles.detailCard}>
          <button type="button" className={styles.backBtn} onClick={() => setSelected(null)}>
            ← Retour à la liste
          </button>
          <h2 className={styles.detailTitle}>{selected.titre}</h2>
          <p className={styles.detailDate}>
            {new Date(selected.created_at).toLocaleDateString("fr-FR")}
          </p>
          <div className={styles.detailContent}>{selected.contenu}</div>
        </div>
      )}

      {!selected && (
        <>
          {newsList.length === 0 && (
            <p className={styles.empty}>Aucune actualité pour le moment.</p>
          )}
          <div className={styles.list}>
            {newsList.map((n) => (
              <div key={n.id} className={styles.newsRow}>
                <span className={n.is_read ? styles.readDot : styles.unreadDot}
                  title={n.is_read ? "Lu" : "Non lu"} />
                <span className={styles.newsDate}>
                  {new Date(n.created_at).toLocaleDateString("fr-FR")}
                </span>
                <span className={styles.newsTitre}>{n.titre}</span>
                <button type="button" className={styles.viewBtn} onClick={() => handleView(n.id)}>
                  Voir
                </button>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
