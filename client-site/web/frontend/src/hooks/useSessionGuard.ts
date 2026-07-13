"use client";

import { useEffect } from "react";
import { isTokenExpired } from "../lib/auth";

const TOKEN_KEY = "token";
const CHECK_INTERVAL_MS = 60_000; // 60 seconds

/**
 * Paths where we should NOT trigger a redirect (prevent loops).
 */
const EXCLUDED_PATHS = ["/login", "/accueil"];

/**
 * Checks if the current path is one where we should skip redirect logic.
 */
function isExcludedPath(): boolean {
  if (typeof window === "undefined") return true;
  return EXCLUDED_PATHS.some((path) => window.location.pathname.startsWith(path));
}

/**
 * Performs the session check: if a token exists and is expired,
 * clears it and redirects to /accueil.
 * Does nothing if no token is present (user not logged in)
 * or if already on an excluded path.
 */
function checkAndLogout(): void {
  if (isExcludedPath()) return;

  const token = localStorage.getItem(TOKEN_KEY);

  // No token → user is not logged in, no action needed
  if (!token) return;

  // Token exists and is expired → clear and redirect
  if (isTokenExpired(token)) {
    localStorage.removeItem(TOKEN_KEY);
    window.location.href = "/accueil";
  }
}

/**
 * React hook that proactively guards the session by:
 * 1. Checking token validity when the tab becomes visible (visibilitychange)
 * 2. Periodically checking token validity every 60 seconds
 *
 * If an expired token is detected, it is cleared from localStorage
 * and the user is redirected to /accueil.
 *
 * No action is taken when:
 * - No token exists (user not logged in)
 * - Token is valid (not expired)
 * - Already on /login or /accueil (prevent redirect loops)
 */
export function useSessionGuard(): void {
  useEffect(() => {
    // Handler for visibilitychange event
    function handleVisibilityChange(): void {
      if (document.visibilityState === "visible") {
        checkAndLogout();
      }
    }

    // Listen for tab becoming visible
    document.addEventListener("visibilitychange", handleVisibilityChange);

    // Periodic timer to check token validity
    const intervalId = setInterval(checkAndLogout, CHECK_INTERVAL_MS);

    // Cleanup on unmount
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      clearInterval(intervalId);
    };
  }, []);
}
