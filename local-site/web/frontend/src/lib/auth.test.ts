/**
 * Unit tests for isTokenExpired() utility function.
 *
 * **Validates: Requirements 2.1, 2.4**
 *
 * Tests cover:
 * - Expired tokens (currentTime > exp - 30)
 * - Valid non-expired tokens (currentTime <= exp - 30)
 * - Null/undefined tokens
 * - Malformed tokens (invalid base64, wrong structure)
 * - Missing exp field
 * - Safety margin behavior (30-second window)
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { isTokenExpired } from "./auth";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Create a fake JWT token with the given payload.
 */
function makeToken(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payloadStr = btoa(JSON.stringify(payload));
  const signature = btoa("fakesignature");
  return `${header}.${payloadStr}.${signature}`;
}

/**
 * Create a token with a specific exp timestamp.
 */
function makeTokenWithExp(exp: number): string {
  return makeToken({ sub: "user@test.com", exp, iat: exp - 3600 });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("isTokenExpired", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("null/undefined tokens", () => {
    it("returns true for null token", () => {
      expect(isTokenExpired(null)).toBe(true);
    });

    it("returns true for undefined token", () => {
      expect(isTokenExpired(undefined)).toBe(true);
    });

    it("returns true for empty string token", () => {
      expect(isTokenExpired("")).toBe(true);
    });
  });

  describe("malformed tokens", () => {
    it("returns true for token with only one part", () => {
      expect(isTokenExpired("onlyonepart")).toBe(true);
    });

    it("returns true for token with two parts", () => {
      expect(isTokenExpired("part1.part2")).toBe(true);
    });

    it("returns true for token with four parts", () => {
      expect(isTokenExpired("a.b.c.d")).toBe(true);
    });

    it("returns true for token with invalid base64 payload", () => {
      expect(isTokenExpired("header.!!!invalid!!!.signature")).toBe(true);
    });

    it("returns true for token with non-JSON payload", () => {
      const nonJson = btoa("this is not json");
      expect(isTokenExpired(`header.${nonJson}.signature`)).toBe(true);
    });
  });

  describe("missing exp field", () => {
    it("returns true when payload has no exp field", () => {
      const token = makeToken({ sub: "user@test.com", iat: 1000 });
      expect(isTokenExpired(token)).toBe(true);
    });

    it("returns true when exp is a string instead of number", () => {
      const token = makeToken({ sub: "user@test.com", exp: "not-a-number" });
      expect(isTokenExpired(token)).toBe(true);
    });

    it("returns true when exp is null", () => {
      const token = makeToken({ sub: "user@test.com", exp: null });
      expect(isTokenExpired(token)).toBe(true);
    });
  });

  describe("expired tokens", () => {
    it("returns true for token expired 5 minutes ago", () => {
      const fiveMinutesAgo = Math.floor(Date.now() / 1000) - 300;
      const token = makeTokenWithExp(fiveMinutesAgo);
      expect(isTokenExpired(token)).toBe(true);
    });

    it("returns true for token expired 1 hour ago", () => {
      const oneHourAgo = Math.floor(Date.now() / 1000) - 3600;
      const token = makeTokenWithExp(oneHourAgo);
      expect(isTokenExpired(token)).toBe(true);
    });

    it("returns true for token expired 1 second ago", () => {
      const oneSecondAgo = Math.floor(Date.now() / 1000) - 1;
      const token = makeTokenWithExp(oneSecondAgo);
      expect(isTokenExpired(token)).toBe(true);
    });
  });

  describe("safety margin (30 seconds)", () => {
    it("returns true when token expires in exactly 30 seconds (at boundary)", () => {
      // When exp = now + 30, then exp - 30 = now.
      // Since Date.now()/1000 may have fractional ms > now (floor),
      // currentTime > exp - 30 can be true. Use a clear margin.
      const now = Math.floor(Date.now() / 1000);
      const token = makeTokenWithExp(now + 30);
      // At the exact boundary, the token is considered expired due to
      // fractional time differences (Date.now()/1000 > Math.floor(Date.now()/1000))
      expect(isTokenExpired(token)).toBe(true);
    });

    it("returns true when token expires in 29 seconds (within margin)", () => {
      const now = Math.floor(Date.now() / 1000);
      const token = makeTokenWithExp(now + 29);
      // currentTime > exp - 30 → now > (now + 29) - 30 → now > now - 1 → true
      expect(isTokenExpired(token)).toBe(true);
    });

    it("returns false when token expires in 31 seconds (outside margin)", () => {
      const now = Math.floor(Date.now() / 1000);
      const token = makeTokenWithExp(now + 31);
      // currentTime > exp - 30 → now > (now + 31) - 30 → now > now + 1 → false
      expect(isTokenExpired(token)).toBe(false);
    });
  });

  describe("valid non-expired tokens", () => {
    it("returns false for token expiring in 1 hour", () => {
      const oneHourFromNow = Math.floor(Date.now() / 1000) + 3600;
      const token = makeTokenWithExp(oneHourFromNow);
      expect(isTokenExpired(token)).toBe(false);
    });

    it("returns false for token expiring in 5 minutes", () => {
      const fiveMinutesFromNow = Math.floor(Date.now() / 1000) + 300;
      const token = makeTokenWithExp(fiveMinutesFromNow);
      expect(isTokenExpired(token)).toBe(false);
    });

    it("returns false for token expiring in 24 hours", () => {
      const oneDayFromNow = Math.floor(Date.now() / 1000) + 86400;
      const token = makeTokenWithExp(oneDayFromNow);
      expect(isTokenExpired(token)).toBe(false);
    });
  });

  describe("base64url encoding", () => {
    it("handles tokens with base64url characters (- and _)", () => {
      // Create a payload that produces base64url characters
      const exp = Math.floor(Date.now() / 1000) + 3600;
      const payload = { sub: "user+special/chars@test.com", exp, data: ">>>???" };
      const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
      // Use base64url encoding (replace + with -, / with _)
      const payloadB64 = btoa(JSON.stringify(payload))
        .replace(/\+/g, "-")
        .replace(/\//g, "_")
        .replace(/=+$/, "");
      const signature = btoa("sig").replace(/=+$/, "");
      const token = `${header}.${payloadB64}.${signature}`;

      expect(isTokenExpired(token)).toBe(false);
    });

    it("handles tokens with padding stripped (base64url without =)", () => {
      const exp = Math.floor(Date.now() / 1000) + 3600;
      const payload = { sub: "u@t.co", exp };
      const header = btoa(JSON.stringify({ alg: "HS256" })).replace(/=+$/, "");
      const payloadB64 = btoa(JSON.stringify(payload)).replace(/=+$/, "");
      const signature = btoa("s").replace(/=+$/, "");
      const token = `${header}.${payloadB64}.${signature}`;

      expect(isTokenExpired(token)).toBe(false);
    });
  });
});
