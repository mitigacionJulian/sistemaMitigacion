const ACCESS_KEY = 'sg_access'
const REFRESH_KEY = 'sg_refresh'
const ACTIVITY_KEY = 'sg_last_activity'

export function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY)
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY)
}

export function setTokens({ access, refresh }) {
  if (access) localStorage.setItem(ACCESS_KEY, access)
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  touchActivity()
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
  localStorage.removeItem(ACTIVITY_KEY)
}

export function touchActivity() {
  localStorage.setItem(ACTIVITY_KEY, String(Date.now()))
}

export function getLastActivity() {
  const raw = localStorage.getItem(ACTIVITY_KEY)
  return raw ? Number(raw) : null
}

export const IDLE_MS = 15 * 60 * 1000

export function isIdleExpired() {
  const last = getLastActivity()
  if (!last) return false
  return Date.now() - last > IDLE_MS
}
