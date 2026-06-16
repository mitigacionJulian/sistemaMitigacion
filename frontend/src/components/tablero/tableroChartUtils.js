export const DIAS_CORTO = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']

export const BAR_COMPARE_MARGIN = { top: 52, right: 18, left: 58, bottom: 56 }

export const LEGEND_TOP_PROPS = {
  verticalAlign: 'top',
  align: 'center',
  wrapperStyle: { fontSize: '12px', lineHeight: '16px', paddingBottom: 6 },
  iconType: 'circle',
}

export function riesgoColor(nivel, variante = 'base') {
  const paleta = {
    alto: { base: '#dc2626', light: '#fca5a5', chip: '#fee2e2', text: '#991b1b' },
    medio: { base: '#d97706', light: '#fcd34d', chip: '#fef3c7', text: '#92400e' },
    bajo: { base: '#16a34a', light: '#86efac', chip: '#dcfce7', text: '#166534' },
  }
  return (paleta[nivel] || paleta.bajo)[variante]
}

export function nivelCargaSemana(row) {
  return row.carga_dia_nivel ?? row.riesgo_nivel ?? 'bajo'
}

export function participacionSemanalPct(row) {
  return Number(row.participacion_incidentes_pct ?? row.riesgo_score ?? 0)
}

export function ratioVsUniforme(row) {
  const r = row.ratio_vs_reparto_uniforme
  return r != null && r !== '' ? Number(r) : null
}

export function buildHeatmapGrid(serie, key) {
  const grid = Array.from({ length: 7 }, () => Array(24).fill(0))
  ;(serie || []).forEach((cell) => {
    const d = cell.dia_semana
    const h = cell.hora
    if (d >= 0 && d < 7 && h >= 0 && h < 24) {
      grid[d][h] = Number(cell[key] ?? 0)
    }
  })
  return grid
}

export function mapClaseIncidenteChart(serie) {
  return (serie || []).map((it) => {
    const label = String(it.clase || 'Sin clasificar')
    const short = label.length > 36 ? `${label.slice(0, 33)}…` : label
    return {
      clase: short,
      claseFull: label,
      codigo: it.codigo || '',
      actual: Number(it.incidentes_periodo_actual || 0),
      anterior: Number(it.incidentes_periodo_anterior || 0),
      pctActual: Number(it.porcentaje_actual ?? 0),
      pctAnterior: Number(it.porcentaje_anterior ?? 0),
    }
  })
}

export function mapGravedadChart(serie) {
  const orden = { FATAL: 0, HERIDO: 1, GRAVE: 2, LEVE: 3, OTRO: 9 }
  return (serie || [])
    .filter(
      (it) => (Number(it.victimas_periodo_actual) || 0) > 0 || (Number(it.victimas_periodo_anterior) || 0) > 0,
    )
    .sort((a, b) => (orden[a.codigo] ?? 50) - (orden[b.codigo] ?? 50))
    .map((it) => {
    const label = String(it.gravedad || 'Sin clasificar')
    const short = label.length > 28 ? `${label.slice(0, 25)}…` : label
    return {
      gravedad: short,
      gravedadFull: label,
      codigo: it.codigo || '',
      actual: Number(it.victimas_periodo_actual || 0),
      anterior: Number(it.victimas_periodo_anterior || 0),
      pctActual: Number(it.porcentaje_actual ?? 0),
      pctAnterior: Number(it.porcentaje_anterior ?? 0),
    }
  })
}
