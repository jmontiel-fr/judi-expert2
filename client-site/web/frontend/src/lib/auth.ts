/**
 * Auth utilities — Token expiration checking for session management.
 *
 * Provides client-side JWT expiration detection to enable proactive
 * session timeout handling. Used by the session guard hook and
 * the 401 interceptor to determine if a token has expired.
 */

/**
 * Checks whether a JWT token is expired, malformed, or absent.
 *
 * Decodes the JWT payload (base64 part 2) and compares the `exp` claim
 * against the current time with a 30-second safety margin.
 *
 * @param token - The JWT token string, or null/undefined if no token exists.
 * @returns `true` if the token is expired, malformed, or null/undefined.
 *          `false` only for valid, non-expired tokens.
 */
export function isTokenExpired(token: string | null | undefined): boolean {
  // Null or undefined token → considered expired (no valid session)
  if (!token) {
    return true;
  }

  try {
    // JWT structure: header.payload.signature
    const parts = token.split(".");
    if (parts.length !== 3) {
      return true; // Malformed token
    }

    // Decode the payload (part 2) from base64url
    const payloadBase64 = parts[1];

    // Convert base64url to standard base64
    let base64 = payloadBase64.replace(/-/g, "+").replace(/_/g, "/");

    // Add padding if needed
    const padding = 4 - (base64.length % 4);
    if (padding !== 4) {
      base64 += "=".repeat(padding);
    }

    const payloadJson = atob(base64);
    const payload = JSON.parse(payloadJson);

    // Missing exp field → treat as expired
    if (typeof payload.exp !== "number") {
      return true;
    }

    // Compare with current time, applying 30-second safety margin
    const currentTime = Date.now() / 1000;
    return currentTime > payload.exp - 30;
  } catch {
    // Any decoding or parsing error → treat as expired
    return true;
  }
}
