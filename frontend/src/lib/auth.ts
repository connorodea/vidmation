const ACCESS_TOKEN_KEY = "aividio_access_token";
const REFRESH_TOKEN_KEY = "aividio_refresh_token";

export interface TokenUser {
  id: string;
  email: string;
  name: string;
  exp: number;
}

/**
 * Decode a JWT payload without a library.
 * Does NOT verify the signature — that is the server's responsibility.
 */
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const base64 = token.split(".")[1];
    if (!base64) return null;
    const json = atob(base64.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Token storage
// ---------------------------------------------------------------------------

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(access: string, refresh?: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACCESS_TOKEN_KEY, access);
  if (refresh) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  }
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

// ---------------------------------------------------------------------------
// Derived state helpers
// ---------------------------------------------------------------------------

export function getUserFromToken(): TokenUser | null {
  const token = getAccessToken();
  if (!token) return null;

  const payload = decodeJwtPayload(token);
  if (!payload) return null;

  return {
    id: (payload.sub as string) || (payload.id as string) || "",
    email: (payload.email as string) || "",
    name: (payload.name as string) || "",
    exp: (payload.exp as number) || 0,
  };
}

export function isTokenExpired(token?: string | null): boolean {
  const t = token ?? getAccessToken();
  if (!t) return true;

  const payload = decodeJwtPayload(t);
  if (!payload || typeof payload.exp !== "number") return true;

  // Consider expired 30 seconds before actual expiry to allow buffer
  return Date.now() >= (payload.exp - 30) * 1000;
}

export function isAuthenticated(): boolean {
  const token = getAccessToken();
  return !!token && !isTokenExpired(token);
}

/**
 * Returns the number of milliseconds until the access token expires.
 * Returns 0 if already expired or no token exists.
 */
export function msUntilExpiry(): number {
  const token = getAccessToken();
  if (!token) return 0;

  const payload = decodeJwtPayload(token);
  if (!payload || typeof payload.exp !== "number") return 0;

  const remaining = payload.exp * 1000 - Date.now();
  return Math.max(0, remaining);
}
