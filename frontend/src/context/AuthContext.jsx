import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import * as api from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const me = await api.fetchMe()
      setUser(me)
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const login = useCallback(async (username, password) => {
    const u = await api.login(username, password)
    setUser(u)
  }, [])

  const logout = useCallback(async () => {
    await api.logout()
    setUser(null)
  }, [])

  const register = useCallback(async (payload) => {
    const u = await api.register(payload)
    setUser(u)
  }, [])

  const value = useMemo(
    () => ({ user, loading, refresh, login, logout, register }),
    [user, loading, refresh, login, logout, register],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components -- hook + provider en un solo módulo
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return ctx
}
