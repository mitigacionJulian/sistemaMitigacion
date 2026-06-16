export function formatReporteFecha(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('es-CO', {
    dateStyle: 'long',
    timeStyle: 'short',
  })
}

export function formatReporteFechaCorta(iso) {
  if (!iso) return ''
  const [y, m, day] = iso.split('-').map(Number)
  const d = new Date(y, m - 1, day)
  return d.toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function formatReporteNumero(value, options = {}) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return n.toLocaleString('es-CO', options)
}

export function formatReporteVariacion(pct) {
  if (pct === null || pct === undefined) return 'sin variación % (denominador 0)'
  const sign = pct > 0 ? '+' : ''
  return `${sign}${formatReporteNumero(pct, { maximumFractionDigits: 2 })}% vs año anterior`
}

/** Área en km² de una celda cuadrada de lado tamanoCeldaM (metros). */
export function areaCeldaKm2(tamanoCeldaM) {
  const m = Number(tamanoCeldaM)
  if (!Number.isFinite(m) || m <= 0) return null
  return (m / 1000) ** 2
}

/**
 * Convierte densidad / km² a incidentes por celda: densidad × área celda (km²).
 * En malla regular equivale a densidad ÷ (1.000.000 / tamaño²).
 */
export function incidentesPorCeldaDesdeDensidad(densidadPorKm2, areaKm2) {
  const d = Number(densidadPorKm2)
  const a = Number(areaKm2)
  if (!Number.isFinite(d) || !Number.isFinite(a) || a <= 0) return null
  return d * a
}

export function divisorDensidadMallaRegular(tamanoCeldaM) {
  const area = areaCeldaKm2(tamanoCeldaM)
  if (!area) return null
  return 1 / area
}