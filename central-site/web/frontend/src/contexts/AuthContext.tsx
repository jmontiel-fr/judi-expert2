"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
} from "react";
import { apiLogin, apiLogout, apiGetProfile, type Profile } from "@/lib/api";
import { isTokenExpired } from "@/lib/auth";

/* ------------------------------------------------------------------ */
/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface User {
  id: string;
  email: string;
  nom: string;
  prenom: string;
  domaine: string;
  adresse: string;
  ville: string;
  code_postal: string;
  telephone: string;
}

interface AuthContextValue {
  user: User | null;
  isAdmin: boolean;
  accessToken: string | null;
  loading: boolean;
  login: (email: string, password: string, captchaToken: string) => Promise<void>;
  register: (params: RegisterParams) => Promise<void>;
  logout: () => Promise<void>;
}

export interface RegisterParams {
  email: string;
  password: string;
  nom: string;
  prenom: string;
  adresse: string;
  ville: string;
  code_postal: string;
  telephone: string;
  domaine: string;
  acceptMentions: boolean;
  acceptCGU: boolean;
  acceptProtection: boolean;
  acceptNewsletter: boolean;
}

const ADMIN_EMAIL = "admin@judi-expert.fr";
const TOKEN_KEY = "judi_access_token";

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/* ------------------------------------------------------------------ */
/*  Provider                                                           */
/* ------------------------------------------------------------------ */

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const expirationTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* ---- Expiration timer helpers ---- */
  function clearExpirationTimer() {
    if (expirationTimerRef.current !== null) {
      clearTimeout(expirationTimerRef.current);
      expirationTimerRef.current = null;
    }
  }

  function startExpirationTimer(token: string) {
    clearExpirationTimer();
    try {
      const parts = token.split(".");
      if (parts.length !== 3) return;
      let base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
      const padding = 4 - (base64.length % 4);
      if (padding !== 4) base64 += "=".repeat(padding);
      const payload = JSON.parse(atob(base64));
      if (typeof payload.exp !== "number") return;

      const msUntilExpiry = (payload.exp - Date.now() / 1000) * 1000;
      if (msUntilExpiry <= 0) return; // Already expired, will be caught by visibilitychange or restoreSession

      expirationTimerRef.current = setTimeout(async () => {
        try {
          const currentToken = localStorage.getItem(TOKEN_KEY);
          if (currentToken) {
            await apiLogout(currentToken).catch(() => {});
          }
        } catch {
          // Best-effort backend logout
        }
        setUser(null);
        setIsAdmin(false);
        setAccessToken(null);
        localStorage.removeItem(TOKEN_KEY);
        const path = window.location.pathname;
        if (path !== "/" && path !== "/login") {
          window.location.href = "/";
        }
      }, msUntilExpiry);
    } catch {
      // Token decode failed — timer not set
    }
  }

  /* Restore session on mount */
  useEffect(() => {
    restoreSession();
  }, []);

  async function restoreSession() {
    // Try token from localStorage
    try {
      const savedToken = localStorage.getItem(TOKEN_KEY);
      if (savedToken) {
        // Check token expiration BEFORE making any API call
        if (isTokenExpired(savedToken)) {
          localStorage.removeItem(TOKEN_KEY);
          setUser(null);
          setIsAdmin(false);
          setAccessToken(null);
          setLoading(false);
          const path = window.location.pathname;
          if (path !== "/" && path !== "/login") {
            window.location.href = "/";
          }
          return;
        }

        const profile = await apiGetProfile(savedToken);
        applyProfile(profile, savedToken);
        return;
      }
    } catch {
      localStorage.removeItem(TOKEN_KEY);
    }

    setLoading(false);
  }

  /* Visibilitychange listener — check token expiration when tab becomes visible */
  useEffect(() => {
    function handleVisibilityChange() {
      if (document.visibilityState === "visible") {
        const token = localStorage.getItem(TOKEN_KEY);
        if (token && isTokenExpired(token)) {
          // Token expired while tab was hidden — trigger logout
          clearExpirationTimer();
          setUser(null);
          setIsAdmin(false);
          setAccessToken(null);
          localStorage.removeItem(TOKEN_KEY);
          const path = window.location.pathname;
          if (path !== "/" && path !== "/login") {
            window.location.href = "/";
          }
        }
      }
    }

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      clearExpirationTimer();
    };
  }, []);

  function applyProfile(profile: Profile, token: string) {
    const u: User = {
      id: String(profile.id),
      email: profile.email,
      nom: profile.nom,
      prenom: profile.prenom,
      domaine: profile.domaine,
      adresse: profile.adresse,
      ville: profile.ville || "",
      code_postal: profile.code_postal || "",
      telephone: profile.telephone || "",
    };
    setUser(u);
    setAccessToken(token);
    setIsAdmin(profile.email === ADMIN_EMAIL);
    localStorage.setItem(TOKEN_KEY, token);
    startExpirationTimer(token);
    setLoading(false);
  }

  /* ---- Login via backend (Cognito + Captcha verification) ---- */
  const login = useCallback(async (email: string, password: string, captchaToken: string) => {
    // Call the backend which validates captcha + authenticates via Cognito
    const tokens = await apiLogin(email, password, captchaToken);
    setAccessToken(tokens.access_token);

    // Fetch profile from backend
    const profile = await apiGetProfile(tokens.access_token);
    applyProfile(profile, tokens.access_token);
  }, []);

  /* ---- Register via backend (Cognito) ---- */
  const register = useCallback(async (params: RegisterParams) => {
    const { apiRegister } = await import("@/lib/api");
    await apiRegister({
      email: params.email,
      password: params.password,
      nom: params.nom,
      prenom: params.prenom,
      adresse: params.adresse,
      ville: params.ville,
      code_postal: params.code_postal,
      telephone: params.telephone,
      domaine: params.domaine,
      accept_mentions_legales: params.acceptMentions,
      accept_cgu: params.acceptCGU,
      accept_protection_donnees: params.acceptProtection,
      accept_newsletter: params.acceptNewsletter,
    });
  }, []);

  /* ---- Logout ---- */
  const logout = useCallback(async () => {
    clearExpirationTimer();
    try {
      if (accessToken) {
        await apiLogout(accessToken);
      }
    } catch {
      // Best-effort backend logout
    }
    setUser(null);
    setIsAdmin(false);
    setAccessToken(null);
    localStorage.removeItem(TOKEN_KEY);
  }, [accessToken]);

  return (
    <AuthContext.Provider value={{ user, isAdmin, accessToken, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
