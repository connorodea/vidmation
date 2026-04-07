"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import {
  type TokenUser,
  clearTokens,
  getAccessToken,
  getRefreshToken,
  getUserFromToken,
  isAuthenticated as checkAuth,
  isTokenExpired,
  msUntilExpiry,
  setTokens,
} from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

// ---------------------------------------------------------------------------
// Context shape
// ---------------------------------------------------------------------------

interface AuthContextValue {
  user: TokenUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<TokenUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ---- helpers ----

  const scheduleRefresh = useCallback(() => {
    if (refreshTimer.current) clearTimeout(refreshTimer.current);

    const ms = msUntilExpiry();
    if (ms <= 0) return;

    // Refresh 60 seconds before expiry (minimum 5 s from now)
    const delay = Math.max(ms - 60_000, 5_000);

    refreshTimer.current = setTimeout(async () => {
      try {
        const refreshToken = getRefreshToken();
        if (!refreshToken) {
          clearTokens();
          setUser(null);
          return;
        }

        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (!res.ok) {
          clearTokens();
          setUser(null);
          router.push("/login");
          return;
        }

        const data = await res.json();
        setTokens(data.access_token, data.refresh_token);
        setUser(getUserFromToken());
        scheduleRefresh();
      } catch {
        clearTokens();
        setUser(null);
      }
    }, delay);
  }, [router]);

  // ---- initial hydration ----

  useEffect(() => {
    if (checkAuth()) {
      setUser(getUserFromToken());
      scheduleRefresh();
    }
    setIsLoading(false);

    return () => {
      if (refreshTimer.current) clearTimeout(refreshTimer.current);
    };
  }, [scheduleRefresh]);

  // ---- auth actions ----

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Login failed" }));
        throw new Error(err.detail || "Invalid email or password");
      }

      const data = await res.json();
      setTokens(data.access_token, data.refresh_token);
      setUser(getUserFromToken());
      scheduleRefresh();
    },
    [scheduleRefresh]
  );

  const signup = useCallback(
    async (name: string, email: string, password: string) => {
      const res = await fetch(`${API_BASE}/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      });

      if (!res.ok) {
        const err = await res
          .json()
          .catch(() => ({ detail: "Signup failed" }));
        throw new Error(err.detail || "Could not create account");
      }

      const data = await res.json();
      setTokens(data.access_token, data.refresh_token);
      setUser(getUserFromToken());
      scheduleRefresh();
    },
    [scheduleRefresh]
  );

  const logout = useCallback(() => {
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
    clearTokens();
    setUser(null);
    router.push("/login");
  }, [router]);

  // ---- value ----

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: !!user && !isTokenExpired(),
      isLoading,
      login,
      signup,
      logout,
    }),
    [user, isLoading, login, signup, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
