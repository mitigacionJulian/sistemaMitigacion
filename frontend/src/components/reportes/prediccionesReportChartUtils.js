export function serieObservados(r) {
  return r.observados ?? r.incidentes_observados ?? 0
}

export function serieAjuste(r) {
  const v = r.ajuste_modelo ?? r.incidentes_ajuste_lineal
  return v != null ? v : null
}

export function buildPrediccionesLineData(serieHistorica, proyeccion) {
  const h = (serieHistorica || []).map((r) => ({
    mes: r.mes_etiqueta,
    observados: serieObservados(r),
    ajuste: serieAjuste(r),
  }))
  const pr = (proyeccion || []).map((r) => ({
    mes: r.mes_etiqueta,
    observados: null,
    ajuste: serieAjuste(r),
  }))
  return [...h, ...pr]
}

export function buildProporcionLineData(serieHistorica, proyeccion) {
  const h = (serieHistorica || []).map((r) => ({
    mes: r.mes_etiqueta,
    pct: r.pct_fatales,
    ajuste: r.ajuste_pct,
  }))
  let lastAjuste = null
  for (const row of h) {
    if (row.ajuste != null) lastAjuste = row.ajuste
  }
  if (h.length > 0 && h[h.length - 1].ajuste == null && lastAjuste != null) {
    h[h.length - 1] = { ...h[h.length - 1], ajuste: lastAjuste }
  }

  const pr = (proyeccion || []).map((r) => ({
    mes: r.mes_etiqueta,
    pct: null,
    ajuste: r.pct_fatales_proyectado ?? r.ajuste_pct,
  }))
  if (pr.length > 0 && h.length > 0) {
    const ultimoHist = h[h.length - 1].ajuste
    if (ultimoHist != null && pr[0].ajuste != null && pr[0].ajuste === 0 && ultimoHist > 0) {
      pr[0] = { ...pr[0], ajuste: ultimoHist }
    }
  }
  return [...h, ...pr]
}

export function buildCargaComparativaData(ranking, nivel) {
  return [...(ranking || [])]
    .sort((a, b) => (b.carga_proyectada_horizonte ?? 0) - (a.carga_proyectada_horizonte ?? 0))
    .slice(0, 12)
    .map((row) => {
      const nombre =
        nivel === 'barrio' ? (row.barrio_nombre ?? '—') : (row.comuna_nombre ?? '—')
      const etiqueta =
        nivel === 'barrio' && row.comuna_nombre ? `${nombre} (${row.comuna_nombre})` : nombre
      return {
        nombre: etiqueta,
        carga: Number(row.carga_proyectada_horizonte ?? 0),
        categoria: row.categoria_esperada ?? 'bajo',
        incidentes: row.incidentes_periodo ?? 0,
        rank: row.rank,
      }
    })
}

export function buildPrioridadChartData(ranking, nivel, limite = 12) {
  return [...(ranking || [])]
    .slice(0, limite)
    .map((row) => {
      const nombre =
        nivel === 'barrio' ? (row.barrio_nombre ?? '—') : (row.comuna_nombre ?? '—')
      const etiqueta =
        nivel === 'barrio' && row.comuna_nombre ? `${nombre} (${row.comuna_nombre})` : nombre
      const short = etiqueta.length > 32 ? `${etiqueta.slice(0, 29)}…` : etiqueta
      return {
        territorio: short,
        territorioFull: etiqueta,
        indice: Number(row.indice_prioridad ?? 0),
        nivel: row.nivel_prioridad ?? 'bajo',
        rank: row.rank,
      }
    })
}

export const CARGA_CATEGORIA_COLOR = {
  alto: '#dc2626',
  medio: '#d97706',
  bajo: '#16a34a',
}

export const PRIORIDAD_NIVEL_COLOR = {
  alto: '#dc2626',
  medio: '#d97706',
  bajo: '#16a34a',
}

export const PATRON_RIESGO_COLOR = {
  alto: '#dc2626',
  medio: '#d97706',
  bajo: '#16a34a',
}
