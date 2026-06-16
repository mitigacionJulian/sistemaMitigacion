import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
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
  mapClaseIncidenteChart,
  mapGravedadChart,
  nivelCargaSemana,
  participacionSemanalPct,
  ratioVsUniforme,
  riesgoColor,
} from '../tablero/tableroChartUtils.js'
import { formatReporteFechaCorta } from './reporteFormat.js'

const CHART_PRINT_PROPS = { isAnimationActive: false }

function heatmapCellBackground(v, max, mode = 'base') {
  const intensity = max > 0 ? Math.min(1, Math.abs(v) / max) : 0
  if (mode === 'delta') {
    if (v > 0) return `rgba(185, 28, 28, ${0.15 + intensity * 0.75})`
    if (v < 0) return `rgba(15, 118, 110, ${0.15 + intensity * 0.75})`
    return '#f1f5f9'
  }
  return `rgba(15, 118, 110, ${0.12 + intensity * 0.82})`
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

function formatMatrizValor(v, mode) {
  const n = Number(v) || 0
  if (mode === 'delta') {
    if (n > 0) return `+${n}`
    return String(n)
  }
  return String(n)
}

function MatrizLeyenda({ mode }) {
  if (mode === 'delta') {
    return (
      <div className="reporte-matriz-leyenda heatmap-delta-legend">
        <p className="reporte-matriz-leyenda-intro muted small">
          Cada celda muestra <strong>actual − anterior</strong> (incidentes en ese día y hora).
        </p>
        <ul className="reporte-matriz-leyenda-list">
          <li>
            <span className="reporte-matriz-leyenda-muestra reporte-matriz-cell-up">+N</span>
            <strong>Positivo:</strong> hubo <strong>más incidentes</strong> en el periodo actual que en el mismo día y
            hora del año anterior (aumento de accidentalidad en esa franja).
          </li>
          <li>
            <span className="reporte-matriz-leyenda-muestra reporte-matriz-cell-down">−N</span>
            <strong>Negativo:</strong> hubo <strong>menos incidentes</strong> en el periodo actual (disminución en esa
            franja).
          </li>
          <li>
            <span className="reporte-matriz-leyenda-muestra reporte-matriz-cell-neutral">0</span>
            <strong>Cero:</strong> sin cambio respecto al año anterior en ese día y hora.
          </li>
        </ul>
      </div>
    )
  }

  return (
    <p className="reporte-matriz-leyenda muted small">
      Cada celda indica el <strong>número de incidentes</strong> en esa combinación día de la semana × hora (0–23 h).
      El tono de fondo solo ayuda a comparar intensidades dentro de esta matriz.
    </p>
  )
}

function ReporteMatrizTable({ title, grid, max, mode = 'base' }) {
  return (
    <div className="reporte-matriz-panel">
      <h4 className="reporte-matriz-title">{title}</h4>
      <MatrizLeyenda mode={mode} />
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

export function TableroEvolucionChart({ evolucion }) {
  if (!evolucion?.serie?.length) return null
  const n = evolucion.serie.length
  const angle = n > 8 ? -30 : 0
  const textAnchor = n > 8 ? 'end' : 'middle'
  const xHeight = n > 8 ? 52 : 36

  return (
    <ReportChartBox height={400}>
      <BarChart data={evolucion.serie} margin={BAR_COMPARE_MARGIN} barCategoryGap="18%">
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
        <XAxis
          dataKey="mes_etiqueta"
          tick={{ fontSize: 11 }}
          angle={angle}
          textAnchor={textAnchor}
          height={xHeight}
          interval={0}
          label={{
            value: 'Mes (periodo seleccionado)',
            position: 'bottom',
            offset: n > 8 ? 28 : 14,
            fontSize: 12,
            fill: '#64748b',
          }}
        />
        <YAxis
          allowDecimals={false}
          tick={{ fontSize: 11 }}
          width={48}
          label={{
            value: 'Cantidad (barras apiladas)',
            angle: -90,
            position: 'left',
            offset: 10,
            style: { textAnchor: 'middle', fontSize: 12, fill: '#64748b' },
          }}
        />
        <Tooltip />
        <Legend {...LEGEND_TOP_PROPS} />
        <Bar
          {...CHART_PRINT_PROPS}
          stackId="act"
          dataKey="incidentes_periodo_actual"
          name="Incidentes (periodo actual)"
          fill="#0f766e"
        />
        <Bar
          {...CHART_PRINT_PROPS}
          stackId="act"
          dataKey="victimas_periodo_actual"
          name="Víctimas (periodo actual)"
          fill="#5eead4"
          radius={[4, 4, 0, 0]}
        />
        <Bar
          {...CHART_PRINT_PROPS}
          stackId="ant"
          dataKey="incidentes_periodo_anterior"
          name="Incidentes (año anterior)"
          fill="#475569"
        />
        <Bar
          {...CHART_PRINT_PROPS}
          stackId="ant"
          dataKey="victimas_periodo_anterior"
          name="Víctimas (año anterior)"
          fill="#cbd5e1"
          radius={[4, 4, 0, 0]}
        />
      </BarChart>
    </ReportChartBox>
  )
}

export function TableroDiaSemanaChart({ diaSemana }) {
  if (!diaSemana?.serie?.length) return null

  return (
    <>
      <div className="risk-legend reporte-risk-legend">
        <span className="risk-chip risk-chip-alto">Alto: ratio ≥ 1,45</span>
        <span className="risk-chip risk-chip-medio">Medio: ratio ≥ 1,12</span>
        <span className="risk-chip risk-chip-bajo">Bajo: ratio &lt; 1,12</span>
      </div>
      <ReportChartBox height={400}>
        <BarChart data={diaSemana.serie} margin={BAR_COMPARE_MARGIN} barCategoryGap="18%">
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis
            dataKey="dia"
            tick={{ fontSize: 11 }}
            label={{
              value: 'Día de la semana',
              position: 'bottom',
              offset: 12,
              fontSize: 12,
              fill: '#64748b',
            }}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 11 }}
            width={48}
            label={{
              value: 'Cantidad (barras apiladas)',
              angle: -90,
              position: 'left',
              offset: 10,
              style: { textAnchor: 'middle', fontSize: 12, fill: '#64748b' },
            }}
          />
          <Tooltip />
          <Legend {...LEGEND_TOP_PROPS} />
          <Bar
            {...CHART_PRINT_PROPS}
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
            {...CHART_PRINT_PROPS}
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
            {...CHART_PRINT_PROPS}
            stackId="ant"
            dataKey="incidentes_periodo_anterior"
            name="Incidentes (año anterior)"
            fill="#475569"
          />
          <Bar
            {...CHART_PRINT_PROPS}
            stackId="ant"
            dataKey="victimas_periodo_anterior"
            name="Víctimas (año anterior)"
            fill="#cbd5e1"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ReportChartBox>
      <div className="risk-grid reporte-risk-grid">
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
              {pct.toLocaleString('es-CO', { maximumFractionDigits: 2 })}% del total semanal
              {ratio != null && !Number.isNaN(ratio) ? (
                <> (ratio vs. uniforme: {ratio.toLocaleString('es-CO', { maximumFractionDigits: 2 })})</>
              ) : null}
            </div>
          )
        })}
      </div>
    </>
  )
}

export function TableroMatrizHeatmaps({ matriz, periodoMeta }) {
  const serie = matriz?.serie
  if (!serie?.length) return null

  const gridAct = buildHeatmapGrid(serie, 'total_incidentes_actual')
  const gridAnt = buildHeatmapGrid(serie, 'total_incidentes_anterior')
  const gridDelta = buildHeatmapGrid(serie, 'delta_abs')
  const maxAct = Math.max(0, ...gridAct.flat())
  const maxAnt = Math.max(0, ...gridAnt.flat())
  const maxDelta = Math.max(0, ...gridDelta.flat().map((v) => Math.abs(v)))

  return (
    <div className="reporte-matriz-wrap">
      <p className="muted small reporte-section-hint">
        Periodo actual ({formatReporteFechaCorta(periodoMeta?.fecha_inicio)} —{' '}
        {formatReporteFechaCorta(periodoMeta?.fecha_fin)}) vs mismo intervalo del año anterior (
        {formatReporteFechaCorta(periodoMeta?.fecha_inicio_anterior)} —{' '}
        {formatReporteFechaCorta(periodoMeta?.fecha_fin_anterior)}).
      </p>
      <div className="reporte-matriz-panels">
        <ReporteMatrizTable title="Periodo actual — incidentes por día y hora" grid={gridAct} max={maxAct} />
        <ReporteMatrizTable title="Año anterior — incidentes por día y hora" grid={gridAnt} max={maxAnt} />
        <ReporteMatrizTable
          title="Diferencia (actual − anterior)"
          grid={gridDelta}
          max={maxDelta}
          mode="delta"
        />
      </div>
    </div>
  )
}

function CompareBarChartVertical({ data, categoryKey, categoryFullKey, codigoKey, valueLabel }) {
  const height = Math.max(360, data.length * 40 + 100)
  return (
    <ReportChartBox height={height}>
      <BarChart
        layout="vertical"
        data={data}
        margin={{ top: 52, right: 24, left: 4, bottom: 52 }}
        barCategoryGap="12%"
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
        <XAxis
          type="number"
          allowDecimals={false}
          tick={{ fontSize: 11 }}
          label={{
            value: valueLabel,
            position: 'bottom',
            offset: 14,
            fontSize: 12,
            fill: '#64748b',
          }}
        />
        <YAxis type="category" dataKey={categoryKey} width={148} tick={{ fontSize: 11 }} interval={0} />
        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const row = payload[0].payload
            const full = row[categoryFullKey]
            const title = row[codigoKey] ? `${full} (${row[codigoKey]})` : full
            return (
              <div className="recharts-default-tooltip reporte-chart-tooltip">
                <p className="small" style={{ marginBottom: 8, fontWeight: 600 }}>
                  {title}
                </p>
                <p className="small muted" style={{ margin: '4px 0' }}>
                  Periodo actual: <strong>{row.actual.toLocaleString('es-CO')}</strong> (
                  {Number(row.pctActual ?? 0).toLocaleString('es-CO', { maximumFractionDigits: 1 })}%)
                </p>
                <p className="small muted" style={{ margin: '4px 0' }}>
                  Año anterior: <strong>{row.anterior.toLocaleString('es-CO')}</strong> (
                  {Number(row.pctAnterior ?? 0).toLocaleString('es-CO', { maximumFractionDigits: 1 })}%)
                </p>
              </div>
            )
          }}
        />
        <Legend {...LEGEND_TOP_PROPS} />
        <Bar {...CHART_PRINT_PROPS} dataKey="actual" name="Periodo actual" fill="#0ea5e9" radius={[0, 4, 4, 0]} />
        <Bar
          {...CHART_PRINT_PROPS}
          dataKey="anterior"
          name="Año anterior equivalente"
          fill="#94a3b8"
          radius={[0, 4, 4, 0]}
        />
      </BarChart>
    </ReportChartBox>
  )
}

export function TableroClaseIncidenteChart({ clase }) {
  const data = mapClaseIncidenteChart(clase?.serie)
  if (!data.length) return null
  return (
    <CompareBarChartVertical
      data={data}
      categoryKey="clase"
      categoryFullKey="claseFull"
      codigoKey="codigo"
      valueLabel="Número de incidentes"
    />
  )
}

export function TableroGravedadChart({ gravedad }) {
  const data = mapGravedadChart(gravedad?.serie)
  if (!data.length) return null
  return (
    <CompareBarChartVertical
      data={data}
      categoryKey="gravedad"
      categoryFullKey="gravedadFull"
      codigoKey="codigo"
      valueLabel="Número de víctimas"
    />
  )
}
