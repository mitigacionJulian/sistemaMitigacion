import { decodeChoroplethPayload } from '../map/choroplethDecode.js'
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  isIdleExpired,
  setTokens,
  touchActivity,
} from '../auth/tokenStorage.js'

const API_PREFIX = '/api'

let refreshInFlight = null

async function refreshAccessToken() {
  const refresh = getRefreshToken()
  if (!refresh) return false
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_PREFIX}/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
      .then(async (r) => {
        if (!r.ok) return false
        const body = await r.json()
        if (body.access) {
          setTokens({ access: body.access, refresh: body.refresh || refresh })
          return true
        }
        return false
      })
      .finally(() => {
        refreshInFlight = null
      })
  }
  return refreshInFlight
}

export async function apiFetch(path, options = {}) {
  if (isIdleExpired()) {
    clearTokens()
    throw new Error('Sesión cerrada por inactividad (15 min).')
  }

  const method = (options.method || 'GET').toUpperCase()
  const headers = new Headers(options.headers)

  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }

  const access = getAccessToken()
  if (access) {
    headers.set('Authorization', `Bearer ${access}`)
    touchActivity()
  }

  let r = await fetch(`${API_PREFIX}${path}`, {
    ...options,
    credentials: 'omit',
    headers,
    ...(method === 'GET' ? { cache: 'no-store' } : {}),
  })

  if (r.status === 401 && getRefreshToken()) {
    const ok = await refreshAccessToken()
    if (ok) {
      headers.set('Authorization', `Bearer ${getAccessToken()}`)
      r = await fetch(`${API_PREFIX}${path}`, {
        ...options,
        credentials: 'omit',
        headers,
        ...(method === 'GET' ? { cache: 'no-store' } : {}),
      })
    }
  }

  return r
}

export async function fetchMe() {
  const access = getAccessToken()
  if (!access || isIdleExpired()) {
    clearTokens()
    return null
  }
  const r = await apiFetch('/auth/me/')
  if (r.status === 403 || r.status === 401) {
    clearTokens()
    return null
  }
  if (!r.ok) throw new Error('No se pudo obtener la sesión')
  return r.json()
}

export async function login(username, password) {
  const r = await fetch(`${API_PREFIX}/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({}))
    throw new Error(err.detail || 'Error al iniciar sesión')
  }
  const data = await r.json()
  setTokens({ access: data.access, refresh: data.refresh })
  return data.user
}

export async function logout() {
  const access = getAccessToken()
  if (access) {
    try {
      await apiFetch('/auth/logout/', { method: 'POST' })
    } catch {
      /* ignore */
    }
  }
  clearTokens()
}

export async function register(payload) {
  const r = await fetch(`${API_PREFIX}/auth/register/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({}))
    const msg =
      typeof err === 'object' && err && 'detail' in err ? String(err.detail) : formatFieldErrors(err)
    throw new Error(msg || 'Error al registrar')
  }
  const data = await r.json()
  const tokens = data.tokens || { access: data.access, refresh: data.refresh }
  setTokens(tokens)
  const { tokens: _t, access: _a, refresh: _r, ...user } = data
  return user
}

function formatFieldErrors(err) {
  if (!err || typeof err !== 'object') return null
  const parts = []
  for (const [k, v] of Object.entries(err)) {
    if (Array.isArray(v)) parts.push(`${k}: ${v.join(' ')}`)
    else if (typeof v === 'string') parts.push(v)
  }
  return parts.length ? parts.join(' · ') : null
}

export async function requestPasswordReset(payload) {
  const r = await fetch(`${API_PREFIX}/auth/password-reset/request/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    throw new Error(body.detail || formatFieldErrors(body) || 'No se pudo solicitar recuperación')
  }
  return body
}

export async function confirmPasswordReset(payload) {
  const r = await fetch(`${API_PREFIX}/auth/password-reset/confirm/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    throw new Error(body.detail || formatFieldErrors(body) || 'No se pudo restablecer la contraseña')
  }
  return body
}

export async function fetchDashboardMock() {
  const r = await apiFetch('/dashboard/mock/')
  if (!r.ok) throw new Error('No se pudo cargar el tablero de demostración')
  return r.json()
}

function buildQuery(params) {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') qs.set(k, String(v))
  })
  const q = qs.toString()
  return q ? `?${q}` : ''
}

function detailFromBody(body, fallback) {
  if (!body || typeof body !== 'object') return fallback
  const d = body.detail
  const dbg = body.debug && typeof body.debug === 'string' ? ` — ${body.debug}` : ''
  if (typeof d === 'string') return `${d}${dbg}`
  if (Array.isArray(d)) return `${d.join(' ')}${dbg}`
  if (dbg) return `${fallback}${dbg}`
  return fallback
}

export async function fetchDashboardRangoFechas() {
  const r = await apiFetch('/dashboard/rango-fechas/')
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    throw new Error(
      detailFromBody(body, `No se pudo obtener el rango de fechas (${r.status})`),
    )
  }
  return body
}

const PUNTOS_WORKER_THRESHOLD = 2000
let expandWorker = null
let expandReqId = 0

function expandPuntosMapaSync(data) {
  if (!data?.puntos?.length || data.meta?.formato_puntos !== 'compacto') return data
  const cols = data.meta.columnas_puntos || [
    'id',
    'latitud',
    'longitud',
    'radicado',
    'fecha_incidente',
    'clase_incidente',
  ]
  const idx = Object.fromEntries(cols.map((c, i) => [c, i]))
  return {
    ...data,
    puntos: data.puntos.map((row) => ({
      id: row[idx.id],
      latitud: row[idx.latitud],
      longitud: row[idx.longitud],
      radicado: row[idx.radicado],
      fecha_incidente: row[idx.fecha_incidente],
      clase_incidente: row[idx.clase_incidente] ?? '',
    })),
  }
}

function getExpandWorker() {
  if (!expandWorker) {
    expandWorker = new Worker(new URL('../workers/expandPuntosMapa.worker.js', import.meta.url), {
      type: 'module',
    })
  }
  return expandWorker
}

function expandPuntosMapaAsync(data) {
  return new Promise((resolve, reject) => {
    const worker = getExpandWorker()
    const id = ++expandReqId
    const onMessage = (ev) => {
      if (ev.data?.id !== id) return
      worker.removeEventListener('message', onMessage)
      if (ev.data.error) reject(new Error(ev.data.error))
      else resolve(ev.data.data)
    }
    worker.addEventListener('message', onMessage)
    worker.postMessage({ id, data })
  })
}

async function expandPuntosMapa(data) {
  if (!data?.puntos?.length || data.meta?.formato_puntos !== 'compacto') return data
  if (data.puntos.length < PUNTOS_WORKER_THRESHOLD) return expandPuntosMapaSync(data)
  try {
    return await expandPuntosMapaAsync(data)
  } catch {
    return expandPuntosMapaSync(data)
  }
}

export async function fetchDashboardIncidentesMapa(params = {}) {
  const r = await apiFetch(`/dashboard/incidentes-mapa/${buildQuery(params)}`)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(
      body,
      `No se pudo cargar el mapa de incidentes (${r.status}).`,
    )
    throw new Error(msg)
  }
  return expandPuntosMapa(body)
}

export async function fetchDashboardMapaDetalle(params = {}) {
  const q = buildQuery(params)
  const path = q ? `/dashboard/mapa-detalle${q}` : '/dashboard/mapa-detalle/'
  const r = await apiFetch(path)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(body, `No se pudo cargar el mapa detalle (${r.status}).`)
    throw new Error(msg)
  }
  const choropleth = decodeChoroplethPayload(body.choropleth)
  const puntosPayload = await expandPuntosMapa({
    meta: body.meta || body.puntos_meta,
    puntos: body.puntos,
  })
  return {
    meta: body.meta,
    choropleth,
    puntos: puntosPayload.puntos,
    puntos_meta: puntosPayload.meta || body.puntos_meta,
  }
}

export async function fetchDashboardHotspotsCuadricula(params = {}) {
  const r = await apiFetch(`/dashboard/hotspots-cuadricula/${buildQuery(params)}`)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(
      body,
      `No se pudo cargar la cuadrícula de hotspots (${r.status}).`,
    )
    throw new Error(msg)
  }
  return body
}

export async function fetchDashboardKpis(params = {}) {
  const r = await apiFetch(`/dashboard/kpis/${buildQuery(params)}`)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(
      body,
      `No se pudieron cargar los indicadores (${r.status}). ¿PostgreSQL encendido y variables POSTGRES_* correctas?`,
    )
    throw new Error(msg)
  }
  return body
}

export async function fetchDashboardEvolucionMensual(params = {}) {
  const r = await apiFetch(`/dashboard/evolucion-mensual/${buildQuery(params)}`)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(
      body,
      `No se pudo cargar la evolución mensual (${r.status}).`,
    )
    throw new Error(msg)
  }
  return body
}

export async function fetchDashboardPrediccionesMensuales(params = {}) {
  const r = await apiFetch(`/dashboard/predicciones-mensuales/${buildQuery(params)}`)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(
      body,
      `No se pudo cargar la proyección mensual (${r.status}).`,
    )
    throw new Error(msg)
  }
  return body
}

export async function fetchDashboardPrioridadTerritorial(params = {}) {
  const r = await apiFetch(`/dashboard/prioridad-territorial/${buildQuery(params)}`)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(
      body,
      `No se pudo cargar la prioridad territorial (${r.status}).`,
    )
    throw new Error(msg)
  }
  return body
}

export async function fetchDashboardProporcionFatalesMensual(params = {}) {
  const r = await apiFetch(`/dashboard/proporcion-fatales-mensual/${buildQuery(params)}`)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(
      body,
      `No se pudo cargar la proporción de fatales (${r.status}).`,
    )
    throw new Error(msg)
  }
  return body
}

export async function fetchDashboardCargaEsperadaTerritorial(params = {}) {
  const r = await apiFetch(`/dashboard/carga-esperada-territorial/${buildQuery(params)}`)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(
      body,
      `No se pudo cargar la carga esperada (${r.status}).`,
    )
    throw new Error(msg)
  }
  return body
}

export async function fetchDashboardPorDiaSemana(params = {}) {
  const r = await apiFetch(`/dashboard/por-dia-semana/${buildQuery(params)}`)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(
      body,
      `No se pudo cargar la serie por día de la semana (${r.status}).`,
    )
    throw new Error(msg)
  }
  return body
}

export async function fetchDashboardMatrizDiaHora(params = {}) {
  const r = await apiFetch(`/dashboard/matriz-dia-hora/${buildQuery(params)}`)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(
      body,
      `No se pudo cargar la matriz día/hora (${r.status}).`,
    )
    throw new Error(msg)
  }
  return body
}

export async function fetchDashboardMatrizDiaHoraProyectada(params = {}) {
  const r = await apiFetch(`/dashboard/matriz-dia-hora-proyectada/${buildQuery(params)}`)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(
      body,
      `No se pudo cargar la matriz día/hora proyectada (P12) (${r.status}).`,
    )
    throw new Error(msg)
  }
  return body
}

export async function fetchDashboardPorDiaSemanaProyectado(params = {}) {
  const r = await apiFetch(`/dashboard/por-dia-semana-proyectado/${buildQuery(params)}`)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(
      body,
      `No se pudo cargar la proyección por día de semana (P13) (${r.status}).`,
    )
    throw new Error(msg)
  }
  return body
}

export async function fetchDashboardTops(params = {}) {
  /** Siempre `/dashboard/tops/` + `?…` para que coincida con Django (`dashboard/tops/`). */
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') qs.set(k, String(v))
  })
  const qstr = qs.toString()
  const path = qstr ? `/dashboard/tops/?${qstr}` : '/dashboard/tops/'
  const r = await apiFetch(path)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(body, `No se pudieron cargar los rankings (${r.status}).`)
    throw new Error(msg)
  }
  return body
}

export async function fetchDashboardDistribucionClaseIncidente(params = {}) {
  const r = await apiFetch(`/dashboard/distribucion-clase-incidente/${buildQuery(params)}`)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(
      body,
      `No se pudo cargar la distribución por clase de incidente (${r.status}).`,
    )
    throw new Error(msg)
  }
  return body
}

export async function fetchDashboardCatalogos() {
  const r = await apiFetch('/dashboard/catalogos/')
  if (!r.ok) throw new Error('No se pudieron cargar los catálogos')
  return r.json()
}

export async function fetchDashboardBarrios(comunaId) {
  const r = await apiFetch(`/dashboard/barrios/${buildQuery({ comuna_id: comunaId })}`)
  if (!r.ok) throw new Error('No se pudieron cargar los barrios')
  return r.json()
}

export async function fetchDashboardCalidadTerritorio(params = {}) {
  const r = await apiFetch(`/dashboard/calidad-territorio/${buildQuery(params)}`)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(
      body,
      `No se pudo cargar la calidad territorial G03 (${r.status}).`,
    )
    throw new Error(msg)
  }
  return body
}

export async function fetchDashboardDensidadTerritorial(params = {}) {
  const r = await apiFetch(`/dashboard/densidad-territorial/${buildQuery(params)}`)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(
      body,
      `No se pudo cargar densidad territorial G01 (${r.status}).`,
    )
    throw new Error(msg)
  }
  return body
}

export async function fetchDashboardHotspotsRanking(params = {}) {
  const r = await apiFetch(`/dashboard/hotspots-ranking/${buildQuery(params)}`)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(
      body,
      `No se pudo cargar ranking de celdas G06 (${r.status}).`,
    )
    throw new Error(msg)
  }
  return body
}

export async function fetchDashboardChoroplethTerritorial(params = {}) {
  const q = buildQuery(params)
  const path = q ? `/dashboard/choropleth-territorial${q}` : '/dashboard/choropleth-territorial/'
  const r = await apiFetch(path)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(
      body,
      `No se pudo cargar la coroplética territorial (${r.status}).`,
    )
    throw new Error(msg)
  }
  return decodeChoroplethPayload(body)
}

export async function fetchDashboardComunasGeojson(params = {}) {
  const r = await apiFetch(`/dashboard/comunas-geojson/${buildQuery(params)}`)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(body, `No se pudieron cargar límites comunales (${r.status}).`)
    throw new Error(msg)
  }
  return body
}
