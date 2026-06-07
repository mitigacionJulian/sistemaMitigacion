import { getAccessToken, touchActivity } from '../auth/tokenStorage.js'

const API_PREFIX = '/api'

function detailFromBody(body, fallback) {
  if (body && typeof body.detail === 'string') return body.detail
  return fallback
}

/**
 * Peticiones al asistente. Envía JWT si hay sesión (habilita predicciones para analistas).
 */
export async function agentFetch(path, options = {}) {
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }
  const access = getAccessToken()
  if (access) {
    headers.set('Authorization', `Bearer ${access}`)
    touchActivity()
  }
  const r = await fetch(`${API_PREFIX}${path}`, {
    ...options,
    credentials: 'omit',
    headers,
    cache: 'no-store',
  })
  return r
}

export async function fetchAgentInfo() {
  const r = await agentFetch('/agent/info/')
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    throw new Error(detailFromBody(body, `No se pudo cargar información del asistente (${r.status}).`))
  }
  return body
}

export async function fetchAgentChat({ message, model, history, skipCache = false }) {
  const r = await agentFetch('/agent/chat/', {
    method: 'POST',
    body: JSON.stringify({ message, model, history, skip_cache: skipCache }),
  })
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    throw new Error(detailFromBody(body, `No se pudo procesar la consulta (${r.status}).`))
  }
  return body
}
