/**
 * Centralized API client for the Site Central frontend.
 * Connects to all FastAPI backend routes.
 *
 * Base URL is configurable via NEXT_PUBLIC_API_URL (defaults to http://localhost:8000).
 */

/**
 * When NEXT_PUBLIC_API_URL is set, calls go directly to the backend.
 * Otherwise, calls use relative paths and rely on Next.js rewrites
 * (see next.config.js) to proxy /api/* → http://localhost:8000/api/*.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? "Erreur serveur");
  }
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

/* ------------------------------------------------------------------ */
/*  Auth                                                               */
/* ------------------------------------------------------------------ */

export interface RegisterPayload {
  email: string;
  password: string;
  nom: string;
  prenom: string;
  adresse: string;
  ville: string;
  code_postal: string;
  telephone: string;
  domaine: string;
  accept_mentions_legales: boolean;
  accept_cgu: boolean;
  accept_protection_donnees: boolean;
  accept_newsletter: boolean;
}

export interface AuthTokens {
  access_token: string;
  id_token: string;
  refresh_token: string;
}

export async function apiRegister(payload: RegisterPayload): Promise<{ message: string; cognito_sub: string }> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

export async function apiLogin(email: string, password: string, captchaToken: string): Promise<AuthTokens> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, captcha_token: captchaToken }),
  });
  return handleResponse(res);
}

export async function apiLogout(accessToken: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ access_token: accessToken }),
  });
  await handleResponse(res);
}


/* ------------------------------------------------------------------ */
/*  Profile                                                            */
/* ------------------------------------------------------------------ */

export interface Profile {
  id: number;
  email: string;
  nom: string;
  prenom: string;
  adresse: string;
  ville: string;
  code_postal: string;
  telephone: string;
  domaine: string;
  accept_newsletter: boolean;
  created_at: string;
}

export interface ProfileUpdate {
  nom?: string;
  prenom?: string;
  adresse?: string;
  ville?: string;
  code_postal?: string;
  telephone?: string;
  domaine?: string;
  accept_newsletter?: boolean;
}

export async function apiGetProfile(token: string): Promise<Profile> {
  const res = await fetch(`${API_BASE}/api/profile`, {
    headers: authHeaders(token),
  });
  return handleResponse(res);
}

export async function apiUpdateProfile(token: string, data: ProfileUpdate): Promise<Profile> {
  const res = await fetch(`${API_BASE}/api/profile`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function apiChangePassword(token: string, oldPassword: string, newPassword: string): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/api/profile/password`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  });
  return handleResponse(res);
}

export async function apiDeleteAccount(token: string): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/api/profile/delete`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  return handleResponse(res);
}

/* ------------------------------------------------------------------ */
/*  Tickets                                                            */
/* ------------------------------------------------------------------ */

export interface TicketItem {
  id: number;
  ticket_code: string;
  domaine: string;
  statut: string;
  montant: number;
  created_at: string;
  used_at: string | null;
}

export interface PurchaseResult {
  checkout_url: string;
}

export async function apiListTickets(token: string): Promise<TicketItem[]> {
  const res = await fetch(`${API_BASE}/api/tickets/list`, {
    headers: authHeaders(token),
  });
  return handleResponse(res);
}

export async function apiPurchaseTicket(token: string): Promise<PurchaseResult> {
  const res = await fetch(`${API_BASE}/api/tickets/purchase`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({}),
  });
  return handleResponse(res);
}

/* ------------------------------------------------------------------ */
/*  Corpus                                                             */
/* ------------------------------------------------------------------ */

export interface CorpusVersion {
  id: number;
  version: string;
  description: string;
  ecr_image_uri: string;
  published_at: string;
}

export interface CorpusDomain {
  nom: string;
  repertoire: string;
  actif: boolean;
  versions: CorpusVersion[];
}

export async function apiListCorpus(): Promise<CorpusDomain[]> {
  const res = await fetch(`${API_BASE}/api/corpus`, {
    headers: { "Content-Type": "application/json" },
  });
  return handleResponse(res);
}

export async function apiGetCorpusVersions(domaine: string): Promise<CorpusVersion[]> {
  const res = await fetch(`${API_BASE}/api/corpus/${encodeURIComponent(domaine)}/versions`, {
    headers: { "Content-Type": "application/json" },
  });
  return handleResponse(res);
}

/* ------------------------------------------------------------------ */
/*  Contact                                                            */
/* ------------------------------------------------------------------ */

export async function apiSubmitContact(
  data: { domaine: string; objet: string; message: string },
  token?: string | null,
): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/api/contact`, {
    method: "POST",
    headers: authHeaders(token ?? null),
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

/* ------------------------------------------------------------------ */
/*  Downloads                                                          */
/* ------------------------------------------------------------------ */

export interface DownloadInfo {
  download_url: string;
  version: string;
  description: string;
  file_size: string | null;
}

export async function apiGetDownloadInfo(): Promise<DownloadInfo> {
  const res = await fetch(`${API_BASE}/api/downloads/app`, {
    headers: { "Content-Type": "application/json" },
  });
  return handleResponse(res);
}

/* ------------------------------------------------------------------ */
/*  Admin                                                              */
/* ------------------------------------------------------------------ */

export interface ExpertItem {
  id: number;
  email: string;
  nom: string;
  prenom: string;
  domaine: string;
  created_at: string;
}

export interface MonthStat {
  month: string;
  count: number;
  amount: number;
}

export interface TicketStats {
  today_count: number;
  today_amount: number;
  month_count: number;
  month_amount: number;
  past_months: MonthStat[];
}

export async function apiListExperts(token: string): Promise<ExpertItem[]> {
  const res = await fetch(`${API_BASE}/api/admin/experts`, {
    headers: authHeaders(token),
  });
  return handleResponse(res);
}

export async function apiGetTicketStats(token: string, domaine: string = "Tous"): Promise<TicketStats> {
  const params = new URLSearchParams({ domaine });
  const res = await fetch(`${API_BASE}/api/admin/stats/tickets?${params}`, {
    headers: authHeaders(token),
  });
  return handleResponse(res);
}
