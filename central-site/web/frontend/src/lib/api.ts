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

export class NewPasswordRequiredError extends Error {
  session: string;
  email: string;
  constructor(session: string, email: string) {
    super("NEW_PASSWORD_REQUIRED");
    this.session = session;
    this.email = email;
  }
}

export async function apiLogin(email: string, password: string, captchaToken: string): Promise<AuthTokens> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, captcha_token: captchaToken }),
  });
  if (res.status === 403) {
    const data = await res.json();
    if (data.detail === "NEW_PASSWORD_REQUIRED") {
      const session = res.headers.get("X-Cognito-Session") || "";
      throw new NewPasswordRequiredError(session, email);
    }
    if (data.detail === "USER_NOT_CONFIRMED") {
      throw new Error("USER_NOT_CONFIRMED");
    }
  }
  return handleResponse(res);
}

export async function apiSetNewPassword(email: string, newPassword: string, session: string): Promise<AuthTokens> {
  const res = await fetch(`${API_BASE}/api/auth/new-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, new_password: newPassword, session }),
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
  ticket_token: string | null;
  domaine: string;
  statut: string;
  montant: number;
  created_at: string;
  expires_at: string | null;
  used_at: string | null;
}

export interface PurchaseResult {
  checkout_url: string;
}

export interface TicketPriceInfo {
  prix_ht: number;
  tva_rate: number;
  prix_ttc: number;
}

export async function apiGetTicketPrice(): Promise<TicketPriceInfo> {
  const res = await fetch(`${API_BASE}/api/tickets/price`, {
    headers: { "Content-Type": "application/json" },
  });
  return handleResponse(res);
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

export async function apiDeleteTicket(token: string, ticketId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/tickets/${ticketId}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  await handleResponse(res);
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
  data: { domaine: string; objet: string; message: string; bloquant?: boolean; urgent?: boolean; captcha_token: string },
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

export async function apiGetAdminTicketConfig(token: string): Promise<TicketPriceInfo> {
  const res = await fetch(`${API_BASE}/api/admin/ticket-config`, {
    headers: authHeaders(token),
  });
  return handleResponse(res);
}

export async function apiUpdateAdminTicketConfig(
  token: string,
  data: { prix_ht?: number; tva_rate?: number },
): Promise<TicketPriceInfo> {
  const res = await fetch(`${API_BASE}/api/admin/ticket-config`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}


/* ------------------------------------------------------------------ */
/*  News                                                               */
/* ------------------------------------------------------------------ */

export interface NewsItem {
  id: number;
  titre: string;
  visible: boolean;
  created_at: string;
  is_read: boolean;
}

export interface NewsDetail {
  id: number;
  titre: string;
  contenu: string;
  visible: boolean;
  created_at: string;
  updated_at: string;
}

export async function apiListNews(token?: string | null): Promise<NewsItem[]> {
  const res = await fetch(`${API_BASE}/api/news`, {
    headers: authHeaders(token ?? null),
  });
  return handleResponse(res);
}

export async function apiGetNews(id: number, token?: string | null): Promise<NewsDetail> {
  const res = await fetch(`${API_BASE}/api/news/${id}`, {
    headers: authHeaders(token ?? null),
  });
  return handleResponse(res);
}

/* Admin news */

export async function apiAdminListNews(token: string): Promise<NewsItem[]> {
  const res = await fetch(`${API_BASE}/api/admin/news`, {
    headers: authHeaders(token),
  });
  return handleResponse(res);
}

export async function apiAdminCreateNews(token: string, data: { titre: string; contenu: string }): Promise<NewsDetail> {
  const res = await fetch(`${API_BASE}/api/admin/news`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function apiAdminGetNews(token: string, id: number): Promise<NewsDetail> {
  const res = await fetch(`${API_BASE}/api/admin/news/${id}`, {
    headers: authHeaders(token),
  });
  return handleResponse(res);
}

export async function apiAdminUpdateNews(token: string, id: number, data: { titre?: string; contenu?: string }): Promise<NewsDetail> {
  const res = await fetch(`${API_BASE}/api/admin/news/${id}`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function apiAdminToggleVisibility(token: string, id: number): Promise<NewsDetail> {
  const res = await fetch(`${API_BASE}/api/admin/news/${id}/visibility`, {
    method: "PUT",
    headers: authHeaders(token),
  });
  return handleResponse(res);
}

export async function apiAdminDeleteNews(token: string, id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/admin/news/${id}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? "Erreur serveur");
  }
}


/* ------------------------------------------------------------------ */
/*  Corpus Content (public + admin)                                    */
/* ------------------------------------------------------------------ */

export interface ContenuItem {
  nom: string;
  description: string;
  type: string;
  date_ajout: string;
}

export interface UrlItem {
  nom: string;
  url: string;
  description: string;
  type: string;
  date_ajout: string;
}

export interface AddUrlPayload {
  nom: string;
  url: string;
  description: string;
  type: string;
}

export async function apiGetCorpusContenu(domaine: string): Promise<ContenuItem[]> {
  const res = await fetch(`${API_BASE}/api/corpus/${encodeURIComponent(domaine)}/contenu`, {
    headers: { "Content-Type": "application/json" },
  });
  return handleResponse(res);
}

export async function apiGetCorpusUrls(domaine: string): Promise<UrlItem[]> {
  const res = await fetch(`${API_BASE}/api/corpus/${encodeURIComponent(domaine)}/urls`, {
    headers: { "Content-Type": "application/json" },
  });
  return handleResponse(res);
}

export function getCorpusFileUrl(domaine: string, filename: string): string {
  return `${API_BASE}/api/corpus/${encodeURIComponent(domaine)}/fichier/${encodeURIComponent(filename)}`;
}

export async function apiAdminUploadDocument(token: string, domaine: string, file: File): Promise<ContenuItem> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/admin/corpus/${encodeURIComponent(domaine)}/documents`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  return handleResponse(res);
}

export async function apiAdminAddUrl(token: string, domaine: string, data: AddUrlPayload): Promise<UrlItem> {
  const res = await fetch(`${API_BASE}/api/admin/corpus/${encodeURIComponent(domaine)}/urls`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}


/* ------------------------------------------------------------------ */
/*  Chatbot                                                            */
/* ------------------------------------------------------------------ */

export interface ChatbotMessage {
  role: "user" | "assistant";
  content: string;
}

export async function apiChatbotMessage(
  message: string,
  history: ChatbotMessage[],
  token: string
): Promise<string> {
  const res = await fetch(`${API_BASE}/api/chatbot/message`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ message, history }),
  });
  const data = await handleResponse<{ response: string }>(res);
  return data.response;
}

/* ------------------------------------------------------------------ */
/*  Admin Chatbot                                                      */
/* ------------------------------------------------------------------ */

export interface ChatbotStatus {
  last_refresh: string | null;
  docs_indexed: number;
  points_count: number;
  available_docs: string[];
}

export interface ChatbotRefreshResult {
  message: string;
  docs_indexed: number;
  total_chunks: number;
  last_refresh: string;
}

export async function apiAdminChatbotStatus(token: string): Promise<ChatbotStatus> {
  const res = await fetch(`${API_BASE}/api/admin/chatbot/status`, {
    headers: authHeaders(token),
  });
  return handleResponse(res);
}

export async function apiAdminChatbotRefresh(token: string): Promise<ChatbotRefreshResult> {
  const res = await fetch(`${API_BASE}/api/admin/chatbot/refresh`, {
    method: "POST",
    headers: authHeaders(token),
  });
  return handleResponse(res);
}


/* ------------------------------------------------------------------ */
/*  Auth — Confirmation                                                */
/* ------------------------------------------------------------------ */

export async function apiConfirmSignUp(email: string, code: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/auth/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code }),
  });
  await handleResponse<unknown>(res);
}

export async function apiResendCode(email: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/auth/resend-code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  await handleResponse<unknown>(res);
}
