export const PARTICIPACION_CELDA_HELP =
  'Participación: porcentaje de los incidentes del polígono que cayó en esa celda. ' +
  'Ej.: 27 % significa que más de una cuarta parte del total del área se concentró en un tramo pequeño.'

function fmtNum(n, digits = 0) {
  if (n == null || Number.isNaN(Number(n))) return '—'
  return Number(n).toLocaleString('es-CO', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function pctArea(conteo, total) {
  const t = Number(total)
  const c = Number(conteo)
  if (!t || t <= 0 || !Number.isFinite(c)) return null
  return (c / t) * 100
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
  const hot = resumen.celda_mas_caliente
  const hotPct =
    hot?.porcentaje_area ??
    pctArea(hot?.conteo, resumen.total_incidentes)

  return (
    <section className="landing-map-area-analisis" aria-labelledby="map-area-analisis-title">
      <h3 id="map-area-analisis-title" className="landing-map-area-analisis-title">
        Análisis del área seleccionada
      </h3>
      <p className="muted small landing-map-area-analisis-note">{resumen.nota}</p>
      <p className="muted small landing-map-density-help">{PARTICIPACION_CELDA_HELP}</p>
      {topCeldas.length > 0 && (
        <p className="muted small landing-map-area-rank-hint">
          Los números sobre el mapa coinciden con la columna <strong>#</strong> en «Top celdas en el
          área» (solo celdas con incidentes; las grises no llevan número).
        </p>
      )}

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

      {hot && (
        <p className="small landing-map-area-hotspot">
          Celda más caliente: <strong>{fmtNum(hot.conteo)}</strong> incidentes
          {hotPct != null && (
            <>
              {' '}
              — <strong>{fmtNum(hotPct, 1)} %</strong> del total del área
            </>
          )}
          .
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
                  <th>% área</th>
                </tr>
              </thead>
              <tbody>
                {topCeldas.map((c) => (
                  <tr key={c.rank}>
                    <td>{c.rank}</td>
                    <td>{fmtNum(c.conteo)}</td>
                    <td>
                      {fmtNum(
                        c.porcentaje_area ?? pctArea(c.conteo, resumen.total_incidentes),
                        1,
                      )}
                    </td>
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
