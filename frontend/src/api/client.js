const API_PREFIX = '/api'

function getCookie(name) {
  const m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'))
  return m ? decodeURIComponent(m[2]) : null
}

let csrfReady = null

export function ensureCsrf() {
  if (!csrfReady) {
    csrfReady = fetch(`${API_PREFIX}/auth/csrf/`, {
      credentials: 'include',
    }).then(() => undefined)
  }
  return csrfReady
}

export async function apiFetch(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const headers = new Headers(options.headers)

  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }

  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    await ensureCsrf()
    const token = getCookie('csrftoken')
    if (token) headers.set('X-CSRFToken', token)
  }

  return fetch(`${API_PREFIX}${path}`, {
    ...options,
    credentials: 'include',
    headers,
    ...(method === 'GET' ? { cache: 'no-store' } : {}),
  })
}

export async function fetchMe() {
  const r = await apiFetch('/auth/me/')
  if (r.status === 403 || r.status === 401) return null
  if (!r.ok) throw new Error('No se pudo obtener la sesión')
  return r.json()
}

export async function login(username, password) {
  const r = await apiFetch('/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({}))
    throw new Error(err.detail || 'Error al iniciar sesión')
  }
  return r.json()
}

export async function logout() {
  const r = await apiFetch('/auth/logout/', { method: 'POST' })
  if (!r.ok && r.status !== 204) throw new Error('Error al cerrar sesión')
  csrfReady = null
}

export async function register(payload) {
  const r = await apiFetch('/auth/register/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({}))
    const msg =
      typeof err === 'object' && err && 'detail' in err ? String(err.detail) : 'Error al registrar'
    throw new Error(msg)
  }
  return r.json()
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

export async function fetchDashboardCargaEsperadaEspacial(params = {}) {
  const r = await apiFetch(`/dashboard/carga-esperada-espacial/${buildQuery(params)}`)
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = detailFromBody(
      body,
      `No se pudo cargar la carga espacial (fase C) (${r.status}).`,
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
