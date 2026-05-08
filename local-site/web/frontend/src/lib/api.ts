/**
 * API Client — Centralized service for all backend communication.
 *
 * Connects the Next.js frontend to the FastAPI backend (port 8000).
 * All API calls go through this module for consistent auth, error handling,
 * and base URL configuration.
 *
 * The API base URL is configurable via NEXT_PUBLIC_API_URL env variable
 * (defaults to "" which uses Next.js rewrites to proxy to localhost:8000).
 */

import axios, { AxiosError, type AxiosInstance } from "axios";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DossierStep {
  step_number: number;
  statut: string;
  executed_at: string | null;
  validated_at: string | null;
  execution_duration_seconds: number | null;
  files: StepFileItem[];
}

export interface DossierListItem {
  id: number;
  nom: string;
  ticket_id: string;
  domaine: string;
  statut: string;
  created_at: string;
  steps?: DossierStep[];
}

export interface DossierDetail {
  id: number;
  nom: string;
  ticket_id: string;
  domaine: string;
  statut: string;
  created_at: string;
  updated_at: string;
  steps: DossierStep[];
}

export interface StepFileItem {
  id: number;
  filename: string;
  file_path: string;
  file_type: string;
  file_size: number;
  created_at: string;
  is_modified: boolean;
  original_file_path: string | null;
  updated_at: string | null;
}

export interface StepDetail {
  id: number;
  step_number: number;
  statut: string;
  executed_at: string | null;
  validated_at: string | null;
  execution_duration_seconds: number | null;
  files: StepFileItem[];
}

export interface RAGVersion {
  version: string;
  description: string;
  domaine: string;
}

export interface DocumentItem {
  doc_id: string;
  filename: string;
  doc_type: string;
  chunk_count: number;
  collection: string;
}

export interface StepFileResponse {
  id: number;
  filename: string;
  file_type: string;
  file_size: number;
  is_modified: boolean;
  original_file_path: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface StepFileReplaceResponse {
  message: string;
  file: StepFileResponse;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Token management
// ---------------------------------------------------------------------------

const TOKEN_KEY = "token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_KEY, token);
  }
}

export function clearToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
  }
}

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120_000, // 2 min — OCR/LLM calls can be slow
});

// Request interceptor — attach JWT token
apiClient.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — normalize errors
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) => {
    // Extract a human-readable message from the backend error
    if (error.response?.data?.detail) {
      error.message = error.response.data.detail;
    }
    return Promise.reject(error);
  },
);

/**
 * Extract a user-friendly error message from an axios error.
 */
export function getErrorMessage(err: unknown, fallback = "Une erreur est survenue."): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data;
    // FastAPI detail string
    if (typeof data?.detail === "string") return data.detail;
    // FastAPI validation errors (422) — array of {loc, msg, type}
    if (Array.isArray(data?.detail)) {
      return data.detail.map((e: { msg?: string }) => e.msg ?? "Erreur de validation").join(", ");
    }
    // Other structured error
    if (data?.message) return data.message;
    // Status-based fallbacks
    const status = err.response?.status;
    if (status === 401) return "Session expirée. Veuillez vous reconnecter.";
    if (status === 403) return "Accès refusé.";
    if (status === 404) return "Ressource non trouvée.";
    if (status === 422) return "Données invalides envoyées au serveur.";
    if (status === 500) return "Erreur interne du serveur.";
    if (status === 502) return "Erreur de communication entre services.";
    if (status === 503) return "Service temporairement indisponible.";
    if (status) return `Erreur serveur (HTTP ${status}).`;
    // Network error (no response)
    if (err.code === "ERR_NETWORK") return "Erreur réseau — le serveur est-il démarré ?";
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------

export const authApi = {
  async setup(password: string, domaine: string) {
    const res = await apiClient.post<{ message: string; domaine: string }>(
      "/api/auth/setup",
      { password, domaine },
    );
    return res.data;
  },

  async login(email: string, password: string) {
    const res = await apiClient.post<{ access_token: string; token_type: string; email: string; domaine: string }>(
      "/api/auth/login",
      { email, password },
    );
    setToken(res.data.access_token);
    return res.data;
  },

  async info() {
    const res = await apiClient.get<{ configured: boolean; email: string | null; domaine: string | null }>(
      "/api/auth/info",
    );
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Config API
// ---------------------------------------------------------------------------

export const configApi = {
  async getDomain() {
    const res = await apiClient.get<{ domaine: string; rag_version?: string }>(
      "/api/config/domain",
    );
    return res.data;
  },

  async updateDomain(domaine: string) {
    const res = await apiClient.put<{ domaine: string }>(
      "/api/config/domain",
      { domaine },
    );
    return res.data;
  },

  async getRagVersions() {
    const res = await apiClient.get<{ versions: RAGVersion[] }>(
      "/api/config/rag-versions",
    );
    return res.data;
  },

  async installRag(version: string) {
    const res = await apiClient.post<{ message: string; version: string }>(
      "/api/config/rag-install",
      { version },
    );
    return res.data;
  },

  async uploadTpe(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiClient.post<{ message: string; filename: string; doc_id: string }>(
      "/api/config/tpe",
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return res.data;
  },

  async uploadTemplate(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiClient.post<{ message: string; filename: string; doc_id: string }>(
      "/api/config/template",
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return res.data;
  },

  async getDocuments() {
    const res = await apiClient.get<{ documents: DocumentItem[] }>(
      "/api/config/documents",
    );
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Dossiers API
// ---------------------------------------------------------------------------

export const dossiersApi = {
  async list() {
    const res = await apiClient.get<{ dossiers: DossierListItem[] }>(
      "/api/dossiers",
    );
    return res.data;
  },

  async create(nom: string, ticket_id: string) {
    const res = await apiClient.post<DossierDetail>(
      "/api/dossiers",
      { nom, ticket_id },
    );
    return res.data;
  },

  async get(id: string | number) {
    const res = await apiClient.get<DossierDetail>(
      `/api/dossiers/${id}`,
    );
    return res.data;
  },

  async getStep(dossierId: string | number, stepNumber: number) {
    const res = await apiClient.get<StepDetail>(
      `/api/dossiers/${dossierId}/steps/${stepNumber}`,
    );
    return res.data;
  },

  async close(id: string | number) {
    const res = await apiClient.post<{ message: string }>(
      `/api/dossiers/${id}/close`,
      {},
    );
    return res.data;
  },

  getDownloadUrl(id: string | number): string {
    const token = getToken();
    const base = API_BASE_URL || "";
    const url = `${base}/api/dossiers/${id}/download`;
    return token ? `${url}?token=${encodeURIComponent(token)}` : url;
  },

  async resetStep(dossierId: string | number, stepNumber: number) {
    const res = await apiClient.post<{ message: string }>(
      `/api/dossiers/${dossierId}/steps/${stepNumber}/reset`,
      {},
    );
    return res.data;
  },

  async cancelStep(dossierId: string | number, stepNumber: number) {
    const res = await apiClient.post<{ message: string }>(
      `/api/dossiers/${dossierId}/steps/${stepNumber}/cancel`,
      {},
    );
    return res.data;
  },

  async validateStep(dossierId: string | number, stepNumber: number) {
    const res = await apiClient.post<{ message: string }>(
      `/api/dossiers/${dossierId}/step${stepNumber === 0 ? 1 : stepNumber}/validate`,
      {},
    );
    return res.data;
  },

  async resetAll(dossierId: string | number) {
    const res = await apiClient.post<{ message: string }>(
      `/api/dossiers/${dossierId}/reset-all`,
      {},
    );
    return res.data;
  },

  async archive(dossierId: string | number) {
    const res = await apiClient.post<{ message: string }>(
      `/api/dossiers/${dossierId}/archive`,
      {},
    );
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Step 1 API — Création dossier (extraction OCR + structuration)
// ---------------------------------------------------------------------------

export const step1Api = {
  /** Upload ordonnance PDF dans step1/in/ (sans lancer de traitement) */
  async upload(dossierId: string | number, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiClient.post<{ message: string; filename: string; file_size: number }>(
      `/api/dossiers/${dossierId}/step1/upload`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" }, timeout: 60_000 },
    );
    return res.data;
  },

  /** Lance l'extraction OCR + structuration LLM sur les fichiers uploadés */
  async execute(dossierId: string | number) {
    const res = await apiClient.post<{ markdown: string; pdf_path: string; md_path: string }>(
      `/api/dossiers/${dossierId}/step1/execute`,
      {},
      { timeout: 1_800_000 },
    );
    return res.data;
  },

  /** [LEGACY] Upload + extraction en un seul appel */
  async extract(dossierId: string | number, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiClient.post<{ markdown: string; pdf_path: string; md_path: string }>(
      `/api/dossiers/${dossierId}/step1/extract`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" }, timeout: 1_800_000 },
    );
    return res.data;
  },

  /** Upload pièce complémentaire (rapport, plainte, autre) */
  async uploadComplementary(dossierId: string | number, file: File, label: string, extractOcr: boolean, docType: string = "autre", docFormat: string = "pdf") {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("label", label);
    formData.append("extract_ocr", String(extractOcr));
    formData.append("doc_type", docType);
    formData.append("doc_format", docFormat);
    const res = await apiClient.post<{ message: string }>(
      `/api/dossiers/${dossierId}/step1/complementary`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" }, timeout: 1_800_000 },
    );
    return res.data;
  },

  /** Récupérer le Markdown de l'ordonnance */
  async getMarkdown(dossierId: string | number) {
    const res = await apiClient.get<{ markdown: string }>(
      `/api/dossiers/${dossierId}/step1/markdown`,
    );
    return res.data;
  },

  /** Mettre à jour le Markdown (édition manuelle) */
  async updateMarkdown(dossierId: string | number, content: string) {
    const res = await apiClient.put<{ message: string }>(
      `/api/dossiers/${dossierId}/step1/markdown`,
      { content },
    );
    return res.data;
  },

  /** Importer un .docx modifié par l'expert */
  async importDocx(dossierId: string | number, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiClient.post<{ message: string }>(
      `/api/dossiers/${dossierId}/step1/import-docx`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return res.data;
  },

  /** Valider le Step 1 (verrouillage) */
  async validate(dossierId: string | number) {
    const res = await apiClient.post<{ message: string }>(
      `/api/dossiers/${dossierId}/step1/validate`,
      {},
    );
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Step 2 API — Préparation investigations (génération PE/PA)
// ---------------------------------------------------------------------------

export const step2Api = {
  /** Générer le Plan d'Entretien (PE) ou Plan d'Analyse (PA) */
  async execute(dossierId: string | number, mode: "entretien" | "analyse" = "entretien") {
    const res = await apiClient.post<{ plan: string }>(
      `/api/dossiers/${dossierId}/step2/execute`,
      { mode },
      { timeout: 1_800_000 },
    );
    return res.data;
  },

  /** Télécharger le PE/PA généré */
  getDownloadUrl(dossierId: string | number): string {
    const token = getToken();
    const base = API_BASE_URL || "";
    const url = `${base}/api/dossiers/${dossierId}/step2/download`;
    return token ? `${url}?token=${encodeURIComponent(token)}` : url;
  },

  /** Valider le Step 2 (verrouillage) */
  async validate(dossierId: string | number) {
    const res = await apiClient.post<{ message: string }>(
      `/api/dossiers/${dossierId}/step2/validate`,
      {},
    );
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Step 3 API — Consolidation documentaire (import pièces diligence + OCR)
// ---------------------------------------------------------------------------

export const step3Api = {
  /** Upload pièces de diligence (PDF/scan) → OCR → .md */
  async upload(dossierId: string | number, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiClient.post<{ message: string; filename: string }>(
      `/api/dossiers/${dossierId}/step3/upload`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" }, timeout: 1_800_000 },
    );
    return res.data;
  },

  /** Lancer l'extraction OCR sur les pièces uploadées */
  async execute(dossierId: string | number) {
    const res = await apiClient.post<{ message: string; filenames: string[] }>(
      `/api/dossiers/${dossierId}/step3/execute`,
      {},
      { timeout: 1_800_000 },
    );
    return res.data;
  },

  /** Valider le Step 3 (verrouillage) */
  async validate(dossierId: string | number) {
    const res = await apiClient.post<{ message: string }>(
      `/api/dossiers/${dossierId}/step3/validate`,
      {},
    );
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Step 4 API — Production pré-rapport (PEA/PAA → PRE + DAC)
// ---------------------------------------------------------------------------

export const step4Api = {
  /** Upload du PEA/PAA annoté et génération du pré-rapport + DAC */
  async execute(dossierId: string | number, peaFile: File) {
    const formData = new FormData();
    formData.append("file", peaFile);
    const res = await apiClient.post<{ message: string; filenames: string[] }>(
      `/api/dossiers/${dossierId}/step4/execute`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" }, timeout: 1_800_000 },
    );
    return res.data;
  },

  /** Télécharger le PRE ou le DAC */
  getDownloadUrl(dossierId: string | number, docType: "pre" | "dac"): string {
    const token = getToken();
    const base = API_BASE_URL || "";
    const url = `${base}/api/dossiers/${dossierId}/step4/download/${docType}`;
    return token ? `${url}?token=${encodeURIComponent(token)}` : url;
  },

  /** Valider le Step 4 (verrouillage) */
  async validate(dossierId: string | number) {
    const res = await apiClient.post<{ message: string }>(
      `/api/dossiers/${dossierId}/step4/validate`,
      {},
    );
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Step 5 API — Finalisation et archivage (REF → ZIP + timbre)
// ---------------------------------------------------------------------------

export const step5Api = {
  /** Upload du rapport final (REF) et génération de l'archive + timbre */
  async execute(dossierId: string | number, refFile?: File) {
    const formData = new FormData();
    if (refFile) formData.append("file", refFile);
    const res = await apiClient.post<{ message: string; filenames: string[] }>(
      `/api/dossiers/${dossierId}/step5/execute`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" }, timeout: 1_800_000 },
    );
    return res.data;
  },

  /** Télécharger l'archive ZIP */
  getDownloadUrl(dossierId: string | number): string {
    const token = getToken();
    const base = API_BASE_URL || "";
    const url = `${base}/api/dossiers/${dossierId}/step5/download`;
    return token ? `${url}?token=${encodeURIComponent(token)}` : url;
  },

  /** Valider le Step 5 (verrouillage + fermeture dossier) */
  async validate(dossierId: string | number) {
    const res = await apiClient.post<{ message: string }>(
      `/api/dossiers/${dossierId}/step5/validate`,
      {},
    );
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Step Files API (generic file operations)
// ---------------------------------------------------------------------------

export const stepFilesApi = {
  getDownloadUrl(dossierId: string | number, stepNumber: number, fileId: number): string {
    const token = getToken();
    const base = API_BASE_URL || "";
    const url = `${base}/api/dossiers/${dossierId}/steps/${stepNumber}/files/${fileId}/download`;
    return token ? `${url}?token=${encodeURIComponent(token)}` : url;
  },

  getViewUrl(dossierId: string | number, stepNumber: number, fileId: number): string {
    const token = getToken();
    const base = API_BASE_URL || "";
    const url = `${base}/api/dossiers/${dossierId}/steps/${stepNumber}/files/${fileId}/view`;
    return token ? `${url}?token=${encodeURIComponent(token)}` : url;
  },

  async replaceFile(
    dossierId: string | number,
    stepNumber: number,
    fileId: number,
    file: File,
  ): Promise<StepFileReplaceResponse> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiClient.post<StepFileReplaceResponse>(
      `/api/dossiers/${dossierId}/steps/${stepNumber}/files/${fileId}/replace`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// ChatBot API
// ---------------------------------------------------------------------------

export const chatbotApi = {
  async sendMessage(message: string, sessionId = 1) {
    const res = await apiClient.post<{ response: string }>(
      "/api/chatbot/message",
      { message, session_id: sessionId },
    );
    return res.data;
  },

  async *sendMessageStream(message: string, sessionId = 1): AsyncGenerator<string> {
    const token = getToken();
    const base = API_BASE_URL || "";
    const res = await fetch(`${base}/api/chatbot/message/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message, session_id: sessionId }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const reader = res.body?.getReader();
    if (!reader) return;
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data === "[DONE]") return;
          if (data.startsWith("[ERROR]")) throw new Error(data);
          yield data;
        }
      }
    }
  },

  async getHistory(sessionId = 1) {
    const res = await apiClient.get<ChatMessage[]>(
      "/api/chatbot/history",
      { params: { session_id: sessionId } },
    );
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Workflow helpers
// ---------------------------------------------------------------------------

/**
 * Determines if a step is accessible based on the sequential workflow rule:
 * Step N is accessible if N === 1 OR step N-1 has statut "valide".
 */
export function isStepAccessible(stepNumber: number, steps: DossierStep[]): boolean {
  if (stepNumber === 1) return true;
  const sorted = [...steps].sort((a, b) => a.step_number - b.step_number);
  const prev = sorted.find((s) => s.step_number === stepNumber - 1);
  return prev?.statut === "valide";
}

/**
 * Determines if a step is locked (validated and immutable).
 */
export function isStepLocked(step: { statut: string }): boolean {
  return step.statut === "valide";
}

/**
 * Formats a file size in bytes into a human-readable string using
 * French units (o, Ko, Mo, Go). Matches the backend FileService logic.
 *
 * Exact values omit decimals (e.g. 1024 → "1 Ko"),
 * non-exact values show 1 decimal (e.g. 1536 → "1.5 Ko").
 */
export function formatFileSize(bytes: number): string {
  const units = ["o", "Ko", "Mo", "Go"] as const;
  let value = bytes;

  for (let i = 0; i < units.length - 1; i++) {
    if (value < 1024) {
      const formatted = Number(value.toFixed(1));
      return `${formatted} ${units[i]}`;
    }
    value /= 1024;
  }

  // Terminal unit: Go
  const formatted = Number(value.toFixed(1));
  return `${formatted} ${units[units.length - 1]}`;
}

export default apiClient;
