import { apiFetch } from './client.js'

async function parseReporteResponse(r, fallbackError) {
  if (r.status === 403) {
    throw new Error('Se requiere rol analista para generar reportes.')
  }
  if (!r.ok) {
    const body = await r.json().catch(() => ({}))
    const detail = body.detail
    if (typeof detail === 'string') {
      throw new Error(detail)
    }
    if (r.status === 404) {
      throw new Error(
        'El endpoint de reportes no está disponible en el servidor (404). Reinicie el backend de Django para cargar la ruta nueva.',
      )
    }
    throw new Error(fallbackError)
  }
  return r.json()
}

export async function fetchReportePreview({ seccion = 'preview', titulo = '', notas = '', filtros = {} } = {}) {
  const r = await apiFetch('/reportes/preview/', {
    method: 'POST',
    body: JSON.stringify({ seccion, titulo, notas, filtros }),
  })
  return parseReporteResponse(r, 'No se pudo generar la vista previa del reporte.')
}

export async function fetchReporteTablero({ titulo = '', notas = '', filtros = {}, query = {} } = {}) {
  const r = await apiFetch('/reportes/tablero/', {
    method: 'POST',
    body: JSON.stringify({ titulo, notas, filtros, query }),
  })
  return parseReporteResponse(r, 'No se pudo generar el reporte del tablero.')
}

export async function fetchReporteMapa({ titulo = '', notas = '', filtros = {}, query = {} } = {}) {
  const r = await apiFetch('/reportes/mapa/', {
    method: 'POST',
    body: JSON.stringify({ titulo, notas, filtros, query }),
  })
  return parseReporteResponse(r, 'No se pudo generar el reporte de mapa.')
}

export async function fetchReportePredicciones({ titulo = '', notas = '', filtros = {}, query = {} } = {}) {
  const r = await apiFetch('/reportes/predicciones/', {
    method: 'POST',
    body: JSON.stringify({ titulo, notas, filtros, query }),
  })
  return parseReporteResponse(r, 'No se pudo generar el reporte de predicciones.')
}

export async function fetchReporteForSeccion({
  seccion,
  titulo = '',
  notas = '',
  filtros = {},
  query = {},
}) {
  if (seccion === 'tablero') {
    return fetchReporteTablero({ titulo, notas, filtros, query })
  }
  if (seccion === 'mapa') {
    return fetchReporteMapa({ titulo, notas, filtros, query })
  }
  if (seccion === 'predicciones') {
    return fetchReportePredicciones({ titulo, notas, filtros, query })
  }
  return fetchReportePreview({ seccion, titulo, notas, filtros })
}