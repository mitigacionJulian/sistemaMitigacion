import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import * as api from '../api/client.js'
import { clearTokens, getAccessToken, IDLE_MS, isIdleExpired, touchActivity } from '../auth/tokenStorage.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      if (isIdleExpired()) {
        clearTokens()
        setUser(null)
        return
      }
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

  useEffect(() => {
    const onActivity = () => {
      if (getAccessToken()) touchActivity()
    }
    window.addEventListener('pointerdown', onActivity)
    window.addEventListener('keydown', onActivity)
    return () => {
      window.removeEventListener('pointerdown', onActivity)
      window.removeEventListener('keydown', onActivity)
    }
  }, [])

  useEffect(() => {
    const id = window.setInterval(() => {
      if (isIdleExpired() && getAccessToken()) {
        clearTokens()
        setUser(null)
      }
    }, 60_000)
    return () => window.clearInterval(id)
  }, [])

  const login = useCallback(async (username, password) => {
    const u = await api.login(username, password)
    setUser(u)
    return u
  }, [])

  const logout = useCallback(async () => {
    await api.logout()
    setUser(null)
  }, [])

  const register = useCallback(async (payload) => {
    const u = await api.register(payload)
    setUser(u)
    return u
  }, [])

  const isAnalista = user?.perfil?.rol_codigo === 'analista'

  const value = useMemo(
    () => ({
      user,
      loading,
      refresh,
      login,
      logout,
      register,
      isAnalista,
      idleMs: IDLE_MS,
    }),
    [user, loading, refresh, login, logout, register, isAnalista],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return ctx
}
