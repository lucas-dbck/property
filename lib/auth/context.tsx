"use client"

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react"
import { api } from "@/lib/api/client"
import { getToken, setToken } from "@/lib/api/client"
import type { AuthUser } from "@/lib/api/types"

const USER_KEY = "roi.user"

interface AuthContextValue {
  user: AuthUser | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name?: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Restore session from localStorage on mount.
  useEffect(() => {
    const token = getToken()
    const stored = typeof window !== "undefined" ? window.localStorage.getItem(USER_KEY) : null
    if (token && stored) {
      try {
        setUser(JSON.parse(stored))
      } catch {
        setUser(null)
      }
    }
    setIsLoading(false)
  }, [])

  const persist = useCallback((u: AuthUser, token: string) => {
    setToken(token)
    setUser(u)
    if (typeof window !== "undefined") window.localStorage.setItem(USER_KEY, JSON.stringify(u))
  }, [])

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api.login({ email, password })
      persist(res.user, res.token)
    },
    [persist],
  )

  const register = useCallback(
    async (email: string, password: string, name?: string) => {
      const res = await api.register({ email, password, name })
      persist(res.user, res.token)
    },
    [persist],
  )

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    if (typeof window !== "undefined") window.localStorage.removeItem(USER_KEY)
  }, [])

  const value = useMemo(
    () => ({ user, isLoading, login, register, logout }),
    [user, isLoading, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
