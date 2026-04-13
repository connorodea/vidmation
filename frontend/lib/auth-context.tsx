"use client"

import { createContext, useContext, useState, useEffect, type ReactNode } from "react"
import { authFetch, clearTokens } from "@/lib/api"

export type SubscriptionTier = "free" | "pro" | "business"

export interface User {
  id: string
  email: string
  name: string
  subscription_tier: SubscriptionTier
  subscription_expires_at: string | null
  is_active: boolean
  is_admin: boolean
  is_verified: boolean
  created_at: string
  last_login_at: string
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (name: string, email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem("access_token")
      if (token) {
        try {
          const userData = await authFetch<User>("/me")
          setUser(userData)
        } catch {
          // Token expired or invalid
          clearTokens()
        }
      }
      setIsLoading(false)
    }
    checkAuth()
  }, [])

  const login = async (email: string, password: string) => {
    setIsLoading(true)
    try {
      const res = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || "Invalid email or password")
      }

      const tokens = await res.json()
      localStorage.setItem("access_token", tokens.access_token)
      localStorage.setItem("refresh_token", tokens.refresh_token)

      // Fetch user profile
      const userData = await authFetch<User>("/me")
      setUser(userData)
    } finally {
      setIsLoading(false)
    }
  }

  const signup = async (name: string, email: string, password: string) => {
    setIsLoading(true)
    try {
      const res = await fetch("/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || "Signup failed")
      }

      const tokens = await res.json()
      localStorage.setItem("access_token", tokens.access_token)
      localStorage.setItem("refresh_token", tokens.refresh_token)

      // Fetch user profile
      const userData = await authFetch<User>("/me")
      setUser(userData)
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async () => {
    try {
      await authFetch("/logout", { method: "POST" })
    } catch {
      // Logout may fail if token is already expired — that's fine
    }
    clearTokens()
    setUser(null)
  }

  const refreshUser = async () => {
    try {
      const userData = await authFetch<User>("/me")
      setUser(userData)
    } catch {
      clearTokens()
      setUser(null)
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        signup,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
