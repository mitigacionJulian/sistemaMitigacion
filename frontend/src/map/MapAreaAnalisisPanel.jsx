function fmtNum(n, digits = 0) {
  if (n == null || Number.isNaN(Number(n))) return '—'
  return Number(n).toLocaleString('es-CO', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

/**
 * @param {{ resumen: object | null | undefined, loading?: boolean }} props
 */
export function MapAreaAnalisisPanel({ resumen, loading = false }) {
  if (!resumen && !loading) return null

  if (loading && !resumen) {
    return (
      <div className="landing-map-area-analisis muted small" role="status">
        Calculando resumen del área…
      </div>
    )
  }

  if (!resumen) return null

  const { clases_principales: clases = [], top_celdas: topCeldas = [] } = resumen

  return (
    <section className="landing-map-area-analisis" aria-labelledby="map-area-analisis-title">
      <h3 id="map-area-analisis-title" className="landing-map-area-analisis-title">
        Análisis del área seleccionada
      </h3>
      <p className="muted small landing-map-area-analisis-note">{resumen.nota}</p>

      <div className="landing-map-area-analisis-kpis">
        <div className="landing-map-area-kpi">
          <span className="landing-map-area-kpi-label">Superficie</span>
          <strong>{fmtNum(resumen.area_km2, 3)} km²</strong>
        </div>
        <div className="landing-map-area-kpi">
          <span className="landing-map-area-kpi-label">Incidentes</span>
          <strong>{fmtNum(resumen.total_incidentes)}</strong>
        </div>
        <div className="landing-map-area-kpi">
          <span className="landing-map-area-kpi-label">Densidad área</span>
          <strong>{fmtNum(resumen.densidad_incidentes_km2, 2)} / km²</strong>
        </div>
        <div className="landing-map-area-kpi">
          <span className="landing-map-area-kpi-label">Tasa diaria</span>
          <strong>{fmtNum(resumen.tasa_incidentes_por_dia, 2)} / día</strong>
        </div>
        <div className="landing-map-area-kpi">
          <span className="landing-map-area-kpi-label">Víctimas fatales</span>
          <strong>{fmtNum(resumen.victimas_fatales)}</strong>
        </div>
        <div className="landing-map-area-kpi">
          <span className="landing-map-area-kpi-label">Celdas con datos</span>
          <strong>
            {fmtNum(resumen.celdas_con_datos)} / {fmtNum(resumen.total_celdas_estimadas)}
          </strong>
        </div>
      </div>

      {resumen.celda_mas_caliente && (
        <p className="small landing-map-area-hotspot">
          Celda más caliente: <strong>{fmtNum(resumen.celda_mas_caliente.conteo)}</strong> incidentes
          ({fmtNum(resumen.celda_mas_caliente.densidad_por_km2, 1)} / km² en celda de{' '}
          {fmtNum(resumen.tamano_celda_m, 0)} m).
        </p>
      )}

      <div className="landing-map-area-analisis-cols">
        {clases.length > 0 && (
          <div className="landing-map-area-col">
            <h4 className="landing-map-area-col-title">Clases principales</h4>
            <ul className="landing-map-area-list">
              {clases.map((c) => (
                <li key={c.clase}>
                  <span>{c.clase}</span>
                  <span>
                    {fmtNum(c.conteo)} ({fmtNum(c.porcentaje, 1)}%)
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {topCeldas.length > 0 && (
          <div className="landing-map-area-col">
            <h4 className="landing-map-area-col-title">Top celdas en el área</h4>
            <table className="landing-map-area-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Inc.</th>
                  <th>Dens. / km²</th>
                </tr>
              </thead>
              <tbody>
                {topCeldas.map((c) => (
                  <tr key={c.rank}>
                    <td>{c.rank}</td>
                    <td>{fmtNum(c.conteo)}</td>
                    <td>{fmtNum(c.densidad_por_km2, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  )
}
