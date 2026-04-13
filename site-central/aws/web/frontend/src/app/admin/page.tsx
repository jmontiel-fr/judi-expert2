"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import {
  apiListExperts,
  apiGetTicketStats,
  type ExpertItem,
  type TicketStats,
  type MonthStat,
} from "@/lib/api";
import styles from "./admin.module.css";

const DOMAINES = ["Tous", "psychologie", "psychiatrie", "medecine_legale", "batiment", "comptabilite"];

type Tab = "experts" | "stats";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR");
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function ExpertsTab({ experts, loading }: { experts: ExpertItem[]; loading: boolean }) {
  if (loading) return <p>Chargement des experts…</p>;
  if (experts.length === 0) return <p className={styles.emptyState}>Aucun expert inscrit.</p>;

  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th>Nom</th>
          <th>Prénom</th>
          <th>Email</th>
          <th>Domaine</th>
          <th>Date d&apos;inscription</th>
        </tr>
      </thead>
      <tbody>
        {experts.map((e) => (
          <tr key={e.id}>
            <td>{e.nom}</td>
            <td>{e.prenom}</td>
            <td>{e.email}</td>
            <td>{e.domaine}</td>
            <td>{formatDate(e.created_at)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function StatsTab({
  stats,
  loading,
  domaineFilter,
  onFilterChange,
}: {
  stats: TicketStats | null;
  loading: boolean;
  domaineFilter: string;
  onFilterChange: (v: string) => void;
}) {
  return (
    <>
      <div className={styles.filterBar}>
        <label htmlFor="domaine-filter" className={styles.filterLabel}>Filtrer par domaine :</label>
        <select id="domaine-filter" className={styles.filterSelect}
          value={domaineFilter} onChange={(e) => onFilterChange(e.target.value)}>
          {DOMAINES.map((d) => <option key={d} value={d}>{d === "Tous" ? "Tous" : d}</option>)}
        </select>
      </div>

      {loading && <p>Chargement des statistiques…</p>}

      {stats && (
        <>
          <div className={styles.statsSection}>
            <h3 className={styles.sectionTitle}>Aujourd&apos;hui</h3>
            <p>{stats.today_count} ticket(s) — {Number(stats.today_amount).toFixed(2)} €</p>
          </div>

          <div className={styles.statsSection}>
            <h3 className={styles.sectionTitle}>Mois courant</h3>
            <p>{stats.month_count} ticket(s) — {Number(stats.month_amount).toFixed(2)} €</p>
          </div>

          <div className={styles.statsSection}>
            <h3 className={styles.sectionTitle}>Mois passés</h3>
            {stats.past_months.length === 0 ? (
              <p>Aucun achat les mois précédents</p>
            ) : (
              <table className={styles.table}>
                <thead>
                  <tr><th>Mois</th><th>Nombre</th><th>Montant</th></tr>
                </thead>
                <tbody>
                  {stats.past_months.map((m: MonthStat) => (
                    <tr key={m.month}>
                      <td>{m.month}</td>
                      <td>{m.count}</td>
                      <td>{Number(m.amount).toFixed(2)} €</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Main page component                                                */
/* ------------------------------------------------------------------ */

export default function AdminPage() {
  const { user, isAdmin, accessToken } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<Tab>("experts");
  const [experts, setExperts] = useState<ExpertItem[]>([]);
  const [ticketStats, setTicketStats] = useState<TicketStats | null>(null);
  const [domaineFilter, setDomaineFilter] = useState("Tous");
  const [loadingExperts, setLoadingExperts] = useState(true);
  const [loadingStats, setLoadingStats] = useState(true);
  const [error, setError] = useState("");

  /* Auth guard */
  useEffect(() => {
    if (!user) {
      router.replace("/connexion");
    } else if (!isAdmin) {
      router.replace("/");
    }
  }, [user, isAdmin, router]);

  /* Fetch experts */
  useEffect(() => {
    async function load() {
      if (!accessToken) return;
      try {
        const data = await apiListExperts(accessToken);
        setExperts(data);
      } catch {
        setError("Impossible de charger la liste des experts.");
      } finally {
        setLoadingExperts(false);
      }
    }
    load();
  }, [accessToken]);

  /* Fetch ticket stats (re-fetch when filter changes) */
  useEffect(() => {
    async function load() {
      if (!accessToken) return;
      setLoadingStats(true);
      try {
        const data = await apiGetTicketStats(accessToken, domaineFilter);
        setTicketStats(data);
      } catch {
        setError("Impossible de charger les statistiques.");
      } finally {
        setLoadingStats(false);
      }
    }
    load();
  }, [accessToken, domaineFilter]);

  if (!user || !isAdmin) {
    return <div className={styles.loading}>Redirection…</div>;
  }

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Administration</h1>
      <p className={styles.subtitle}>Gestion des experts et statistiques de vente</p>

      {error && <p style={{ color: "var(--color-error, #dc2626)", marginBottom: 16 }}>{error}</p>}

      <nav className={styles.tabNav} aria-label="Administration">
        <button type="button"
          className={`${styles.tabBtn} ${activeTab === "experts" ? styles.tabBtnActive : ""}`}
          onClick={() => setActiveTab("experts")} aria-selected={activeTab === "experts"}>
          Experts
        </button>
        <button type="button"
          className={`${styles.tabBtn} ${activeTab === "stats" ? styles.tabBtnActive : ""}`}
          onClick={() => setActiveTab("stats")} aria-selected={activeTab === "stats"}>
          Statistiques tickets
        </button>
      </nav>

      {activeTab === "experts" && <ExpertsTab experts={experts} loading={loadingExperts} />}
      {activeTab === "stats" && (
        <StatsTab stats={ticketStats} loading={loadingStats}
          domaineFilter={domaineFilter} onFilterChange={setDomaineFilter} />
      )}
    </div>
  );
}
