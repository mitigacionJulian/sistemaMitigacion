import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  BAR_COMPARE_MARGIN,
  DIAS_CORTO,
  LEGEND_TOP_PROPS,
  buildHeatmapGrid,
} from '../tablero/tableroChartUtils.js'
import {
  CARGA_CATEGORIA_COLOR,
  PATRON_RIESGO_COLOR,
  PRIORIDAD_NIVEL_COLOR,
  buildCargaComparativaData,
  buildPrediccionesLineData,
  buildPrioridadChartData,
  buildProporcionLineData,
} from './prediccionesReportChartUtils.js'

const CHART_PRINT_PROPS = { isAnimationActive: false }

const LABEL_PROPS = {
  fontSize: 9,
  fill: '#334155',
  fontWeight: 600,
}

function fmtEtiquetaGrafico(value, { decimales = 0, sufijo = '' } = {}) {
  if (value == null || value === '') return ''
  const n = Number(value)
  if (Number.isNaN(n)) return ''
  return `${n.toLocaleString('es-CO', { maximumFractionDigits: decimales })}${sufijo}`
}

function ReportChartBox({ height, children }) {
  return (
    <div className="reporte-chart-box chart-box chart-box-tall" style={{ height, minHeight: height }}>
      <ResponsiveContainer width="100%" height={height}>
        {children}
      </ResponsiveContainer>
    </div>
  )
}

function heatmapCellBackground(v, max, mode = 'base') {
  const intensity = max > 0 ? Math.min(1, Math.abs(v) / max) : 0
  if (mode === 'delta') {
    if (v > 0) return `rgba(185, 28, 28, ${0.15 + intensity * 0.75})`
    if (v < 0) return `rgba(15, 118, 110, ${0.15 + intensity * 0.75})`
    return '#f1f5f9'
  }
  return `rgba(15, 118, 110, ${0.12 + intensity * 0.82})`
}

function formatMatrizValor(v, mode) {
  const n = Number(v) || 0
  if (mode === 'delta') {
    if (n > 0) return `+${n}`
    return String(n)
  }
  return String(n)
}

function ReporteMatrizTable({ title, grid, max, mode = 'base' }) {
  return (
    <div className="reporte-matriz-panel">
      <h4 className="reporte-matriz-title">{title}</h4>
      <div className="reporte-matriz-table-wrap">
        <table className="table reporte-matriz-table">
          <thead>
            <tr>
              <th className="reporte-matriz-corner" scope="col">
                Día \ Hora
              </th>
              {Array.from({ length: 24 }, (_, h) => (
                <th key={`h-${h}`} className="reporte-matriz-hour" scope="col">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {grid.map((row, di) => (
              <tr key={`row-${di}`}>
                <th className="reporte-matriz-day" scope="row">
                  {DIAS_CORTO[di]}
                </th>
                {row.map((v, hi) => {
                  const n = Number(v) || 0
                  const cellClass =
                    mode === 'delta'
                      ? n > 0
                        ? 'reporte-matriz-cell-up'
                        : n < 0
                          ? 'reporte-matriz-cell-down'
                          : 'reporte-matriz-cell-neutral'
                      : 'reporte-matriz-cell-count'
                  return (
                    <td
                      key={`${di}-${hi}`}
                      className={`reporte-matriz-cell ${cellClass}`}
                      style={{ background: heatmapCellBackground(n, max, mode) }}
                    >
                      {formatMatrizValor(n, mode)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function PrediccionesMensualesChart({ predicciones, variableLabel = 'Valor' }) {
  if (!predicciones?.serie_historica?.length && !predicciones?.proyeccion?.length) return null
  if (predicciones?.meta?.sin_modelo) return null

  const data = buildPrediccionesLineData(predicciones.serie_historica, predicciones.proyeccion)
  if (!data.length) return null

  const n = data.length
  const angle = n > 8 ? -28 : 0
  const textAnchor = n > 8 ? 'end' : 'middle'
  const xHeight = n > 8 ? 52 : 36

  return (
    <ReportChartBox height={360}>
      <LineChart
        data={data}
        margin={{ top: 56, right: 16, left: 12, bottom: n > 8 ? 44 : 36 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="mes"
          tick={{ fontSize: 10 }}
          angle={angle}
          textAnchor={textAnchor}
          height={xHeight}
          interval={0}
        />
        <YAxis allowDecimals tick={{ fontSize: 10 }} width={44} />
        <Tooltip />
        <Legend {...LEGEND_TOP_PROPS} />
        <Line
          {...CHART_PRINT_PROPS}
          type="monotone"
          dataKey="observados"
          name={`Observado (${variableLabel})`}
          stroke="#0f766e"
          strokeWidth={2}
          dot={{ r: 3 }}
          connectNulls={false}
        >
          <LabelList
            dataKey="observados"
            position="top"
            {...LABEL_PROPS}
            formatter={(v) => fmtEtiquetaGrafico(v)}
          />
        </Line>
        <Line
          {...CHART_PRINT_PROPS}
          type="monotone"
          dataKey="ajuste"
          name="Ajuste / proyección"
          stroke="#7c3aed"
          strokeWidth={2}
          strokeDasharray="6 4"
          dot={{ r: 3 }}
          connectNulls
        >
          <LabelList
            dataKey="ajuste"
            position="top"
            {...LABEL_PROPS}
            fill="#6d28d9"
            formatter={(v) => fmtEtiquetaGrafico(v, { decimales: 1 })}
          />
        </Line>
      </LineChart>
    </ReportChartBox>
  )
}

export function PrioridadTerritorialChart({ prioridad, nivel = 'comuna' }) {
  if (!prioridad?.ranking?.length) return null
  const data = buildPrioridadChartData(prioridad.ranking, nivel)
  const height = Math.max(320, data.length * 36 + 100)

  return (
    <ReportChartBox height={height}>
      <BarChart
        layout="vertical"
        data={data}
        margin={{ top: 48, right: 52, left: 4, bottom: 40 }}
        barCategoryGap="14%"
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 10 }} />
        <YAxis type="category" dataKey="territorio" width={140} tick={{ fontSize: 10 }} interval={0} />
        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const row = payload[0].payload
            return (
              <div className="recharts-default-tooltip reporte-chart-tooltip">
                <p className="small" style={{ marginBottom: 6, fontWeight: 600 }}>
                  #{row.rank} — {row.territorioFull}
                </p>
                <p className="small muted">Índice: {row.indice.toLocaleString('es-CO')}</p>
              </div>
            )
          }}
        />
        <Legend {...LEGEND_TOP_PROPS} />
        <Bar {...CHART_PRINT_PROPS} dataKey="indice" name="Índice de prioridad" radius={[0, 4, 4, 0]}>
          {data.map((d, i) => (
            <Cell key={`prio-${i}`} fill={PRIORIDAD_NIVEL_COLOR[d.nivel] ?? PRIORIDAD_NIVEL_COLOR.bajo} />
          ))}
          <LabelList
            dataKey="indice"
            position="right"
            {...LABEL_PROPS}
            formatter={(v) => fmtEtiquetaGrafico(v, { decimales: 1 })}
          />
        </Bar>
      </BarChart>
    </ReportChartBox>
  )
}

export function ProporcionFatalesChart({ proporcion }) {
  if (!proporcion?.serie_historica?.length && !proporcion?.proyeccion?.length) return null
  const data = buildProporcionLineData(proporcion.serie_historica, proporcion.proyeccion)
  if (!data.length) return null

  const n = data.length
  const angle = n > 8 ? -28 : 0
  const textAnchor = n > 8 ? 'end' : 'middle'

  return (
    <ReportChartBox height={340}>
      <LineChart
        data={data}
        margin={{ top: 56, right: 16, left: 12, bottom: n > 8 ? 44 : 36 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="mes"
          tick={{ fontSize: 10 }}
          angle={angle}
          textAnchor={textAnchor}
          height={n > 8 ? 52 : 36}
          interval={0}
        />
        <YAxis tick={{ fontSize: 10 }} width={44} unit="%" />
        <Tooltip formatter={(v) => (v != null ? `${Number(v).toFixed(2)}%` : '—')} />
        <Legend {...LEGEND_TOP_PROPS} />
        <Line
          {...CHART_PRINT_PROPS}
          type="monotone"
          dataKey="pct"
          name="% fatales observado"
          stroke="#0f766e"
          strokeWidth={2}
          dot={{ r: 3 }}
          connectNulls={false}
        >
          <LabelList
            dataKey="pct"
            position="top"
            {...LABEL_PROPS}
            formatter={(v) => fmtEtiquetaGrafico(v, { decimales: 1, sufijo: '%' })}
          />
        </Line>
        <Line
          {...CHART_PRINT_PROPS}
          type="monotone"
          dataKey="ajuste"
          name="Ajuste / proyección %"
          stroke="#b45309"
          strokeWidth={2}
          strokeDasharray="6 4"
          dot={{ r: 3 }}
          connectNulls
        >
          <LabelList
            dataKey="ajuste"
            position="top"
            {...LABEL_PROPS}
            fill="#b45309"
            formatter={(v) => fmtEtiquetaGrafico(v, { decimales: 1, sufijo: '%' })}
          />
        </Line>
      </LineChart>
    </ReportChartBox>
  )
}

export function CargaEsperadaChart({ carga, nivel = 'comuna' }) {
  if (!carga?.ranking?.length) return null
  const data = buildCargaComparativaData(carga.ranking, nivel)
  const height = Math.max(320, data.length * 36 + 100)

  return (
    <ReportChartBox height={height}>
      <BarChart
        layout="vertical"
        data={data}
        margin={{ top: 48, right: 56, left: 4, bottom: 40 }}
        barCategoryGap="14%"
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 10 }} allowDecimals />
        <YAxis type="category" dataKey="nombre" width={148} tick={{ fontSize: 10 }} interval={0} />
        <Tooltip />
        <Legend {...LEGEND_TOP_PROPS} />
        <Bar {...CHART_PRINT_PROPS} dataKey="carga" name="Carga proyectada (horizonte)" radius={[0, 4, 4, 0]}>
          {data.map((d, i) => (
            <Cell key={`carga-${i}`} fill={CARGA_CATEGORIA_COLOR[d.categoria] ?? CARGA_CATEGORIA_COLOR.bajo} />
          ))}
          <LabelList
            dataKey="carga"
            position="right"
            {...LABEL_PROPS}
            formatter={(v) => fmtEtiquetaGrafico(v, { decimales: 1 })}
          />
        </Bar>
      </BarChart>
    </ReportChartBox>
  )
}

export function DiaSemanaProyectadoChart({ diaSemana }) {
  if (!diaSemana?.serie?.length) return null
  const data = diaSemana.serie

  return (
    <>
      <div className="risk-legend reporte-risk-legend">
        <span className="risk-chip risk-chip-alto">Carga alta (obs.)</span>
        <span className="risk-chip risk-chip-medio">Carga media</span>
        <span className="risk-chip risk-chip-bajo">Carga baja</span>
      </div>
      <ReportChartBox height={400}>
        <BarChart data={data} margin={{ ...BAR_COMPARE_MARGIN, top: 56 }} barCategoryGap="18%">
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis dataKey="dia" tick={{ fontSize: 11 }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 11 }} width={48} />
          <Tooltip />
          <Legend {...LEGEND_TOP_PROPS} />
          <Bar
            {...CHART_PRINT_PROPS}
            dataKey="incidentes_observados_periodo"
            name="Periodo seleccionado"
            radius={[4, 4, 0, 0]}
          >
            {data.map((d, i) => (
              <Cell
                key={`obs-${i}`}
                fill={PATRON_RIESGO_COLOR[d.carga_dia_nivel_observado] ?? PATRON_RIESGO_COLOR.bajo}
              />
            ))}
            <LabelList
              dataKey="incidentes_observados_periodo"
              position="top"
              {...LABEL_PROPS}
              formatter={(v) => fmtEtiquetaGrafico(v)}
            />
          </Bar>
          <Bar
            {...CHART_PRINT_PROPS}
            dataKey="incidentes_proyectados_horizonte"
            name="Proyección (horizonte)"
            fill="#7c3aed"
            radius={[4, 4, 0, 0]}
          >
            <LabelList
              dataKey="incidentes_proyectados_horizonte"
              position="top"
              {...LABEL_PROPS}
              fill="#6d28d9"
              formatter={(v) => fmtEtiquetaGrafico(v, { decimales: 1 })}
            />
          </Bar>
        </BarChart>
      </ReportChartBox>
    </>
  )
}

export function MatrizProyectadaHeatmaps({ matriz, horizonteMeses = 3 }) {
  const serie = matriz?.serie
  if (!serie?.length) return null

  const gridPeriodo = buildHeatmapGrid(serie, 'incidentes_observados_periodo')
  const gridProy = buildHeatmapGrid(serie, 'incidentes_proyectados_horizonte')
  const gridDelta = buildHeatmapGrid(serie, 'delta_proyeccion_menos_periodo')
  const maxPeriodo = Math.max(0, ...gridPeriodo.flat())
  const maxProy = Math.max(0, ...gridProy.flat())
  const maxDelta = Math.max(0, ...gridDelta.flat().map((v) => Math.abs(v)))

  return (
    <div className="reporte-matriz-wrap">
      {matriz.meta?.total_proyectado_horizonte != null && (
        <p className="muted small reporte-section-hint">
          Total periodo: {Number(matriz.meta.total_incidentes_periodo ?? 0).toLocaleString('es-CO')} · Total
          proyectado ({horizonteMeses} mes(es)):{' '}
          {Number(matriz.meta.total_proyectado_horizonte).toLocaleString('es-CO', {
            maximumFractionDigits: 1,
          })}
        </p>
      )}
      <div className="reporte-matriz-panels">
        <ReporteMatrizTable title="Periodo seleccionado" grid={gridPeriodo} max={maxPeriodo} />
        <ReporteMatrizTable title={`Proyección (${horizonteMeses} mes(es))`} grid={gridProy} max={maxProy} />
        <ReporteMatrizTable
          title="Diferencia (proyección − periodo)"
          grid={gridDelta}
          max={maxDelta}
          mode="delta"
        />
      </div>
    </div>
  )
}

export function MatrizPorHoraChart({ matriz, horizonteMeses = 3 }) {
  const porHora = matriz?.resumen?.por_hora
  if (!porHora?.length) return null

  const data = porHora.map((r) => ({
    horaLabel: `${r.hora}:00`,
    periodo: r.incidentes_observados,
    proyeccion: r.incidentes_proyectados,
    delta: r.delta,
  }))

  return (
    <ReportChartBox height={320}>
      <LineChart data={data} margin={{ top: 52, right: 12, left: 8, bottom: 28 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="horaLabel" tick={{ fontSize: 9 }} interval={1} />
        <YAxis allowDecimals={false} tick={{ fontSize: 10 }} width={40} />
        <Tooltip />
        <Legend {...LEGEND_TOP_PROPS} />
        <Line
          {...CHART_PRINT_PROPS}
          type="monotone"
          dataKey="periodo"
          name="Periodo seleccionado"
          stroke="#0f766e"
          dot={{ r: 2 }}
        >
          <LabelList
            dataKey="periodo"
            position="top"
            fontSize={8}
            fill="#0f766e"
            fontWeight={600}
            formatter={(v) => (v > 0 ? fmtEtiquetaGrafico(v) : '')}
          />
        </Line>
        <Line
          {...CHART_PRINT_PROPS}
          type="monotone"
          dataKey="proyeccion"
          name={`Proyección (${horizonteMeses} mes)`}
          stroke="#7c3aed"
          dot={{ r: 2 }}
        >
          <LabelList
            dataKey="proyeccion"
            position="bottom"
            fontSize={8}
            fill="#6d28d9"
            fontWeight={600}
            formatter={(v) => (v > 0 ? fmtEtiquetaGrafico(v, { decimales: 1 }) : '')}
          />
        </Line>
      </LineChart>
    </ReportChartBox>
  )
}
