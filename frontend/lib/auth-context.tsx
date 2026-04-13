"use client"

import { createContext, useContext, useState, useEffect, type ReactNode } from "react"

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

// Mock user for demo purposes
const mockUser: User = {
  id: "usr_123456",
  email: "demo@aividio.com",
  name: "Demo User",
  subscription_tier: "pro",
  subscription_expires_at: "2026-12-31T23:59:59Z",
  is_active: true,
  is_admin: false,
  is_verified: true,
  created_at: "2024-01-15T10:30:00Z",
  last_login_at: "2026-04-07T09:00:00Z",
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Check for existing session
    const checkAuth = async () => {
      const token = localStorage.getItem("access_token")
      if (token) {
        // In production, validate token with API
        setUser(mockUser)
      }
      setIsLoading(false)
    }
    checkAuth()
  }, [])

  const login = async (email: string, password: string) => {
    setIsLoading(true)
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))
    
    if (email && password) {
      localStorage.setItem("access_token", "mock_jwt_token")
      localStorage.setItem("refresh_token", "mock_refresh_token")
      setUser({ ...mockUser, email })
    } else {
      throw new Error("Invalid email or password")
    }
    setIsLoading(false)
  }

  const signup = async (name: string, email: string, password: string) => {
    setIsLoading(true)
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))
    
    if (name && email && password) {
      localStorage.setItem("access_token", "mock_jwt_token")
      localStorage.setItem("refresh_token", "mock_refresh_token")
      setUser({ ...mockUser, name, email, subscription_tier: "free", is_verified: false })
    } else {
      throw new Error("All fields are required")
    }
    setIsLoading(false)
  }

  const logout = async () => {
    localStorage.removeItem("access_token")
    localStorage.removeItem("refresh_token")
    setUser(null)
  }

  const refreshUser = async () => {
    // In production, fetch fresh user data
    setUser(mockUser)
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
