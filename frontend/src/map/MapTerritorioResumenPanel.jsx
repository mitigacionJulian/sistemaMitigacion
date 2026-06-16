export const RATIO_VS_CIUDAD_HELP =
  'Indicador G02: compara la densidad del territorio con la densidad promedio de Medellín en el mismo periodo y filtros. ' +
  'Se calcula como densidad del territorio ÷ densidad de la ciudad. ' +
  'Ej.: 2× significa el doble de incidentes por km² que el promedio urbano; 0,5× significa la mitad.'

function fmtNum(n, digits = 0) {
  if (n == null || Number.isNaN(Number(n))) return '—'
  return Number(n).toLocaleString('es-CO', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

/**
 * @param {{ resumen: object | null | undefined, compact?: boolean, loading?: boolean }} props
 */
export function MapTerritorioResumenPanel({ resumen, compact = false, loading = false }) {
  if (!resumen && !loading) return null

  if (loading && !resumen) {
    return (
      <div
        className={`landing-map-territorio-resumen${compact ? ' is-compact' : ''} muted small`}
        role="status"
      >
        Calculando superficie del territorio…
      </div>
    )
  }

  if (!resumen) return null

  const nivelLabel = resumen.nivel === 'barrio' ? 'Barrio' : 'Comuna'
  const ratio =
    resumen.ratio_vs_ciudad != null && Number.isFinite(Number(resumen.ratio_vs_ciudad))
      ? Number(resumen.ratio_vs_ciudad)
      : null

  return (
    <section
      className={`landing-map-territorio-resumen${compact ? ' is-compact' : ''}`}
      aria-labelledby={compact ? 'map-territorio-resumen-sidebar' : 'map-territorio-resumen-title'}
    >
      <h3
        id={compact ? 'map-territorio-resumen-sidebar' : 'map-territorio-resumen-title'}
        className="landing-map-territorio-resumen-title"
      >
        {compact ? 'Territorio seleccionado' : `Resumen — ${nivelLabel}`}
      </h3>
      <p className="landing-map-territorio-resumen-nombre">
        <strong>{resumen.nombre}</strong>
        {resumen.codigo ? <span className="muted"> · {resumen.codigo}</span> : null}
      </p>

      <div className="landing-map-area-analisis-kpis">
        <div className="landing-map-area-kpi">
          <span className="landing-map-area-kpi-label">Superficie</span>
          <strong>{fmtNum(resumen.area_km2, 3)} km²</strong>
        </div>
        <div className="landing-map-area-kpi">
          <span className="landing-map-area-kpi-label">Incidentes</span>
          <strong>{fmtNum(resumen.incidentes)}</strong>
        </div>
        <div className="landing-map-area-kpi">
          <span className="landing-map-area-kpi-label">Densidad</span>
          <strong>{fmtNum(resumen.densidad_km2, 2)} / km²</strong>
        </div>
        {ratio != null && (
          <div className="landing-map-area-kpi">
            <span
              className="landing-map-area-kpi-label"
              title={RATIO_VS_CIUDAD_HELP}
            >
              Ratio vs ciudad (G02)
            </span>
            <strong>{fmtNum(ratio, 2)}×</strong>
          </div>
        )}
      </div>

      {!compact && ratio != null && (
        <p className="muted small landing-map-ratio-help">{RATIO_VS_CIUDAD_HELP}</p>
      )}

      {!compact && resumen.nota && (
        <p className="muted small landing-map-territorio-resumen-note">{resumen.nota}</p>
      )}
    </section>
  )
}
