/**
 * Unit tests for useSessionGuard hook.
 *
 * **Validates: Requirements 2.1, 2.4**
 *
 * Tests cover:
 * - visibilitychange triggers token check when tab becomes visible
 * - Expired token causes localStorage clear + redirect to /accueil
 * - Valid token does not trigger any action
 * - Absent token (null) does not trigger redirect
 * - Periodic timer fires every 60 seconds
 * - Cleanup removes listener and clears interval on unmount
 * - No redirect when already on /login or /accueil
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useSessionGuard } from "./useSessionGuard";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeToken(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payloadStr = btoa(JSON.stringify(payload));
  const signature = btoa("fakesignature");
  return `${header}.${payloadStr}.${signature}`;
}

function makeValidToken(): string {
  const exp = Math.floor(Date.now() / 1000) + 3600; // 1 hour from now
  return makeToken({ sub: "user@test.com", exp, iat: exp - 3600 });
}

function makeExpiredToken(): string {
  const exp = Math.floor(Date.now() / 1000) - 300; // 5 minutes ago
  return makeToken({ sub: "user@test.com", exp, iat: exp - 3600 });
}

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

let mockStorage: Record<string, string> = {};
let visibilityState = "visible";

beforeEach(() => {
  mockStorage = {};
  visibilityState = "visible";

  // Mock localStorage
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(
    (key: string) => mockStorage[key] ?? null
  );
  vi.spyOn(Storage.prototype, "removeItem").mockImplementation(
    (key: string) => { delete mockStorage[key]; }
  );

  // Mock document.visibilityState
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    get: () => visibilityState,
  });

  // Mock window.location
  Object.defineProperty(window, "location", {
    configurable: true,
    value: { href: "", pathname: "/dossier/1" },
  });

  vi.useFakeTimers();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useSessionGuard", () => {
  describe("visibilitychange event", () => {
    it("clears token and redirects when tab becomes visible with expired token", () => {
      mockStorage["token"] = makeExpiredToken();

      renderHook(() => useSessionGuard());

      // Simulate tab becoming visible
      visibilityState = "visible";
      document.dispatchEvent(new Event("visibilitychange"));

      expect(Storage.prototype.removeItem).toHaveBeenCalledWith("token");
      expect(window.location.href).toBe("/accueil");
    });

    it("does nothing when tab becomes visible with valid token", () => {
      mockStorage["token"] = makeValidToken();

      renderHook(() => useSessionGuard());

      visibilityState = "visible";
      document.dispatchEvent(new Event("visibilitychange"));

      expect(Storage.prototype.removeItem).not.toHaveBeenCalled();
      expect(window.location.href).toBe("");
    });

    it("does nothing when tab becomes visible with no token", () => {
      // No token in storage

      renderHook(() => useSessionGuard());

      visibilityState = "visible";
      document.dispatchEvent(new Event("visibilitychange"));

      expect(Storage.prototype.removeItem).not.toHaveBeenCalled();
      expect(window.location.href).toBe("");
    });

    it("does nothing when tab becomes hidden", () => {
      mockStorage["token"] = makeExpiredToken();

      renderHook(() => useSessionGuard());

      visibilityState = "hidden";
      document.dispatchEvent(new Event("visibilitychange"));

      expect(Storage.prototype.removeItem).not.toHaveBeenCalled();
      expect(window.location.href).toBe("");
    });
  });

  describe("periodic timer", () => {
    it("checks token every 60 seconds", () => {
      mockStorage["token"] = makeValidToken();

      renderHook(() => useSessionGuard());

      // Advance 60 seconds — token still valid, no action
      vi.advanceTimersByTime(60_000);
      expect(Storage.prototype.removeItem).not.toHaveBeenCalled();

      // Now expire the token
      mockStorage["token"] = makeExpiredToken();

      // Advance another 60 seconds — should detect expired token
      vi.advanceTimersByTime(60_000);
      expect(Storage.prototype.removeItem).toHaveBeenCalledWith("token");
      expect(window.location.href).toBe("/accueil");
    });
  });

  describe("cleanup on unmount", () => {
    it("removes visibilitychange listener on unmount", () => {
      const removeSpy = vi.spyOn(document, "removeEventListener");

      const { unmount } = renderHook(() => useSessionGuard());
      unmount();

      expect(removeSpy).toHaveBeenCalledWith(
        "visibilitychange",
        expect.any(Function)
      );
    });

    it("clears interval on unmount", () => {
      const clearIntervalSpy = vi.spyOn(global, "clearInterval");

      const { unmount } = renderHook(() => useSessionGuard());
      unmount();

      expect(clearIntervalSpy).toHaveBeenCalled();
    });
  });

  describe("redirect loop prevention", () => {
    it("does not redirect when already on /accueil", () => {
      mockStorage["token"] = makeExpiredToken();
      Object.defineProperty(window, "location", {
        configurable: true,
        value: { href: "", pathname: "/accueil" },
      });

      renderHook(() => useSessionGuard());

      visibilityState = "visible";
      document.dispatchEvent(new Event("visibilitychange"));

      expect(Storage.prototype.removeItem).not.toHaveBeenCalled();
      expect(window.location.href).toBe("");
    });

    it("does not redirect when already on /login", () => {
      mockStorage["token"] = makeExpiredToken();
      Object.defineProperty(window, "location", {
        configurable: true,
        value: { href: "", pathname: "/login" },
      });

      renderHook(() => useSessionGuard());

      visibilityState = "visible";
      document.dispatchEvent(new Event("visibilitychange"));

      expect(Storage.prototype.removeItem).not.toHaveBeenCalled();
      expect(window.location.href).toBe("");
    });
  });
});
