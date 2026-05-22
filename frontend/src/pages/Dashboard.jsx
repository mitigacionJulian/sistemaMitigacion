import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'
import {
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  fetchDashboardBarrios,
  fetchDashboardCatalogos,
  fetchDashboardCargaEsperadaEspacial,
  fetchDashboardEvolucionMensual,
  fetchDashboardDistribucionClaseIncidente,
  fetchDashboardKpis,
  fetchDashboardTops,
  fetchDashboardMatrizDiaHora,
  fetchDashboardPorDiaSemana,
  fetchDashboardRangoFechas,
} from '../api/client.js'

/** Cobertura aproximada del archivo `salida/Mede_Victimas_inci_depurado.xlsx` si falla la API de rango */
const FECHAS_REF_MEDE = {
  default_desde: '2021-01-01',
  default_hasta: '2021-09-30',
  selector_fecha_min: '2014-01-01',
  selector_fecha_max: '2021-09-30',
}

function formatDateEs(iso) {
  if (!iso) return ''
  const [y, m, day] = iso.split('-').map(Number)
  const d = new Date(y, m - 1, day)
  return d.toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' })
}

function variacionTexto(pct) {
  if (pct === null || pct === undefined) return 'sin variación % (denominador 0 en año anterior)'
  const sign = pct > 0 ? '+' : ''
  return `${sign}${pct.toLocaleString('es-CO', { maximumFractionDigits: 2 })}% respecto al año anterior`
}

function variacionClass(pct) {
  if (pct === null || pct === undefined) return 'kpi-delta neutral'
  if (pct < 0) return 'kpi-delta down'
  if (pct > 0) return 'kpi-delta up'
  return 'kpi-delta neutral'
}

/** Ancho mínimo para mostrar las tres matrices día×hora; por debajo: gráficos resumidos por hora. */
const MATRIX_BREAKPOINT_PX = 900

/** Márgenes y leyenda: leyenda arriba + etiquetas de ejes abajo/izquierda para evitar solapes. */
const BAR_COMPARE_MARGIN = { top: 52, right: 18, left: 58, bottom: 56 }
const LEGEND_TOP_PROPS = {
  verticalAlign: 'top',
  align: 'center',
  wrapperStyle: { fontSize: '12px', lineHeight: '16px', paddingBottom: 6 },
  iconType: 'circle',
}

/** Ancho máximo (viewport) para márgenes/alturas de gráficos más compactos (móvil). */
const CHART_COMPACT_MAX_PX = 640

function useMediaQuery(query) {
  return useSyncExternalStore(
    (onStoreChange) => {
      if (typeof window === 'undefined') return () => {}
      const mq = window.matchMedia(query)
      mq.addEventListener('change', onStoreChange)
      return () => mq.removeEventListener('change', onStoreChange)
    },
    () => (typeof window !== 'undefined' ? window.matchMedia(query).matches : false),
    () => false,
  )
}

/** Agrupa la serie día×hora sumando incidentes por hora (todos los días de la semana). */
function aggregateIncidentesPorHora(serie) {
  const acc = Array.from({ length: 24 }, (_, h) => ({
    hora: h,
    horaLabel: `${h}:00`,
    actual: 0,
    anterior: 0,
    delta: 0,
  }))
  ;(serie || []).forEach((cell) => {
    const h = cell.hora
    if (h >= 0 && h < 24) {
      acc[h].actual += Number(cell.total_incidentes_actual ?? 0)
      acc[h].anterior += Number(cell.total_incidentes_anterior ?? 0)
      acc[h].delta += Number(cell.delta_abs ?? 0)
    }
  })
  return acc
}

function KpiCard({ label, value, sub, variacionPct, formatValue }) {
  const display = formatValue ? formatValue(value) : value
  return (
    <div className={`kpi-card${label.includes('fatal') ? ' accent' : ''}`}>
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{display}</span>
      {sub && <span className="kpi-sub muted small">{sub}</span>}
      <span className={`small ${variacionClass(variacionPct)}`}>{variacionTexto(variacionPct)}</span>
    </div>
  )
}

export function Dashboard() {
  const [catalogos, setCatalogos] = useState({ comunas: [], clases_incidente: [] })
  const [barrios, setBarrios] = useState([])

  const [rangoMeta, setRangoMeta] = useState(null)

  const [desde, setDesde] = useState(FECHAS_REF_MEDE.default_desde)
  const [hasta, setHasta] = useState(FECHAS_REF_MEDE.default_hasta)
  const [comunaId, setComunaId] = useState('')
  const [barrioId, setBarrioId] = useState('')
  const [claseId, setClaseId] = useState('')

  const [data, setData] = useState(null)
  const [evolucion, setEvolucion] = useState(null)
  const [diaSemana, setDiaSemana] = useState(null)
  const [matrizDiaHora, setMatrizDiaHora] = useState(null)
  const [tops, setTops] = useState(null)
  const [claseIncidente, setClaseIncidente] = useState(null)
  const [cargaInfra, setCargaInfra] = useState(null)
  const [tipoInfra, setTipoInfra] = useState('ranking_via')
  const [horizonteInfra, setHorizonteInfra] = useState(3)
  const [loadingInfra, setLoadingInfra] = useState(false)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const skipInfraAutoRef = useRef(true)

  const showMatrixHeatmaps = useMediaQuery(`(min-width: ${MATRIX_BREAKPOINT_PX}px)`)
  const chartLayoutCompact = useMediaQuery(`(max-width: ${CHART_COMPACT_MAX_PX}px)`)

  const barChartCompareMargin = useMemo(
    () =>
      chartLayoutCompact
        ? { top: 46, right: 2, left: 34, bottom: 50 }
        : BAR_COMPARE_MARGIN,
    [chartLayoutCompact],
  )

  const barChartCompareHeight = chartLayoutCompact ? 300 : 400

  const legendTopPropsResolved = useMemo(
    () =>
      chartLayoutCompact
        ? {
            ...LEGEND_TOP_PROPS,
            wrapperStyle: { ...LEGEND_TOP_PROPS.wrapperStyle, fontSize: '10px', lineHeight: '14px' },
          }
        : LEGEND_TOP_PROPS,
    [chartLayoutCompact],
  )

  const yAxisTickWidth = chartLayoutCompact ? 34 : 48

  const riesgoColor = (nivel, variante = 'base') => {
    const paleta = {
      alto: { base: '#dc2626', light: '#fca5a5', chip: '#fee2e2', text: '#991b1b' },
      medio: { base: '#d97706', light: '#fcd34d', chip: '#fef3c7', text: '#92400e' },
      bajo: { base: '#16a34a', light: '#86efac', chip: '#dcfce7', text: '#166534' },
    }
    return (paleta[nivel] || paleta.bajo)[variante]
  }

  const nivelCargaSemana = (row) => row.carga_dia_nivel ?? row.riesgo_nivel ?? 'bajo'
  const participacionSemanalPct = (row) => Number(row.participacion_incidentes_pct ?? row.riesgo_score ?? 0)
  const ratioVsUniforme = (row) => {
    const r = row.ratio_vs_reparto_uniforme
    return r != null && r !== '' ? Number(r) : null
  }

  const filtrosQuery = useCallback(
    () => ({
      desde,
      hasta,
      comuna_id: comunaId || undefined,
      barrio_id: barrioId || undefined,
      clase_incidente_id: claseId || undefined,
    }),
    [desde, hasta, comunaId, barrioId, claseId],
  )

  const infraQuery = useCallback(
    () => ({
      ...filtrosQuery(),
      tipo: tipoInfra,
      limite: 12,
      horizonte_meses: horizonteInfra,
      modelo: 'estacional',
      excluir_covid: '1',
    }),
    [filtrosQuery, tipoInfra, horizonteInfra],
  )

  const loadCargaInfra = useCallback(async () => {
    setLoadingInfra(true)
    try {
      const payload = await fetchDashboardCargaEsperadaEspacial(infraQuery())
      setCargaInfra(payload)
    } catch {
      setCargaInfra(null)
    } finally {
      setLoadingInfra(false)
    }
  }, [infraQuery])

  useEffect(() => {
    if (skipInfraAutoRef.current) {
      skipInfraAutoRef.current = false
      return
    }
    if (!cargaInfra && !data) return
    void loadCargaInfra()
  }, [tipoInfra, horizonteInfra, loadCargaInfra])

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const q = { ...filtrosQuery(), top_n: 10 }
      const infraQ = {
        ...filtrosQuery(),
        tipo: tipoInfra,
        limite: 12,
        horizonte_meses: horizonteInfra,
        modelo: 'estacional',
        excluir_covid: '1',
      }
      const [kpiPayload, evoPayload, diaPayload, matrizPayload, topsPayload, clasePayload, infraPayload] =
        await Promise.all([
          fetchDashboardKpis(q),
          fetchDashboardEvolucionMensual(q),
          fetchDashboardPorDiaSemana(q),
          fetchDashboardMatrizDiaHora(q),
          fetchDashboardTops(q),
          fetchDashboardDistribucionClaseIncidente(q),
          fetchDashboardCargaEsperadaEspacial(infraQ),
        ])
      setData(kpiPayload)
      setEvolucion(evoPayload)
      setDiaSemana(diaPayload)
      setMatrizDiaHora(matrizPayload)
      setTops(topsPayload)
      setClaseIncidente(clasePayload)
      setCargaInfra(infraPayload)
    } catch (e) {
      setData(null)
      setEvolucion(null)
      setDiaSemana(null)
      setMatrizDiaHora(null)
      setTops(null)
      setClaseIncidente(null)
      setCargaInfra(null)
      setErr(e instanceof Error ? e.message : 'Error al cargar el tablero')
    } finally {
      setLoading(false)
    }
  }, [filtrosQuery, tipoInfra, horizonteInfra])

  useEffect(() => {
    void fetchDashboardCatalogos()
      .then(setCatalogos)
      .catch(() => setCatalogos({ comunas: [], clases_incidente: [] }))
  }, [])

  useEffect(() => {
    if (!comunaId) {
      setBarrios([])
      return
    }
    void fetchDashboardBarrios(comunaId)
      .then((r) => setBarrios(r.barrios || []))
      .catch(() => setBarrios([]))
  }, [comunaId])

  useEffect(() => {
    let alive = true
    ;(async () => {
      setLoading(true)
      setErr(null)
      try {
        let rango
        try {
          rango = await fetchDashboardRangoFechas()
        } catch {
          rango = {
            ...FECHAS_REF_MEDE,
            hay_datos: false,
            referencia_fuente:
              'No se pudo leer el rango desde el servidor; usando fechas del archivo Mede depurado (aprox. 2014–2021).',
          }
        }
        if (!alive) return
        setRangoMeta(rango)
        setDesde(rango.default_desde)
        setHasta(rango.default_hasta)

        const q = { desde: rango.default_desde, hasta: rango.default_hasta, top_n: 10 }
        const infraQ = {
          desde: rango.default_desde,
          hasta: rango.default_hasta,
          tipo: 'ranking_via',
          limite: 12,
          horizonte_meses: 3,
          modelo: 'estacional',
          excluir_covid: '1',
        }
        const [kpiPayload, evoPayload, diaPayload, matrizPayload, topsPayload, clasePayload, infraPayload] =
          await Promise.all([
            fetchDashboardKpis(q),
            fetchDashboardEvolucionMensual(q),
            fetchDashboardPorDiaSemana(q),
            fetchDashboardMatrizDiaHora(q),
            fetchDashboardTops(q),
            fetchDashboardDistribucionClaseIncidente(q),
            fetchDashboardCargaEsperadaEspacial(infraQ),
          ])
        if (!alive) return
        setData(kpiPayload)
        setEvolucion(evoPayload)
        setDiaSemana(diaPayload)
        setMatrizDiaHora(matrizPayload)
        setTops(topsPayload)
        setClaseIncidente(clasePayload)
        setCargaInfra(infraPayload)
      } catch (e) {
        if (!alive) return
        setData(null)
        setEvolucion(null)
        setDiaSemana(null)
        setMatrizDiaHora(null)
        setTops(null)
        setClaseIncidente(null)
        setCargaInfra(null)
        setErr(e instanceof Error ? e.message : 'Error al cargar indicadores')
      } finally {
        if (alive) setLoading(false)
      }
    })()
    return () => {
      alive = false
    }
  }, [])

  const meta = data?.meta
  const kA = data?.kpis_periodo_actual
  const kPrev = data?.kpis_periodo_anterior
  const cmp = data?.comparacion

  const selMin = rangoMeta?.selector_fecha_min ?? FECHAS_REF_MEDE.selector_fecha_min
  const selMax = rangoMeta?.selector_fecha_max ?? FECHAS_REF_MEDE.selector_fecha_max
  const dias = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']

  const claseIncidenteSeries = claseIncidente?.serie || []
  const claseIncidenteChart = claseIncidenteSeries.map((it) => {
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

  const buildHeatmapGrid = (key) => {
    const grid = Array.from({ length: 7 }, () => Array(24).fill(0))
    ;(matrizDiaHora?.serie || []).forEach((cell) => {
      const d = cell.dia_semana
      const h = cell.hora
      if (d >= 0 && d < 7 && h >= 0 && h < 24) {
        grid[d][h] = Number(cell[key] ?? 0)
      }
    })
    return grid
  }

  const Heatmap = ({ title, grid, max, mode = 'base' }) => (
    <div className="heatmap-matrix">
      <h4>{title}</h4>
      {mode === 'base' && (
        <p className="heatmap-base-legend">
          <span className="legend-item legend-tone-light">Tono claro: pocos incidentes en esa celda día × hora.</span>
          <span className="legend-item legend-tone-dark">
            Tono oscuro (verde): más incidentes; el máximo de oscuridad es el máximo de incidentes <strong>en esta
            matriz</strong> (cada panel tiene su propia escala).
          </span>
        </p>
      )}
      {mode === 'delta' && (
        <p className="heatmap-delta-legend">
          <span className="legend-item legend-up">Rojo: más incidentes en el periodo actual que en el año anterior.</span>
          <span className="legend-item legend-down">
            Verde: menos incidentes en el periodo actual que en el año anterior.
          </span>
          <span className="legend-item legend-neutral">
            Blanco o gris muy claro: diferencia 0, o cambio pequeño respecto al mayor |diferencia| de esta matriz.
          </span>
        </p>
      )}
      <div className="heatmap-wrap">
        <div className="heatmap-grid" style={{ gridTemplateColumns: `60px repeat(24, 1fr)` }}>
          <div />
          {Array.from({ length: 24 }, (_, h) => (
            <div key={`h-${h}`} className="heatmap-hlabel">
              {h}
            </div>
          ))}
          {grid.map((row, di) => (
            <div key={`row-${di}`} style={{ display: 'contents' }}>
              <div className="heatmap-dlabel">{dias[di]}</div>
              {row.map((v, hi) => {
                const intensity = max > 0 ? Math.min(1, Math.abs(v) / max) : 0
                let bg
                if (mode === 'delta') {
                  bg =
                    v > 0
                      ? `color-mix(in srgb, #b91c1c ${Math.round(intensity * 100)}%, #f8fafc)`
                      : v < 0
                        ? `color-mix(in srgb, #0f766e ${Math.round(intensity * 100)}%, #f8fafc)`
                        : '#f8fafc'
                } else {
                  bg = `color-mix(in srgb, #0f766e ${Math.round(intensity * 100)}%, #f8fafc)`
                }
                return (
                  <div
                    key={`${di}-${hi}`}
                    className="heatmap-cell"
                    style={{ background: bg }}
                    title={`${dias[di]} ${hi}:00 — ${v}`}
                  />
                )
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  )

  return (
    <div className="dashboard">
      {loading && !data && !err && <p className="muted">Cargando rango de fechas e indicadores…</p>}

      <section className="panel filter-panel">
        <h2>Filtros del periodo y territorio</h2>
        <p className="muted small filter-help">
          Los datos disponibles cubren aproximadamente <strong>2014–2021</strong> (Mede depurado). El periodo por
          defecto es el <strong>último año con registros</strong> (1 ene → última fecha en base). La comparación usa el{' '}
          <strong>mismo rango de fechas un año antes</strong> (ej. 1 ene–30 sep 2021 vs 1 ene–30 sep 2020).
        </p>
        {rangoMeta?.referencia_fuente && (
          <p className="muted small filter-help" style={{ color: '#9a3412' }}>
            {rangoMeta.referencia_fuente}
          </p>
        )}
        <div className="filter-grid">
          <label className="filter-field">
            Desde
            <input
              type="date"
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
              min={selMin}
              max={hasta}
            />
          </label>
          <label className="filter-field">
            Hasta
            <input
              type="date"
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
              min={desde}
              max={selMax}
            />
          </label>
          <label className="filter-field">
            Comuna
            <select
              value={comunaId}
              onChange={(e) => {
                setComunaId(e.target.value)
                setBarrioId('')
              }}
            >
              <option value="">Todas</option>
              {(catalogos.comunas || []).map((c) => (
                <option key={c.id} value={String(c.id)}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            Barrio
            <select
              value={barrioId}
              onChange={(e) => setBarrioId(e.target.value)}
              disabled={!comunaId}
            >
              <option value="">Todos</option>
              {barrios.map((b) => (
                <option key={b.id} value={String(b.id)}>
                  {b.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            Clase de incidente
            <select value={claseId} onChange={(e) => setClaseId(e.target.value)}>
              <option value="">Todas</option>
              {(catalogos.clases_incidente || []).map((c) => (
                <option key={c.id} value={String(c.id)}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </label>
          <div className="filter-actions">
            <button type="button" className="btn btn-primary" onClick={() => void loadDashboard()} disabled={loading}>
              {loading ? 'Actualizando…' : 'Actualizar'}
            </button>
          </div>
        </div>
      </section>

      {err && <p className="form-error">{err}</p>}

      {meta && kA && (
        <>
          <div className="banner-live">
            {rangoMeta?.fecha_minima && rangoMeta?.fecha_maxima && (
              <p className="small muted" style={{ marginBottom: '0.5rem' }}>
                Registros en base (global): {formatDateEs(rangoMeta.fecha_minima)} —{' '}
                {formatDateEs(rangoMeta.fecha_maxima)}
                {rangoMeta.ultimo_anio_con_datos != null && (
                  <>
                    {' '}
                    Â· Año más reciente con datos: <strong>{rangoMeta.ultimo_anio_con_datos}</strong>
                  </>
                )}
              </p>
            )}
            <p>
              <strong>Rango de fechas (periodo actual):</strong> {formatDateEs(meta.fecha_inicio)} —{' '}
              {formatDateEs(meta.fecha_fin)} ({kA.dias_en_periodo} días).
            </p>
            <p>
              <strong>Comparación:</strong> mismo intervalo en el año anterior ({formatDateEs(meta.fecha_inicio_anterior)}{' '}
              — {formatDateEs(meta.fecha_fin_anterior)}).
            </p>
            {(meta.filtros?.comuna_id != null ||
              meta.filtros?.barrio_id != null ||
              meta.filtros?.clase_incidente_id != null) && (
              <p className="small muted">
                Filtros en esta consulta: comuna id {meta.filtros.comuna_id ?? '—'}, barrio id{' '}
                {meta.filtros.barrio_id ?? '—'}, clase id {meta.filtros.clase_incidente_id ?? '—'}.
              </p>
            )}
          </div>

          <section className="kpi-row">
            <KpiCard
              label="Total incidentes"
              value={kA.total_incidentes}
              variacionPct={cmp?.total_incidentes?.variacion_pct}
            />
            <KpiCard
              label="Total víctimas"
              value={kA.total_victimas}
              variacionPct={cmp?.total_victimas?.variacion_pct}
            />
            <KpiCard
              label="Víctimas fatales"
              value={kA.victimas_fatales}
              variacionPct={cmp?.victimas_fatales?.variacion_pct}
            />
            <KpiCard
              label="Tasa incidentes / día"
              value={kA.tasa_incidentes_por_dia}
              variacionPct={cmp?.tasa_incidentes_por_dia?.variacion_pct}
              formatValue={(v) =>
                Number(v).toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
              }
              sub={`${kA.total_incidentes.toLocaleString('es-CO')} incidentes Ã· ${kA.dias_en_periodo} días`}
            />
          </section>

          <section className="panel">
            <h2>Resumen estadístico (actual vs año anterior)</h2>
            <div className="cmp-table-wrap">
              <table className="table cmp-table">
                <thead>
                  <tr>
                    <th>Indicador</th>
                    <th>Periodo anterior</th>
                    <th>Periodo actual</th>
                    <th>Variación %</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Incidentes</td>
                    <td>{kPrev.total_incidentes.toLocaleString('es-CO')}</td>
                    <td>{kA.total_incidentes.toLocaleString('es-CO')}</td>
                    <td className={variacionClass(cmp?.total_incidentes?.variacion_pct)}>
                      {cmp?.total_incidentes?.variacion_pct != null
                        ? `${cmp.total_incidentes.variacion_pct > 0 ? '+' : ''}${cmp.total_incidentes.variacion_pct}%`
                        : '—'}
                    </td>
                  </tr>
                  <tr>
                    <td>Víctimas</td>
                    <td>{kPrev.total_victimas.toLocaleString('es-CO')}</td>
                    <td>{kA.total_victimas.toLocaleString('es-CO')}</td>
                    <td className={variacionClass(cmp?.total_victimas?.variacion_pct)}>
                      {cmp?.total_victimas?.variacion_pct != null
                        ? `${cmp.total_victimas.variacion_pct > 0 ? '+' : ''}${cmp.total_victimas.variacion_pct}%`
                        : '—'}
                    </td>
                  </tr>
                  <tr>
                    <td>Víctimas fatales</td>
                    <td>{kPrev.victimas_fatales.toLocaleString('es-CO')}</td>
                    <td>{kA.victimas_fatales.toLocaleString('es-CO')}</td>
                    <td className={variacionClass(cmp?.victimas_fatales?.variacion_pct)}>
                      {cmp?.victimas_fatales?.variacion_pct != null
                        ? `${cmp.victimas_fatales.variacion_pct > 0 ? '+' : ''}${cmp.victimas_fatales.variacion_pct}%`
                        : '—'}
                    </td>
                  </tr>
                  <tr>
                    <td>Tasa inc. / día</td>
                    <td>
                      {Number(kPrev.tasa_incidentes_por_dia).toLocaleString('es-CO', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 4,
                      })}
                    </td>
                    <td>
                      {Number(kA.tasa_incidentes_por_dia).toLocaleString('es-CO', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 4,
                      })}
                    </td>
                    <td className={variacionClass(cmp?.tasa_incidentes_por_dia?.variacion_pct)}>
                      {cmp?.tasa_incidentes_por_dia?.variacion_pct != null
                        ? `${cmp.tasa_incidentes_por_dia.variacion_pct > 0 ? '+' : ''}${cmp.tasa_incidentes_por_dia.variacion_pct}%`
                        : '—'}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="muted small" style={{ marginTop: '0.75rem' }}>
              La variación porcentual es{' '}
              <strong>(actual − anterior) / anterior × 100</strong>. Si el valor anterior es 0, no se calcula la
              variación relativa.
            </p>
          </section>

          {evolucion?.serie && evolucion.serie.length > 0 && evolucion.meta && (
            <section className="panel chart-panel-comparativo">
              <h2>Evolución mensual comparativa</h2>
              <p className="muted small">
                <strong>Periodo actual:</strong> {formatDateEs(evolucion.meta.fecha_inicio)} —{' '}
                {formatDateEs(evolucion.meta.fecha_fin)}. <strong>Comparación:</strong> mismo calendario de meses en{' '}
                {formatDateEs(evolucion.meta.fecha_inicio_anterior)} — {formatDateEs(evolucion.meta.fecha_fin_anterior)}{' '}
                (mismos filtros). Cada categoría del eje X es un mes natural dentro del rango; hay{' '}
                <strong>dos columnas apiladas</strong> (periodo actual vs intervalo equivalente del año anterior); en
                cada columna, abajo <strong>incidentes</strong> y arriba <strong>víctimas</strong>.
              </p>
              <div className="chart-box chart-box-tall">
                <ResponsiveContainer width="100%" height={barChartCompareHeight}>
                  <BarChart
                    data={evolucion.serie}
                    margin={barChartCompareMargin}
                    barCategoryGap="18%"
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                    <XAxis
                      dataKey="mes_etiqueta"
                      tick={{ fontSize: chartLayoutCompact ? 9 : 11 }}
                      angle={
                        chartLayoutCompact
                          ? evolucion.serie.length > 4
                            ? -32
                            : 0
                          : evolucion.serie.length > 8
                            ? -30
                            : 0
                      }
                      textAnchor={
                        chartLayoutCompact
                          ? evolucion.serie.length > 4
                            ? 'end'
                            : 'middle'
                          : evolucion.serie.length > 8
                            ? 'end'
                            : 'middle'
                      }
                      height={
                        chartLayoutCompact
                          ? evolucion.serie.length > 4
                            ? 48
                            : 32
                          : evolucion.serie.length > 8
                            ? 52
                            : 36
                      }
                      interval={0}
                      label={{
                        value: 'Mes (periodo seleccionado)',
                        position: 'bottom',
                        offset:
                          chartLayoutCompact && evolucion.serie.length > 4
                            ? 22
                            : evolucion.serie.length > 8
                              ? 28
                              : 14,
                        fontSize: chartLayoutCompact ? 11 : 12,
                        fill: '#64748b',
                      }}
                    />
                    <YAxis
                      allowDecimals={false}
                      tick={{ fontSize: chartLayoutCompact ? 9 : 11 }}
                      width={yAxisTickWidth}
                      label={{
                        value: 'Cantidad (barras apiladas)',
                        angle: -90,
                        position: 'left',
                        offset: chartLayoutCompact ? 6 : 10,
                        style: {
                          textAnchor: 'middle',
                          fontSize: chartLayoutCompact ? 10 : 12,
                          fill: '#64748b',
                        },
                      }}
                    />
                    <Tooltip />
                    <Legend {...legendTopPropsResolved} />
                    <Bar
                      stackId="act"
                      dataKey="incidentes_periodo_actual"
                      name="Incidentes (periodo actual)"
                      fill="#0f766e"
                      radius={[0, 0, 0, 0]}
                    />
                    <Bar
                      stackId="act"
                      dataKey="victimas_periodo_actual"
                      name="Víctimas (periodo actual)"
                      fill="#5eead4"
                      radius={[4, 4, 0, 0]}
                    />
                    <Bar
                      stackId="ant"
                      dataKey="incidentes_periodo_anterior"
                      name="Incidentes (año anterior)"
                      fill="#475569"
                    />
                    <Bar
                      stackId="ant"
                      dataKey="victimas_periodo_anterior"
                      name="Víctimas (año anterior)"
                      fill="#cbd5e1"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>
          )}


          {diaSemana?.serie && diaSemana.serie.length > 0 && diaSemana.meta && (
            <section className="panel chart-panel-comparativo">
              <h2>Por día de la semana (concentración en la semana)</h2>
              <p className="muted small">
                Barras apiladas: periodo actual vs intervalo equivalente del año anterior. El color del{' '}
                <strong>periodo actual</strong> indica qué tan <strong>concentrados</strong> están los incidentes de
                ese día respecto a un reparto uniforme entre los siete días (≈14,3% cada uno). El valor % es la{' '}
                <strong>participación en el total semanal</strong> de incidentes del periodo filtrado (los siete días
                suman 100%). <strong>No es probabilidad</strong> de accidente. La{' '}
                <strong>proyección por día (P13)</strong> está en{' '}
                <a href="/predicciones">Predicciones</a>.
              </p>
              <div className="risk-legend">
                <span className="risk-chip risk-chip-alto">Carga alta</span>
                <span className="risk-chip risk-chip-medio">Carga media</span>
                <span className="risk-chip risk-chip-bajo">Carga baja</span>
              </div>
              <div className="chart-box chart-box-tall">
                <ResponsiveContainer width="100%" height={barChartCompareHeight}>
                  <BarChart
                    data={diaSemana.serie}
                    margin={barChartCompareMargin}
                    barCategoryGap="18%"
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                    <XAxis
                      dataKey="dia"
                      tick={{ fontSize: chartLayoutCompact ? 9 : 11 }}
                      {...(chartLayoutCompact
                        ? { angle: -20, textAnchor: 'end', height: 42 }
                        : { angle: 0, textAnchor: 'middle' })}
                      label={{
                        value: 'Día de la semana',
                        position: 'bottom',
                        offset: chartLayoutCompact ? 18 : 12,
                        fontSize: chartLayoutCompact ? 11 : 12,
                        fill: '#64748b',
                      }}
                    />
                    <YAxis
                      allowDecimals={false}
                      tick={{ fontSize: chartLayoutCompact ? 9 : 11 }}
                      width={yAxisTickWidth}
                      label={{
                        value: 'Cantidad (barras apiladas)',
                        angle: -90,
                        position: 'left',
                        offset: chartLayoutCompact ? 6 : 10,
                        style: {
                          textAnchor: 'middle',
                          fontSize: chartLayoutCompact ? 10 : 12,
                          fill: '#64748b',
                        },
                      }}
                    />
                    <Tooltip />
                    <Legend {...legendTopPropsResolved} />
                    <Bar
                      stackId="act"
                      dataKey="incidentes_periodo_actual"
                      name="Incidentes (periodo actual)"
                      radius={[0, 0, 0, 0]}
                    >
                      {diaSemana.serie.map((d, i) => (
                        <Cell key={`inc-act-${i}`} fill={riesgoColor(nivelCargaSemana(d), 'base')} />
                      ))}
                    </Bar>
                    <Bar
                      stackId="act"
                      dataKey="victimas_periodo_actual"
                      name="Víctimas (periodo actual)"
                      radius={[4, 4, 0, 0]}
                    >
                      {diaSemana.serie.map((d, i) => (
                        <Cell key={`vic-act-${i}`} fill={riesgoColor(nivelCargaSemana(d), 'light')} />
                      ))}
                    </Bar>
                    <Bar
                      stackId="ant"
                      dataKey="incidentes_periodo_anterior"
                      name="Incidentes (año anterior)"
                      fill="#475569"
                    />
                    <Bar
                      stackId="ant"
                      dataKey="victimas_periodo_anterior"
                      name="Víctimas (año anterior)"
                      fill="#cbd5e1"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="risk-grid">
                {diaSemana.serie.map((d) => {
                  const nivel = nivelCargaSemana(d)
                  const pct = participacionSemanalPct(d)
                  const ratio = ratioVsUniforme(d)
                  return (
                  <div
                    key={`carga-dia-${d.dia_semana}`}
                    className="risk-item"
                    style={{
                      borderLeft: `4px solid ${riesgoColor(nivel, 'base')}`,
                      background: riesgoColor(nivel, 'chip'),
                      color: riesgoColor(nivel, 'text'),
                    }}
                  >
                    <strong>{d.dia}</strong>: concentración <strong>{nivel}</strong> —{' '}
                    {pct.toLocaleString('es-CO', { maximumFractionDigits: 2 })}% del total semanal de incidentes
                    {ratio != null && !Number.isNaN(ratio) ? (
                      <>
                        {' '}
                        (ratio vs. reparto uniforme:{' '}
                        {ratio.toLocaleString('es-CO', { maximumFractionDigits: 2 })})
                      </>
                    ) : null}
                  </div>
                  )
                })}
              </div>
            </section>
          )}

          {matrizDiaHora?.serie && matrizDiaHora.serie.length > 0 && (
            <section className="panel chart-panel-comparativo matrix-dia-hora-section">
              <h2>Matriz día/hora comparativa</h2>
              <p className="muted small">
                La matriz <strong>periodo vs. proyección (P12)</strong> está en{' '}
                <a href="/predicciones">Predicciones</a>.
              </p>
              <p className="muted small">
                {showMatrixHeatmaps ? (
                  <>
                    Matriz del periodo actual ({formatDateEs(meta?.fecha_inicio)} — {formatDateEs(meta?.fecha_fin)}) y
                    del mismo intervalo del año anterior ({formatDateEs(meta?.fecha_inicio_anterior)} —{' '}
                    {formatDateEs(meta?.fecha_fin_anterior)}), más una matriz de diferencia (actual − anterior).
                  </>
                ) : (
                  <>
                    Vista compacta: incidentes <strong>agregados por hora del día</strong> (suma de los siete días de la
                    semana), comparando periodo actual vs año anterior y la diferencia. En pantallas de al menos{' '}
                    {MATRIX_BREAKPOINT_PX}px de ancho se muestran las matrices completas día × hora.
                  </>
                )}
              </p>
              {showMatrixHeatmaps && matrizDiaHora?.serie?.length > 0 && (
                <div className="matrix-heatmap-reading" role="note">
                  <strong className="matrix-heatmap-reading-title">Cómo leer las tonalidades</strong>
                  <ul className="matrix-heatmap-reading-list muted small">
                    <li>
                      <strong>Periodo actual</strong> y <strong>año anterior</strong>: color verde más intenso = más
                      incidentes en esa intersección día de la semana × hora. Fondo casi blanco = pocos o ningún
                      incidente. La escala de oscuridad es <strong>independiente en cada matriz</strong> (comparar
                      patrones, no el tono exacto entre un panel y otro).
                    </li>
                    <li>
                      <strong>Diferencia (actual − anterior)</strong>: rojo = subieron los incidentes respecto al año
                      anterior en esa celda; verde = bajaron; blanco o gris muy claro = sin cambio o cambio muy pequeño
                      frente al valor absoluto máximo de diferencia en el periodo.
                    </li>
                  </ul>
                </div>
              )}
              {(() => {
                const gridAct = buildHeatmapGrid('total_incidentes_actual')
                const gridAnt = buildHeatmapGrid('total_incidentes_anterior')
                const gridDelta = buildHeatmapGrid('delta_abs')
                const maxAct = Math.max(1, ...gridAct.flat())
                const maxAnt = Math.max(1, ...gridAnt.flat())
                const maxDelta = Math.max(1, ...gridDelta.flat().map((x) => Math.abs(x)))
                const porHora = aggregateIncidentesPorHora(matrizDiaHora.serie)

                if (!showMatrixHeatmaps) {
                  return (
                    <div className="matrix-mobile-stack">
                      <div className="matrix-mobile-reading muted small" role="note">
                        En vista estrecha no se muestran las celdas día × hora; los gráficos resumen por{' '}
                        <strong>hora</strong>. Las barras de diferencia usan la misma lógica de color que la matriz
                        grande: rojo subió, verde bajó, gris claro casi sin cambio.
                      </div>
                      <div className="matrix-mobile-chart">
                        <h4 className="matrix-mobile-title">Incidentes por hora (suma semanal)</h4>
                        <p className="muted small matrix-mobile-hint">
                          Cada punto suma los incidentes de las 24 celdas (7 días × esa hora).
                        </p>
                        <div className="chart-box" style={{ minHeight: chartLayoutCompact ? 260 : 280 }}>
                          <ResponsiveContainer width="100%" height={chartLayoutCompact ? 248 : 280}>
                            <LineChart
                              data={porHora}
                              margin={{
                                top: chartLayoutCompact ? 36 : 40,
                                right: chartLayoutCompact ? 4 : 12,
                                left: chartLayoutCompact ? 2 : 8,
                                bottom: chartLayoutCompact ? 26 : 28,
                              }}
                            >
                              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                              <XAxis
                                dataKey="hora"
                                type="number"
                                domain={[0, 23]}
                                ticks={[0, 3, 6, 9, 12, 15, 18, 21]}
                                tick={{ fontSize: 10 }}
                                tickFormatter={(v) => `${v}h`}
                                label={{
                                  value: 'Hora del día',
                                  position: 'bottom',
                                  offset: 10,
                                  fontSize: 11,
                                  fill: '#64748b',
                                }}
                              />
                              <YAxis
                                allowDecimals={false}
                                tick={{ fontSize: 11 }}
                                width={40}
                                label={{
                                  value: 'Incidentes (suma 7 días)',
                                  angle: -90,
                                  position: 'left',
                                  offset: 6,
                                  style: { textAnchor: 'middle', fontSize: 11, fill: '#64748b' },
                                }}
                              />
                              <Tooltip
                                formatter={(val) => [
                                  Number(val).toLocaleString('es-CO'),
                                  '',
                                ]}
                                labelFormatter={(h) => `Hora ${h}:00`}
                              />
                              <Legend
                                {...legendTopPropsResolved}
                                wrapperStyle={{
                                  ...legendTopPropsResolved.wrapperStyle,
                                  fontSize: chartLayoutCompact ? '10px' : '11px',
                                }}
                              />
                              <Line
                                type="monotone"
                                dataKey="actual"
                                name="Periodo actual"
                                stroke="#0f766e"
                                strokeWidth={2}
                                dot={{ r: 2 }}
                              />
                              <Line
                                type="monotone"
                                dataKey="anterior"
                                name="Año anterior equiv."
                                stroke="#94a3b8"
                                strokeWidth={2}
                                dot={{ r: 2 }}
                              />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      </div>
                      <div className="matrix-mobile-chart">
                        <h4 className="matrix-mobile-title">Diferencia por hora (actual − anterior)</h4>
                        <p className="heatmap-delta-legend matrix-mobile-legend">
                          <span className="legend-item legend-up">Rojo: más incidentes en el periodo actual</span>
                          <span className="legend-item legend-down">Verde: menos en el periodo actual</span>
                          <span className="legend-item legend-neutral">
                            Gris claro: diferencia cercana a 0
                          </span>
                        </p>
                        <div className="chart-box" style={{ minHeight: chartLayoutCompact ? 228 : 240 }}>
                          <ResponsiveContainer width="100%" height={chartLayoutCompact ? 216 : 240}>
                            <BarChart
                              data={porHora}
                              margin={{
                                top: chartLayoutCompact ? 6 : 10,
                                right: chartLayoutCompact ? 2 : 10,
                                left: chartLayoutCompact ? 36 : 46,
                                bottom: chartLayoutCompact ? 36 : 40,
                              }}
                            >
                              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                              <XAxis
                                dataKey="hora"
                                tick={{ fontSize: 9 }}
                                interval={2}
                                tickFormatter={(v) => `${v}h`}
                                label={{
                                  value: 'Hora del día',
                                  position: 'bottom',
                                  offset: 10,
                                  fontSize: 11,
                                  fill: '#64748b',
                                }}
                              />
                              <YAxis
                                allowDecimals={false}
                                tick={{ fontSize: 10 }}
                                width={38}
                                label={{
                                  value: 'Î” incidentes',
                                  angle: -90,
                                  position: 'left',
                                  offset: 8,
                                  style: { textAnchor: 'middle', fontSize: 11, fill: '#64748b' },
                                }}
                              />
                              <Tooltip
                                formatter={(val) => [Number(val).toLocaleString('es-CO'), 'Î” incidentes']}
                                labelFormatter={(h) => `Hora ${h}:00`}
                              />
                              <Bar dataKey="delta" name="Diferencia" radius={[2, 2, 0, 0]}>
                                {porHora.map((entry, i) => (
                                  <Cell
                                    key={`d-${i}`}
                                    fill={
                                      entry.delta > 0 ? '#b91c1c' : entry.delta < 0 ? '#0f766e' : '#e2e8f0'
                                    }
                                  />
                                ))}
                              </Bar>
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                      </div>
                    </div>
                  )
                }

                return (
                  <div className="heatmap-desktop-shell">
                    <div className="matrix-compare-wrap">
                      <Heatmap title="Periodo actual" grid={gridAct} max={maxAct} />
                      <Heatmap title="Año anterior" grid={gridAnt} max={maxAnt} />
                      <Heatmap title="Diferencia (actual - anterior)" grid={gridDelta} max={maxDelta} mode="delta" />
                    </div>
                  </div>
                )
              })()}
            </section>
          )}

          {claseIncidenteChart.length > 0 && (
            <section className="panel chart-panel-comparativo">
              <h2>Incidentes por clase</h2>
              <p className="muted small">
                Conteo de incidentes por tipo de clasificación, comparando el periodo actual (
                {formatDateEs(meta?.fecha_inicio)} — {formatDateEs(meta?.fecha_fin)}) con el mismo intervalo del año
                anterior ({formatDateEs(meta?.fecha_inicio_anterior)} — {formatDateEs(meta?.fecha_fin_anterior)}). Si
                aplica el filtro por clase, solo se muestra esa categoría. <strong>Eje vertical:</strong> clase de
                incidente.
              </p>
              <div
                className="chart-box chart-box-tall chart-box-clase-incidente"
                style={{
                  minHeight: Math.max(
                    chartLayoutCompact ? 300 : 360,
                    claseIncidenteChart.length * (chartLayoutCompact ? 36 : 40) + (chartLayoutCompact ? 88 : 100),
                  ),
                }}
              >
                <ResponsiveContainer
                  width="100%"
                  height={Math.max(
                    chartLayoutCompact ? 300 : 360,
                    claseIncidenteChart.length * (chartLayoutCompact ? 36 : 40) + (chartLayoutCompact ? 88 : 100),
                  )}
                >
                  <BarChart
                    layout="vertical"
                    data={claseIncidenteChart}
                    margin={
                      chartLayoutCompact
                        ? { top: 44, right: 6, left: 2, bottom: 48 }
                        : { top: 52, right: 24, left: 4, bottom: 52 }
                    }
                    barCategoryGap="12%"
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                    <XAxis
                      type="number"
                      allowDecimals={false}
                      tick={{ fontSize: chartLayoutCompact ? 10 : 11 }}
                      label={{
                        value: 'Número de incidentes',
                        position: 'bottom',
                        offset: chartLayoutCompact ? 12 : 14,
                        fontSize: chartLayoutCompact ? 11 : 12,
                        fill: '#64748b',
                      }}
                    />
                    <YAxis
                      type="category"
                      dataKey="clase"
                      width={chartLayoutCompact ? 120 : 148}
                      tick={{ fontSize: chartLayoutCompact ? 9 : 11 }}
                      interval={0}
                    />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null
                        const row = payload[0].payload
                        const title = row.codigo ? `${row.claseFull} (${row.codigo})` : row.claseFull
                        return (
                          <div
                            className="recharts-default-tooltip"
                            style={{
                              padding: '8px 12px',
                              background: '#fff',
                              border: '1px solid #e2e8f0',
                              borderRadius: 8,
                              boxShadow: '0 4px 12px rgba(15,23,42,0.08)',
                            }}
                          >
                            <p className="small" style={{ marginBottom: 8, fontWeight: 600 }}>
                              {title}
                            </p>
                            <p className="small muted" style={{ margin: '4px 0' }}>
                              Periodo actual:{' '}
                              <strong>{row.actual.toLocaleString('es-CO')}</strong> (
                              {Number(row.pctActual ?? 0).toLocaleString('es-CO', { maximumFractionDigits: 1 })}%)
                            </p>
                            <p className="small muted" style={{ margin: '4px 0' }}>
                              Año anterior equivalente:{' '}
                              <strong>{row.anterior.toLocaleString('es-CO')}</strong> (
                              {Number(row.pctAnterior ?? 0).toLocaleString('es-CO', { maximumFractionDigits: 1 })}%)
                            </p>
                          </div>
                        )
                      }}
                    />
                    <Legend {...legendTopPropsResolved} />
                    <Bar dataKey="actual" name="Periodo actual" fill="#0ea5e9" radius={[0, 4, 4, 0]} />
                    <Bar dataKey="anterior" name="Año anterior equivalente" fill="#94a3b8" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>
          )}

          <section className="panel carga-infra-panel">
            <h2>
              Proyección por vía y punto crítico (P11)
              {loadingInfra && <span className="muted small"> — actualizando…</span>}
            </h2>
            <p className="muted small">
              <strong>Qué mide:</strong>{' '}
              {cargaInfra?.meta?.que_mide ??
                'Carga esperada de incidentes en el horizonte de predicción, por vía o punto crítico con serie suficiente.'}
            </p>
            {cargaInfra?.meta?.diferencia_p08 && (
              <p className="muted small">
                <strong>Vs. comparación territorial (Predicciones):</strong> {cargaInfra.meta.diferencia_p08}
              </p>
            )}
            <div className="predicciones-toolbar dashboard-infra-toolbar">
              <label>
                Ranking
                <select
                  className="predicciones-select"
                  value={tipoInfra}
                  onChange={(e) => setTipoInfra(e.target.value)}
                  disabled={loadingInfra}
                >
                  <option value="ranking_via">Vías</option>
                  <option value="ranking_punto">Puntos críticos</option>
                </select>
              </label>
              <label>
                Horizonte (meses)
                <select
                  className="predicciones-select"
                  value={horizonteInfra}
                  onChange={(e) => setHorizonteInfra(Number(e.target.value))}
                  disabled={loadingInfra}
                >
                  <option value={1}>1</option>
                  <option value={3}>3</option>
                  <option value={6}>6</option>
                  <option value={12}>12</option>
                </select>
              </label>
            </div>
            <p className="muted small">
              Cambios de <strong>ranking</strong> u <strong>horizonte</strong> actualizan sin pulsar Actualizar.
              Fechas y filtros del tablero sí requieren Actualizar.
            </p>
            {cargaInfra?.meta?.interpretacion && (
              <p className="bondad-interpretacion bondad-moderado carga-interpretacion" role="status">
                <strong>Interpretación:</strong> {cargaInfra.meta.interpretacion}
              </p>
            )}
            {cargaInfra?.meta?.cobertura_datos && (
              <p className="muted small">
                Cobertura en el periodo: {cargaInfra.meta.cobertura_datos.pct_con_via}% incidentes con vía ·{' '}
                {cargaInfra.meta.cobertura_datos.pct_con_punto}% con punto crítico.
              </p>
            )}
            {cargaInfra?.meta?.sin_datos && (
              <p className="warn small">Sin entidades con datos suficientes para este ranking y filtros.</p>
            )}
            {cargaInfra?.ranking?.length > 0 && (
              <div className="prioridad-table-wrap">
                <table className="prioridad-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>{tipoInfra === 'ranking_via' ? 'Vía' : 'Punto crítico'}</th>
                      <th>Carga proyectada</th>
                      <th>Incidentes periodo</th>
                      <th>R² serie</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cargaInfra.ranking.map((row) => (
                      <tr key={row.rank}>
                        <td>{row.rank}</td>
                        <td>
                          {tipoInfra === 'ranking_via' ? row.via_nombre : row.punto_critico_nombre}
                          {tipoInfra === 'ranking_punto' && row.via_nombre && (
                            <span className="muted small"> ({row.via_nombre})</span>
                          )}
                        </td>
                        <td>
                          {row.carga_proyectada_horizonte?.toLocaleString('es-CO', {
                            maximumFractionDigits: 1,
                          })}
                        </td>
                        <td>{row.incidentes_periodo}</td>
                        <td>{row.r2 != null ? row.r2 : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {cargaInfra?.meta?.limitaciones && (
              <p className="muted small carga-limitaciones">{cargaInfra.meta.limitaciones}</p>
            )}
          </section>

          {tops?.meta != null && (
            <section className="panel">
              <h2>Rankings del periodo</h2>
              <p className="muted small">
                Los cinco rankings vienen en una sola respuesta de API y aquí se muestran como{' '}
                <strong>tablas independientes</strong> (así se evita una tabla única con filas heterogéneas difíciles de
                leer). Conteo de <strong>víctimas</strong> con los mismos filtros del tablero; el % es sobre el total
                del periodo ({Number(tops.meta.total_victimas_periodo ?? 0).toLocaleString('es-CO')} víctimas). Se listan
                los primeros <strong>{tops.meta.limite ?? 10}</strong> lugares por categoría.
              </p>
              <div className="tops-grid">
                <div className="tops-card">
                  <h3 className="tops-card-title">Top sexo</h3>
                  <div className="tops-table-wrap">
                    <table className="table tops-table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>Sexo</th>
                          <th className="num">Víct.</th>
                          <th className="num">%</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(tops.sexo || []).length === 0 ? (
                          <tr>
                            <td colSpan={4} className="muted">
                              Sin registros
                            </td>
                          </tr>
                        ) : (
                          (tops.sexo || []).map((r) => (
                            <tr key={`${r.sexo_id}-${r.nombre}`}>
                              <td>{r.rank}</td>
                              <td>{r.nombre}</td>
                              <td className="num">{Number(r.total_victimas).toLocaleString('es-CO')}</td>
                              <td className="num">{Number(r.porcentaje).toLocaleString('es-CO')}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
                <div className="tops-card">
                  <h3 className="tops-card-title">Top edad</h3>
                  <p className="muted small tops-card-hint">Por edad declarada (años); empates por frecuencia.</p>
                  <div className="tops-table-wrap">
                    <table className="table tops-table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>Edad</th>
                          <th className="num">Víct.</th>
                          <th className="num">%</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(tops.edad || []).length === 0 ? (
                          <tr>
                            <td colSpan={4} className="muted">
                              Sin registros
                            </td>
                          </tr>
                        ) : (
                          (tops.edad || []).map((r) => (
                            <tr key={`${r.edad}-${r.etiqueta}`}>
                              <td>{r.rank}</td>
                              <td>{r.etiqueta}</td>
                              <td className="num">{Number(r.total_victimas).toLocaleString('es-CO')}</td>
                              <td className="num">{Number(r.porcentaje).toLocaleString('es-CO')}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
                <div className="tops-card">
                  <h3 className="tops-card-title">Top condición en la vía</h3>
                  <div className="tops-table-wrap">
                    <table className="table tops-table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>Condición</th>
                          <th className="num">Víct.</th>
                          <th className="num">%</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(tops.condicion || []).length === 0 ? (
                          <tr>
                            <td colSpan={4} className="muted">
                              Sin registros
                            </td>
                          </tr>
                        ) : (
                          (tops.condicion || []).map((r) => (
                            <tr key={`${r.condicion_id}-${r.nombre}`}>
                              <td>{r.rank}</td>
                              <td>{r.nombre}</td>
                              <td className="num">{Number(r.total_victimas).toLocaleString('es-CO')}</td>
                              <td className="num">{Number(r.porcentaje).toLocaleString('es-CO')}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
                <div className="tops-card">
                  <h3 className="tops-card-title">Top comuna</h3>
                  <div className="tops-table-wrap">
                    <table className="table tops-table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>Comuna</th>
                          <th className="num">Víct.</th>
                          <th className="num">%</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(tops.comuna || []).length === 0 ? (
                          <tr>
                            <td colSpan={4} className="muted">
                              Sin registros
                            </td>
                          </tr>
                        ) : (
                          (tops.comuna || []).map((r) => (
                            <tr key={`${r.comuna_id}-${r.nombre}`}>
                              <td>{r.rank}</td>
                              <td>{r.nombre}</td>
                              <td className="num">{Number(r.total_victimas).toLocaleString('es-CO')}</td>
                              <td className="num">{Number(r.porcentaje).toLocaleString('es-CO')}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
                <div className="tops-card">
                  <h3 className="tops-card-title">Top barrio</h3>
                  <div className="tops-table-wrap">
                    <table className="table tops-table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>Barrio</th>
                          <th className="num">Víct.</th>
                          <th className="num">%</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(tops.barrio || []).length === 0 ? (
                          <tr>
                            <td colSpan={4} className="muted">
                              Sin registros
                            </td>
                          </tr>
                        ) : (
                          (tops.barrio || []).map((r) => (
                            <tr key={`${r.barrio_id}-${r.nombre}`}>
                              <td>{r.rank}</td>
                              <td>
                                {r.nombre}
                                {r.comuna_nombre ? (
                                  <span className="muted small"> Â· {r.comuna_nombre}</span>
                                ) : null}
                              </td>
                              <td className="num">{Number(r.total_victimas).toLocaleString('es-CO')}</td>
                              <td className="num">{Number(r.porcentaje).toLocaleString('es-CO')}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </section>
          )}
        </>
      )}

      {!loading && !err && !data && <p className="muted">Sin datos.</p>}
    </div>
  )
}
