"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from "react";
import { Amplify } from "aws-amplify";
import { signIn, signOut, fetchAuthSession } from "aws-amplify/auth";
import { apiLogin, apiLogout, apiGetProfile, type Profile } from "@/lib/api";

/* ------------------------------------------------------------------ */
/*  Amplify configuration                                              */
/* ------------------------------------------------------------------ */

const COGNITO_USER_POOL_ID = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || "";
const COGNITO_APP_CLIENT_ID = process.env.NEXT_PUBLIC_COGNITO_APP_CLIENT_ID || "";
const AWS_REGION = process.env.NEXT_PUBLIC_AWS_REGION || "eu-west-3";

if (COGNITO_USER_POOL_ID && COGNITO_APP_CLIENT_ID) {
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: COGNITO_USER_POOL_ID,
        userPoolClientId: COGNITO_APP_CLIENT_ID,
      },
    },
  });
}

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
const DEV_TOKEN_KEY = "judi_dev_token";

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/* ------------------------------------------------------------------ */
/*  Provider                                                           */
/* ------------------------------------------------------------------ */

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  /* Restore session on mount */
  useEffect(() => {
    restoreSession();
  }, []);

  async function restoreSession() {
    try {
      // 1. Try Amplify session (production with Cognito)
      const session = await fetchAuthSession();
      const token = session.tokens?.accessToken?.toString();
      if (token) {
        setAccessToken(token);
        const profile = await apiGetProfile(token);
        applyProfile(profile, token);
        return;
      }
    } catch {
      // No Amplify session
    }

    // 2. Try dev token from localStorage (dev mode)
    try {
      const devToken = localStorage.getItem(DEV_TOKEN_KEY);
      if (devToken) {
        const profile = await apiGetProfile(devToken);
        applyProfile(profile, devToken);
        return;
      }
    } catch {
      localStorage.removeItem(DEV_TOKEN_KEY);
    }

    setLoading(false);
  }

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
    // Persist dev tokens for page reload survival
    if (token.startsWith("dev-token-")) {
      localStorage.setItem(DEV_TOKEN_KEY, token);
    }
    setLoading(false);
  }

  /* ---- Login via backend (Cognito + Captcha verification) ---- */
  const login = useCallback(async (email: string, password: string, captchaToken: string) => {
    // Call the backend which validates captcha + authenticates via Cognito
    const tokens = await apiLogin(email, password, captchaToken);
    setAccessToken(tokens.access_token);

    // Also sign in via Amplify so the session is persisted client-side
    try {
      await signIn({ username: email, password });
    } catch {
      // Amplify sign-in may fail if already signed in; tokens from backend are authoritative
    }

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
    try {
      if (accessToken) {
        await apiLogout(accessToken);
      }
    } catch {
      // Best-effort backend logout
    }
    try {
      await signOut();
    } catch {
      // Best-effort Amplify sign-out
    }
    setUser(null);
    setIsAdmin(false);
    setAccessToken(null);
    localStorage.removeItem(DEV_TOKEN_KEY);
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
