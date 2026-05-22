import { useMemo, useSyncExternalStore } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const MATRIX_BREAKPOINT_PX = 900
const CHART_COMPACT_MAX_PX = 640
const LEGEND_TOP_PROPS = {
  verticalAlign: 'top',
  align: 'center',
  wrapperStyle: { fontSize: '12px', lineHeight: '16px', paddingBottom: 6 },
  iconType: 'circle',
}
const BAR_COMPARE_MARGIN = { top: 52, right: 18, left: 58, bottom: 56 }
const DIAS = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']

const PATRON_RIESGO_COLOR = {
  alto: '#dc2626',
  medio: '#d97706',
  bajo: '#16a34a',
}

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

function buildHeatmapGrid(serie, key) {
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

function gridMaxAbs(grid) {
  let m = 0
  for (const row of grid) {
    for (const v of row) {
      m = Math.max(m, Math.abs(v))
    }
  }
  return Math.max(1, m)
}

function aggregatePorHora(serie) {
  const acc = Array.from({ length: 24 }, (_, h) => ({
    hora: h,
    horaLabel: `${h}:00`,
    periodo: 0,
    proyeccion: 0,
    delta: 0,
  }))
  ;(serie || []).forEach((cell) => {
    const h = cell.hora
    if (h >= 0 && h < 24) {
      const obs = Number(cell.incidentes_observados_periodo ?? 0)
      const pr = Number(cell.incidentes_proyectados_horizonte ?? 0)
      acc[h].periodo += obs
      acc[h].proyeccion += pr
      acc[h].delta += Number(cell.delta_proyeccion_menos_periodo ?? pr - obs)
    }
  })
  return acc
}

function Heatmap({ title, grid, max, mode = 'base', deltaLegend = 'periodo', serieMatriz = null }) {
  return (
    <div className="heatmap-matrix">
      <h4>{title}</h4>
      {mode === 'base' && (
        <p className="heatmap-base-legend">
          <span className="legend-item legend-tone-light">Tono claro: pocos incidentes en esa celda.</span>
          <span className="legend-item legend-tone-dark">
            Tono oscuro (verde): más incidentes; escala propia de este panel.
          </span>
        </p>
      )}
      {mode === 'delta' && (
        <p className="heatmap-delta-legend">
          {deltaLegend === 'proyeccion' ? (
            <>
              <span className="legend-item legend-up">Rojo: más incidentes esperados en la proyección que en el periodo seleccionado (misma celda).</span>
              <span className="legend-item legend-down">Verde: menos en la proyección que en el periodo.</span>
            </>
          ) : (
            <>
              <span className="legend-item legend-up">Rojo: sube respecto al periodo.</span>
              <span className="legend-item legend-down">Verde: baja respecto al periodo.</span>
            </>
          )}
          <span className="legend-item legend-neutral">
            Blanco o gris: sin cambio o cambio pequeño frente al máximo |diferencia| de esta matriz.
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
              <div className="heatmap-dlabel">{DIAS[di]}</div>
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
                    title={
                      mode === 'delta' && serieMatriz
                        ? (() => {
                            const cell = (serieMatriz || []).find(
                              (c) => c.dia_semana === di && c.hora === hi,
                            )
                            if (!cell) return `${DIAS[di]} ${hi}:00 — ${v}`
                            return `${DIAS[di]} ${hi}:00 — Δ ${v} (proy. ${cell.incidentes_proyectados_horizonte} − periodo ${cell.incidentes_observados_periodo})`
                          })()
                        : `${DIAS[di]} ${hi}:00 — ${v}`
                    }
                  />
                )
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function PatronesDiaHoraPanel({
  matrizProyectada,
  diaSemanaProyectado,
  loading = false,
  horizonteMeses = 3,
}) {
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
  const yAxisTickWidth = chartLayoutCompact ? 34 : 48
  const legendTopPropsResolved = chartLayoutCompact
    ? {
        ...LEGEND_TOP_PROPS,
        wrapperStyle: { ...LEGEND_TOP_PROPS.wrapperStyle, fontSize: '10px', lineHeight: '14px' },
      }
    : LEGEND_TOP_PROPS

  const serieMatriz = matrizProyectada?.serie
  const mostrar = !matrizProyectada?.meta?.sin_datos && (serieMatriz?.length ?? 0) > 0

  const gridPeriodo = useMemo(
    () => buildHeatmapGrid(serieMatriz, 'incidentes_observados_periodo'),
    [serieMatriz],
  )
  const gridProy = useMemo(
    () => buildHeatmapGrid(serieMatriz, 'incidentes_proyectados_horizonte'),
    [serieMatriz],
  )
  const gridDelta = useMemo(
    () => buildHeatmapGrid(serieMatriz, 'delta_proyeccion_menos_periodo'),
    [serieMatriz],
  )

  const maxPeriodo = gridMaxAbs(gridPeriodo)
  const maxProy = gridMaxAbs(gridProy)
  const maxDelta = gridMaxAbs(gridDelta)
  const porHora = useMemo(() => aggregatePorHora(serieMatriz), [serieMatriz])

  const diaChart = diaSemanaProyectado?.serie || []

  if (!matrizProyectada && !diaSemanaProyectado && !loading) {
    return null
  }

  return (
    <>
      <section className="panel patrones-pred-panel matrix-dia-hora-section">
        <h2>
          Patrones día × hora (P12)
          {loading && <span className="muted small"> — actualizando…</span>}
        </h2>
        <p className="muted small">
          <strong>Qué compara:</strong> distribución de incidentes en el <strong>periodo seleccionado</strong>{' '}
          (fechas y filtros arriba) frente a la <strong>proyección</strong> en el horizonte de{' '}
          <strong>{horizonteMeses} mes(es)</strong>. El total proyectado se reparte por día×hora según el patrón
          histórico del periodo; no es probabilidad individual.
        </p>
        {matrizProyectada?.meta?.metodo && (
          <p className="muted small">
            <strong>Método:</strong> {matrizProyectada.meta.metodo}
          </p>
        )}
        {matrizProyectada?.meta?.total_proyectado_horizonte != null && mostrar && (
          <p className="muted small">
            Incidentes en periodo:{' '}
            <strong>
              {Number(matrizProyectada.meta.total_incidentes_periodo).toLocaleString('es-CO')}
            </strong>
            {' · '}
            Total proyectado (horizonte):{' '}
            <strong>
              {Number(matrizProyectada.meta.total_proyectado_horizonte).toLocaleString('es-CO', {
                maximumFractionDigits: 1,
              })}
            </strong>
          </p>
        )}
        {matrizProyectada?.meta?.lectura_diferencia && (
          <p className="muted small matrix-delta-reading" role="note">
            <strong>Diferencia (proyección − periodo):</strong> {matrizProyectada.meta.lectura_diferencia}
          </p>
        )}
        {matrizProyectada?.meta?.validacion_diferencia?.coherente === false && (
          <p className="warn small">Validación interna: la suma de celdas de diferencia no cuadra con los totales.</p>
        )}
        {matrizProyectada?.meta?.interpretacion && (
          <p className="bondad-interpretacion bondad-moderado carga-interpretacion" role="status">
            <strong>Interpretación:</strong> {matrizProyectada.meta.interpretacion}
          </p>
        )}
        {matrizProyectada?.meta?.sin_datos && (
          <p className="warn small">Sin matriz: amplíe fechas, quite filtros estrechos o revise el modelo mensual.</p>
        )}
        {mostrar && (
          <>
            <p className="muted small">
              {showMatrixHeatmaps ? (
                <>
                  Tres matrices: <strong>periodo seleccionado</strong>, <strong>proyección</strong> y{' '}
                  <strong>diferencia (proyección − periodo)</strong> por celda día × hora.
                </>
              ) : (
                <>
                  Vista compacta por <strong>hora</strong> (suma de los siete días). En pantallas ≥{' '}
                  {MATRIX_BREAKPOINT_PX}px se muestran las matrices completas.
                </>
              )}
            </p>
            {showMatrixHeatmaps && (
              <div className="matrix-heatmap-reading" role="note">
                <strong className="matrix-heatmap-reading-title">Cómo leer las tonalidades</strong>
                <ul className="matrix-heatmap-reading-list muted small">
                  <li>
                    <strong>Periodo seleccionado</strong> y <strong>Proyección</strong>: verde más intenso = más
                    incidentes en esa celda; cada panel tiene escala propia.
                  </li>
                  <li>
                    <strong>Diferencia</strong>: rojo = la proyección espera más que el volumen observado en esa
                    celda; verde = espera menos (reparto proporcional, no predicción celda a celda).
                  </li>
                </ul>
              </div>
            )}
            {showMatrixHeatmaps ? (
              <div className="heatmap-desktop-shell">
                <div className="matrix-compare-wrap matrix-compare-wrap-proy">
                  <Heatmap title="Periodo seleccionado" grid={gridPeriodo} max={maxPeriodo} />
                  <Heatmap title={`Proyección (${horizonteMeses} mes(es))`} grid={gridProy} max={maxProy} />
                  <Heatmap
                    title="Diferencia (proyección − periodo)"
                    grid={gridDelta}
                    max={maxDelta}
                    mode="delta"
                    deltaLegend="proyeccion"
                    serieMatriz={serieMatriz}
                  />
                </div>
              </div>
            ) : (
              <div className="matrix-mobile-stack">
                <div className="matrix-mobile-chart">
                  <h4 className="matrix-mobile-title">Incidentes por hora (suma semanal)</h4>
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
                        <XAxis dataKey="horaLabel" tick={{ fontSize: 10 }} />
                        <YAxis allowDecimals={false} tick={{ fontSize: 10 }} width={yAxisTickWidth} />
                        <Tooltip />
                        <Legend {...legendTopPropsResolved} />
                        <Line
                          type="monotone"
                          dataKey="periodo"
                          name="Periodo seleccionado"
                          stroke="#0f766e"
                          dot={false}
                        />
                        <Line
                          type="monotone"
                          dataKey="proyeccion"
                          name={`Proyección (${horizonteMeses} mes)`}
                          stroke="#7c3aed"
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            )}
            {matrizProyectada?.meta?.limitaciones && (
              <p className="muted small carga-limitaciones">{matrizProyectada.meta.limitaciones}</p>
            )}
          </>
        )}
      </section>

      {diaSemanaProyectado?.serie?.length > 0 && (
        <section className="panel patrones-pred-panel chart-panel-comparativo">
          <h2>Por día de la semana (P13)</h2>
          <p className="muted small">
            Barras: incidentes en el <strong>periodo seleccionado</strong> vs <strong>proyección</strong> repartida
            por día (mismo horizonte y modelo que arriba). El color del periodo sigue la concentración vs. un reparto
            uniforme (~14,3% por día).
          </p>
          <div className="risk-legend">
            <span className="risk-chip risk-chip-alto">Carga alta (obs.)</span>
            <span className="risk-chip risk-chip-medio">Carga media</span>
            <span className="risk-chip risk-chip-bajo">Carga baja</span>
          </div>
          <div className="chart-box chart-box-tall">
            <ResponsiveContainer width="100%" height={barChartCompareHeight}>
              <BarChart data={diaChart} margin={barChartCompareMargin} barCategoryGap="18%">
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis
                  dataKey="dia"
                  tick={{ fontSize: chartLayoutCompact ? 9 : 11 }}
                  {...(chartLayoutCompact
                    ? { angle: -20, textAnchor: 'end', height: 42 }
                    : { angle: 0, textAnchor: 'middle' })}
                />
                <YAxis allowDecimals={false} tick={{ fontSize: chartLayoutCompact ? 9 : 11 }} width={yAxisTickWidth} />
                <Tooltip />
                <Legend {...legendTopPropsResolved} />
                <Bar dataKey="incidentes_observados_periodo" name="Periodo seleccionado" radius={[4, 4, 0, 0]}>
                  {diaChart.map((d, i) => (
                    <Cell
                      key={`obs-${i}`}
                      fill={
                        PATRON_RIESGO_COLOR[d.carga_dia_nivel_observado] ?? PATRON_RIESGO_COLOR.bajo
                      }
                    />
                  ))}
                </Bar>
                <Bar
                  dataKey="incidentes_proyectados_horizonte"
                  name={`Proyección (${horizonteMeses} mes(es))`}
                  fill="#7c3aed"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="risk-grid">
            {diaChart.map((d) => (
              <div
                key={`patron-dia-${d.dia_semana}`}
                className="risk-item"
                style={{
                  borderLeft: `4px solid ${PATRON_RIESGO_COLOR[d.carga_dia_nivel_proyectado] ?? PATRON_RIESGO_COLOR.bajo}`,
                  background: '#f8fafc',
                }}
              >
                <strong>{d.dia}</strong>: proyección <strong>{d.carga_dia_nivel_proyectado}</strong> —{' '}
                {Number(d.incidentes_proyectados_horizonte).toLocaleString('es-CO')} incidentes esperados (
                {Number(d.participacion_proyectada_pct).toLocaleString('es-CO', { maximumFractionDigits: 1 })}% del
                total proyectado)
              </div>
            ))}
          </div>
          {diaSemanaProyectado?.meta?.limitaciones && (
            <p className="muted small carga-limitaciones">{diaSemanaProyectado.meta.limitaciones}</p>
          )}
        </section>
      )}
    </>
  )
}
