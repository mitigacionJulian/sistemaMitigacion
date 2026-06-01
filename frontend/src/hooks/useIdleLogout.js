import { useEffect } from 'react'
import { IDLE_TIMEOUT_MS, getAccessToken, getLastActivity, touchActivity } from '../auth/storage.js'

const EVENTS = ['mousedown', 'keydown', 'scroll', 'touchstart']

/**
 * Cierra sesión tras 20 min sin actividad (complementa la caducidad del JWT).
 */
export function useIdleLogout(onIdle, enabled = true) {
  useEffect(() => {
    if (!enabled || !onIdle || !getAccessToken()) return undefined

    if (!getLastActivity()) {
      touchActivity()
    }

    const bump = () => touchActivity()
    EVENTS.forEach((ev) => window.addEventListener(ev, bump, { passive: true }))

    const interval = window.setInterval(() => {
      if (!getAccessToken()) return
      const last = getLastActivity()
      if (!last) return
      if (Date.now() - last > IDLE_TIMEOUT_MS) {
        onIdle()
      }
    }, 30_000)

    return () => {
      EVENTS.forEach((ev) => window.removeEventListener(ev, bump))
      window.clearInterval(interval)
    }
  }, [enabled, onIdle])
}
