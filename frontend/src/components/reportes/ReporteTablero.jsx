import {
  TableroClaseIncidenteChart,
  TableroDiaSemanaChart,
  TableroEvolucionChart,
  TableroGravedadChart,
  TableroMatrizHeatmaps,
} from './TableroReportCharts.jsx'
import {
  formatReporteFechaCorta,
  formatReporteNumero,
  formatReporteVariacion,
} from './reporteFormat.js'

function ReporteSection({ title, children, hint, className = '' }) {
  return (
    <section className={`reporte-section ${className}`.trim()}>
      <h2 className="reporte-section-title">{title}</h2>
      {hint ? <p className="muted small reporte-section-hint">{hint}</p> : null}
      {children}
    </section>
  )
}

function ReporteTable({ columns, rows, emptyMessage = 'Sin registros' }) {
  return (
    <div className="reporte-table-wrap">
      <table className="table reporte-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} className={col.className}>
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="muted">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row, i) => (
              <tr key={row._key ?? i}>
                {columns.map((col) => (
                  <td key={col.key} className={col.className}>
                    {col.render ? col.render(row) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}

function TopsBlock({ title, hint, rows, nameKey, nameLabel = 'Categoría' }) {
  return (
    <div className="reporte-tops-block">
      <h3 className="reporte-tops-title">{title}</h3>
      {hint ? <p className="muted small">{hint}</p> : null}
      <ReporteTable
        columns={[
          { key: 'rank', label: '#' },
          { key: 'nombre', label: nameLabel, render: (r) => r[nameKey] ?? r.nombre },
          { key: 'total', label: 'Víct.', className: 'num', render: (r) => formatReporteNumero(r.total_victimas) },
          { key: 'pct', label: '%', className: 'num', render: (r) => formatReporteNumero(r.porcentaje) },
        ]}
        rows={rows}
      />
    </div>
  )
}

export function ReporteTablero({ cuerpo }) {
  const kpis = cuerpo?.kpis
  const kA = kpis?.kpis_periodo_actual
  const cmp = kpis?.comparacion
  const kMeta = kpis?.meta

  const evolucion = cuerpo?.evolucion_mensual
  const diaSemana = cuerpo?.dia_semana
  const matriz = cuerpo?.matriz_dia_hora
  const clase = cuerpo?.distribucion_clase_incidente
  const gravedad = cuerpo?.distribucion_gravedad
  const tops = cuerpo?.tops

  const periodoHint =
    kMeta &&
    `Periodo actual: ${formatReporteFechaCorta(kMeta.fecha_inicio)} — ${formatReporteFechaCorta(kMeta.fecha_fin)}. Comparación con ${formatReporteFechaCorta(kMeta.fecha_inicio_anterior)} — ${formatReporteFechaCorta(kMeta.fecha_fin_anterior)}.`

  return (
    <div className="reporte-tablero">
      {kA && cmp && (
        <ReporteSection title="Indicadores clave (KPIs)" hint={periodoHint}>
          <ReporteTable
            columns={[
              { key: 'indicador', label: 'Indicador' },
              { key: 'actual', label: 'Periodo actual', className: 'num' },
              { key: 'anterior', label: 'Año anterior equiv.', className: 'num' },
              { key: 'variacion', label: 'Variación' },
            ]}
            rows={[
              {
                _key: 'inc',
                indicador: 'Total incidentes',
                actual: formatReporteNumero(kA.total_incidentes),
                anterior: formatReporteNumero(cmp.total_incidentes?.valor_anterior),
                variacion: formatReporteVariacion(cmp.total_incidentes?.variacion_pct),
              },
              {
                _key: 'vic',
                indicador: 'Total víctimas',
                actual: formatReporteNumero(kA.total_victimas),
                anterior: formatReporteNumero(cmp.total_victimas?.valor_anterior),
                variacion: formatReporteVariacion(cmp.total_victimas?.variacion_pct),
              },
              {
                _key: 'fat',
                indicador: 'Víctimas fatales',
                actual: formatReporteNumero(kA.victimas_fatales),
                anterior: formatReporteNumero(cmp.victimas_fatales?.valor_anterior),
                variacion: formatReporteVariacion(cmp.victimas_fatales?.variacion_pct),
              },
              {
                _key: 'tasa',
                indicador: 'Tasa incidentes / día',
                actual: formatReporteNumero(kA.tasa_incidentes_por_dia, { maximumFractionDigits: 2 }),
                anterior: formatReporteNumero(cmp.tasa_incidentes_por_dia?.valor_anterior, {
                  maximumFractionDigits: 2,
                }),
                variacion: formatReporteVariacion(cmp.tasa_incidentes_por_dia?.variacion_pct),
              },
            ]}
          />
          {kMeta?.nota_territorio ? (
            <p className="muted small reporte-note">{kMeta.nota_territorio}</p>
          ) : null}
        </ReporteSection>
      )}

      {evolucion?.serie?.length > 0 && (
        <ReporteSection
          title="Evolución mensual comparativa"
          hint={
            evolucion.meta?.descripcion ||
            'Totales por mes natural; barras apiladas de incidentes y víctimas (actual vs año anterior).'
          }
        >
          <TableroEvolucionChart evolucion={evolucion} />
        </ReporteSection>
      )}

      {diaSemana?.serie?.length > 0 && (
        <ReporteSection
          title="Por día de la semana (concentración en la semana)"
          hint="Mismas barras apiladas y semáforo de concentración que en el tablero interactivo."
        >
          <TableroDiaSemanaChart diaSemana={diaSemana} />
        </ReporteSection>
      )}

      {matriz?.serie?.length > 0 && (
        <ReporteSection
          className="reporte-section-matriz"
          title="Matriz día × hora comparativa"
          hint="Tres tablas con conteo por día y hora; la tercera muestra la diferencia (actual − anterior)."
        >
          <TableroMatrizHeatmaps matriz={matriz} periodoMeta={kMeta} />
        </ReporteSection>
      )}

      {clase?.serie?.length > 0 && (
        <ReporteSection title="Incidentes por clase" hint="Barras horizontales comparando periodo actual y año anterior.">
          <TableroClaseIncidenteChart clase={clase} />
        </ReporteSection>
      )}

      {gravedad?.serie?.length > 0 && (
        <ReporteSection title="Víctimas por gravedad" hint="Distribución de víctimas por nivel de gravedad.">
          <TableroGravedadChart gravedad={gravedad} />
        </ReporteSection>
      )}

      {tops?.meta && (
        <ReporteSection
          title="Rankings del periodo"
          hint={`Top ${tops.meta.limite ?? 10} por categoría sobre ${formatReporteNumero(tops.meta.total_victimas_periodo)} víctimas en el periodo.`}
        >
          <div className="reporte-tops-grid">
            <TopsBlock title="Sexo" rows={tops.sexo || []} nameKey="nombre" nameLabel="Sexo" />
            <TopsBlock
              title="Edad"
              hint="Por edad declarada (años)."
              rows={tops.edad || []}
              nameKey="etiqueta"
              nameLabel="Edad"
            />
            <TopsBlock title="Condición en la vía" rows={tops.condicion || []} nameKey="nombre" nameLabel="Condición" />
            <TopsBlock title="Comuna" rows={tops.comuna || []} nameKey="nombre" nameLabel="Comuna" />
            <TopsBlock title="Barrio" rows={tops.barrio || []} nameKey="nombre" nameLabel="Barrio" />
          </div>
        </ReporteSection>
      )}
    </div>
  )
}
