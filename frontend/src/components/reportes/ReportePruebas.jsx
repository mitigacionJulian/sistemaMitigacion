function estadoLabel(estado) {
  const map = {
    passed: 'Pasó',
    failed: 'Falló',
    broken: 'Roto',
    skipped: 'Omitido',
  }
  return map[estado] || estado
}

function formatDuracion(ms) {
  if (ms == null || ms <= 0) return '—'
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(2)} s`
}

function ReporteSection({ title, children, hint }) {
  return (
    <section className="reporte-section">
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

export function ReportePruebas({ cuerpo }) {
  const resumen = cuerpo?.resumen ?? {}
  const ejecucion = cuerpo?.ejecucion ?? {}
  const kpis = [
    { label: 'Total', value: resumen.total ?? 0 },
    { label: 'Pasaron', value: resumen.pasaron ?? 0 },
    { label: 'Fallaron', value: resumen.fallaron ?? 0 },
    { label: 'Rotos', value: resumen.rotos ?? 0 },
    { label: 'Omitidos', value: resumen.omitidos ?? 0 },
  ]

  return (
    <>
      <ReporteSection
        title="Resumen de ejecución"
        hint="Resultados de la suite pytest del backend (salida Allure en JSON). Solo uso administrativo y de validación técnica."
      >
        <dl className="reporte-meta-grid reporte-pruebas-ejecucion">
          <div>
            <dt>Estado</dt>
            <dd>{ejecucion.estado || '—'}</dd>
          </div>
          <div>
            <dt>Código salida pytest</dt>
            <dd>{ejecucion.codigo_salida ?? '—'}</dd>
          </div>
          <div>
            <dt>Ejecutado por</dt>
            <dd>{ejecucion.iniciado_por || '—'}</dd>
          </div>
          <div>
            <dt>Finalizado</dt>
            <dd>{ejecucion.finalizado_en || '—'}</dd>
          </div>
        </dl>
        <div className="reporte-pruebas-kpis">
          {kpis.map((kpi) => (
            <div key={kpi.label} className="reporte-pruebas-kpi">
              <span className="muted small">{kpi.label}</span>
              <strong>{kpi.value}</strong>
            </div>
          ))}
          <div className="reporte-pruebas-kpi">
            <span className="muted small">Duración total</span>
            <strong>{formatDuracion(resumen.duracion_ms)}</strong>
          </div>
        </div>
      </ReporteSection>

      <ReporteSection title="Resultados por módulo">
        <ReporteTable
          columns={[
            { key: 'epic', label: 'Módulo' },
            { key: 'total', label: 'Total', className: 'num' },
            { key: 'pasaron', label: 'Pasaron', className: 'num' },
            { key: 'fallaron', label: 'Fallaron', className: 'num' },
            { key: 'rotos', label: 'Rotos', className: 'num' },
            { key: 'omitidos', label: 'Omitidos', className: 'num' },
          ]}
          rows={resumen.por_epic ?? []}
        />
      </ReporteSection>

      {(resumen.fallos?.length ?? 0) > 0 && (
        <ReporteSection title="Fallos y errores">
          <ReporteTable
            columns={[
              { key: 'nombre', label: 'Prueba' },
              { key: 'estado', label: 'Estado', render: (r) => estadoLabel(r.estado) },
              { key: 'epic', label: 'Módulo' },
              { key: 'feature', label: 'Feature' },
              { key: 'mensaje', label: 'Mensaje' },
            ]}
            rows={resumen.fallos}
          />
        </ReporteSection>
      )}

      <ReporteSection
        title="Detalle de casos"
        hint="Listado completo de pruebas registradas en la última ejecución."
      >
        <ReporteTable
          columns={[
            { key: 'nombre', label: 'Prueba' },
            { key: 'estado', label: 'Estado', render: (r) => estadoLabel(r.estado) },
            { key: 'epic', label: 'Módulo' },
            { key: 'feature', label: 'Feature' },
            { key: 'categoria', label: 'Categoría' },
            { key: 'duracion_ms', label: 'Duración', className: 'num', render: (r) => formatDuracion(r.duracion_ms) },
          ]}
          rows={(resumen.casos ?? []).map((row, i) => ({ ...row, _key: `${row.epic}-${row.nombre}-${i}` }))}
        />
      </ReporteSection>
    </>
  )
}
