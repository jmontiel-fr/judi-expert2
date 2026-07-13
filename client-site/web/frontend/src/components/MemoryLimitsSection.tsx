"use client";

import { useState, useEffect, useCallback } from "react";
import styles from "./MemoryLimitsSection.module.css";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

interface MemoryLimits {
  llm: string;
  rag: string;
  backend: string;
  frontend: string;
  ocr: string;
  total_allocated_mb: number;
  ram_total_mb: number;
  ram_available_for_docker_mb: number;
}

interface ContainerConfig {
  key: keyof Omit<MemoryLimits, "total_allocated_mb" | "ram_total_mb" | "ram_available_for_docker_mb">;
  label: string;
  description: string;
  minMb: number;
}

const CONTAINERS: ContainerConfig[] = [
  { key: "llm", label: "LLM (Ollama)", description: "Modèle d'IA — le plus gourmand", minMb: 2048 },
  { key: "rag", label: "RAG (Qdrant)", description: "Base vectorielle du corpus métier", minMb: 256 },
  { key: "backend", label: "Backend (FastAPI)", description: "Serveur API principal", minMb: 256 },
  { key: "frontend", label: "Frontend (Next.js)", description: "Interface utilisateur", minMb: 256 },
  { key: "ocr", label: "OCR (Tesseract)", description: "Extraction texte des PDF", minMb: 128 },
];

function parseMemToMb(value: string): number {
  const v = value.trim().toLowerCase();
  if (v.endsWith("g")) return Math.round(parseFloat(v) * 1024);
  if (v.endsWith("m")) return Math.round(parseFloat(v));
  return parseInt(v, 10) || 0;
}

function mbToDisplay(mb: number): string {
  if (mb >= 1024 && mb % 1024 === 0) return `${mb / 1024} Go`;
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} Go`;
  return `${mb} Mo`;
}

export default function MemoryLimitsSection() {
  const [limits, setLimits] = useState<MemoryLimits | null>(null);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [restarting, setRestarting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [needsRestart, setNeedsRestart] = useState(false);

  const fetchLimits = useCallback(async () => {
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_URL}/api/config/memory-limits`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Erreur chargement");
      const data: MemoryLimits = await res.json();
      setLimits(data);
      setEditValues({
        llm: data.llm,
        rag: data.rag,
        backend: data.backend,
        frontend: data.frontend,
        ocr: data.ocr,
      });
    } catch {
      setError("Impossible de charger la configuration mémoire.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchLimits(); }, [fetchLimits]);

  const totalAllocatedMb = Object.values(editValues).reduce(
    (sum, v) => sum + parseMemToMb(v), 0
  );
  const ramAvailable = limits?.ram_available_for_docker_mb ?? 0;
  const overBudget = totalAllocatedMb > ramAvailable;

  async function handleSave() {
    setError("");
    setSuccess("");
    setSaving(true);

    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_URL}/api/config/memory-limits`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(editValues),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        setError(data?.detail || "Erreur lors de la sauvegarde.");
        return;
      }

      setSuccess("Configuration sauvegardée. Redémarrage nécessaire pour appliquer.");
      setNeedsRestart(true);
      await fetchLimits();
    } catch {
      setError("Erreur réseau lors de la sauvegarde.");
    } finally {
      setSaving(false);
    }
  }

  async function handleRestart() {
    setError("");
    setSuccess("");
    setRestarting(true);

    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_URL}/api/config/restart`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        setError(data?.detail || "Erreur lors du redémarrage.");
        return;
      }

      setSuccess("Redémarrage en cours… La page se rechargera automatiquement.");
      setNeedsRestart(false);
      // Wait then reload
      setTimeout(() => window.location.reload(), 15000);
    } catch {
      setSuccess("Redémarrage initié. Rechargez la page dans quelques secondes.");
      setTimeout(() => window.location.reload(), 15000);
    } finally {
      setRestarting(false);
    }
  }

  if (loading) {
    return <div className={styles.container}><p>Chargement…</p></div>;
  }

  return (
    <div className={styles.container}>
      <p className={styles.intro}>
        Configurez la mémoire RAM allouée à chaque service Docker.
        Le total ne doit pas dépasser la RAM disponible pour Docker
        ({limits ? mbToDisplay(ramAvailable) : "—"} sur {limits ? mbToDisplay(limits.ram_total_mb) : "—"} totaux,
        après réserve de 7 Go pour le système et vos applications).
      </p>

      {error && <div className={styles.errorMsg} role="alert">{error}</div>}
      {success && <div className={styles.successMsg} role="status">{success}</div>}

      <div className={styles.limitsGrid}>
        {CONTAINERS.map((c) => {
          const currentMb = parseMemToMb(editValues[c.key] || "0");
          const belowMin = currentMb < c.minMb;
          return (
            <div key={c.key} className={styles.limitCard}>
              <div className={styles.limitHeader}>
                <label htmlFor={`mem-${c.key}`} className={styles.limitLabel}>
                  {c.label}
                </label>
                <span className={styles.limitDesc}>{c.description}</span>
              </div>
              <div className={styles.limitInputRow}>
                <input
                  id={`mem-${c.key}`}
                  type="text"
                  className={`${styles.limitInput} ${belowMin ? styles.inputError : ""}`}
                  value={editValues[c.key] || ""}
                  onChange={(e) => setEditValues({ ...editValues, [c.key]: e.target.value })}
                  placeholder={`ex: ${c.minMb >= 1024 ? `${c.minMb / 1024}g` : `${c.minMb}m`}`}
                  aria-describedby={`mem-${c.key}-info`}
                />
                <span className={styles.limitMb} id={`mem-${c.key}-info`}>
                  = {mbToDisplay(currentMb)} (min: {mbToDisplay(c.minMb)})
                </span>
              </div>
              {belowMin && (
                <span className={styles.limitWarning}>
                  ⚠️ En dessous du minimum requis ({mbToDisplay(c.minMb)})
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Budget bar */}
      <div className={styles.budgetSection}>
        <div className={styles.budgetHeader}>
          <span>Total alloué :</span>
          <span className={overBudget ? styles.budgetOver : styles.budgetOk}>
            {mbToDisplay(totalAllocatedMb)} / {mbToDisplay(ramAvailable)}
          </span>
        </div>
        <div className={styles.budgetBarContainer}>
          <div
            className={`${styles.budgetBar} ${overBudget ? styles.budgetBarOver : ""}`}
            style={{ width: `${Math.min((totalAllocatedMb / ramAvailable) * 100, 100)}%` }}
          />
        </div>
        {overBudget && (
          <p className={styles.budgetWarning} role="alert">
            ⚠️ Le total alloué dépasse la RAM disponible. Réduisez les limites pour éviter l&apos;instabilité.
          </p>
        )}
      </div>

      {/* Actions */}
      <div className={styles.actions}>
        <button
          className={styles.saveBtn}
          onClick={handleSave}
          disabled={saving || overBudget}
        >
          {saving ? "Sauvegarde…" : "Sauvegarder"}
        </button>

        {needsRestart && (
          <button
            className={styles.restartBtn}
            onClick={handleRestart}
            disabled={restarting}
          >
            {restarting ? "Redémarrage…" : "🔄 Redémarrer les services"}
          </button>
        )}
      </div>
    </div>
  );
}
