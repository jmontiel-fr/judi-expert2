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
}

export interface StepDetail {
  id: number;
  step_number: number;
  statut: string;
  executed_at: string | null;
  validated_at: string | null;
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
    if (err.response?.data?.detail) return err.response.data.detail;
    if (err.response?.status === 401) return "Session expirée. Veuillez vous reconnecter.";
    if (err.response?.status === 403) return "Accès refusé.";
    if (err.response?.status === 404) return "Ressource non trouvée.";
    if (err.response?.status === 503) return "Service temporairement indisponible.";
  }
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

  async login(password: string) {
    const res = await apiClient.post<{ access_token: string; token_type: string }>(
      "/api/auth/login",
      { password },
    );
    setToken(res.data.access_token);
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
};

// ---------------------------------------------------------------------------
// Step0 API (Extraction)
// ---------------------------------------------------------------------------

export const step0Api = {
  async extract(dossierId: string | number, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiClient.post<{ markdown: string; pdf_path: string; md_path: string }>(
      `/api/dossiers/${dossierId}/step0/extract`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return res.data;
  },

  async getMarkdown(dossierId: string | number) {
    const res = await apiClient.get<{ markdown: string }>(
      `/api/dossiers/${dossierId}/step0/markdown`,
    );
    return res.data;
  },

  async updateMarkdown(dossierId: string | number, content: string) {
    const res = await apiClient.put<{ message: string }>(
      `/api/dossiers/${dossierId}/step0/markdown`,
      { content },
    );
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Step1 API (PEMEC)
// ---------------------------------------------------------------------------

export const step1Api = {
  async execute(dossierId: string | number) {
    const res = await apiClient.post<{ qmec: string }>(
      `/api/dossiers/${dossierId}/step1/execute`,
      {},
    );
    return res.data;
  },

  getDownloadUrl(dossierId: string | number): string {
    const token = getToken();
    const base = API_BASE_URL || "";
    const url = `${base}/api/dossiers/${dossierId}/step1/download`;
    return token ? `${url}?token=${encodeURIComponent(token)}` : url;
  },

  async validate(dossierId: string | number) {
    const res = await apiClient.post<{ message: string }>(
      `/api/dossiers/${dossierId}/step1/validate`,
      {},
    );
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Step2 API (Upload)
// ---------------------------------------------------------------------------

export const step2Api = {
  async upload(dossierId: string | number, neFile: File, rebFile: File) {
    const formData = new FormData();
    formData.append("ne", neFile);
    formData.append("reb", rebFile);
    const res = await apiClient.post<{ message: string; filenames: string[] }>(
      `/api/dossiers/${dossierId}/step2/upload`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return res.data;
  },

  async validate(dossierId: string | number) {
    const res = await apiClient.post<{ message: string }>(
      `/api/dossiers/${dossierId}/step2/validate`,
      {},
    );
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Step3 API (REF + RAUX)
// ---------------------------------------------------------------------------

export const step3Api = {
  async execute(dossierId: string | number) {
    const res = await apiClient.post<{ ref: string; raux: string }>(
      `/api/dossiers/${dossierId}/step3/execute`,
      {},
    );
    return res.data;
  },

  getDownloadUrl(dossierId: string | number, docType: "ref" | "raux"): string {
    const token = getToken();
    const base = API_BASE_URL || "";
    const url = `${base}/api/dossiers/${dossierId}/step3/download/${docType}`;
    return token ? `${url}?token=${encodeURIComponent(token)}` : url;
  },

  async validate(dossierId: string | number) {
    const res = await apiClient.post<{ message: string }>(
      `/api/dossiers/${dossierId}/step3/validate`,
      {},
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
 * Step N is accessible if N === 0 OR step N-1 has statut "valide".
 */
export function isStepAccessible(stepNumber: number, steps: DossierStep[]): boolean {
  if (stepNumber === 0) return true;
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

export default apiClient;
