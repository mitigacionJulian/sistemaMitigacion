import { useEffect, useRef, useState } from 'react'
import { fetchDashboardCalidadTerritorio } from '../api/client.js'
import { useInView } from '../hooks/useInView.js'

function queryId(v) {
  if (v === '' || v === undefined || v === null) return undefined
  const n = Number(v)
  return Number.isFinite(n) ? n : undefined
}

function fmtPct(v) {
  if (v == null || Number.isNaN(Number(v))) return '—'
  return `${Number(v).toLocaleString('es-CO', { maximumFractionDigits: 1 })} %`
}

function fmtInt(v) {
  if (v == null) return '—'
  return Number(v).toLocaleString('es-CO')
}

/**
 * Panel G03 — discrepancia territorio Mede vs polígono PostGIS.
 * Usa el mismo periodo (y filtros opcionales) que el mapa de inicio.
 */
export function LandingCalidadTerritorio({
  desde,
  hasta,
  comunaId,
  barrioId,
  claseId,
  modoTerritorio,
  enabled,
}) {
  const sectionRef = useRef(null)
  const inView = useInView(sectionRef)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)

  useEffect(() => {
    if (!enabled || !inView || !desde || !hasta) return

    let alive = true
    const t = window.setTimeout(async () => {
      setLoading(true)
      setErr(null)
      try {
        const comunaQ = queryId(comunaId)
        const barrioQ = queryId(barrioId)
        const claseQ = queryId(claseId)
        const payload = await fetchDashboardCalidadTerritorio({
          desde,
          hasta,
          limite_ejemplos: 5,
          ...(comunaQ !== undefined ? { comuna_id: comunaQ } : {}),
          ...(barrioQ !== undefined ? { barrio_id: barrioQ } : {}),
          ...(claseQ !== undefined ? { clase_incidente_id: claseQ } : {}),
          ...(modoTerritorio === 'espacial' ? { territorio: 'espacial' } : {}),
        })
        if (alive) setData(payload)
      } catch (e) {
        if (alive) {
          setErr(e instanceof Error ? e.message : 'No se pudo cargar calidad territorial')
          setData(null)
        }
      } finally {
        if (alive) setLoading(false)
      }
    }, 500)

    return () => {
      alive = false
      window.clearTimeout(t)
    }
  }, [desde, hasta, comunaId, barrioId, claseId, modoTerritorio, enabled, inView])

  const meta = data?.meta
  const ejemplos = data?.ejemplos_discrepancia ?? []

  return (
    <section ref={sectionRef} className="landing-g03 panel" aria-labelledby="landing-g03-title">
      <h3 id="landing-g03-title">Calidad geográfica del territorio (G03)</h3>
      <p className="muted small landing-g03-lead">
        Compara el <strong>comuna/barrio del registro Mede</strong> con el que cae el punto dentro de los{' '}
        <strong>polígonos oficiales</strong> (PostGIS). Una discrepancia no implica error de coordenadas: muchas veces
        el texto del CSV no coincide con el límite cartográfico.
      </p>

      {loading && !meta && (
        <p className="muted small" role="status">
          Calculando calidad territorial…
        </p>
      )}
      {err && <p className="form-error">{err}</p>}

      {meta && (
        <>
          <p className="muted small landing-g03-period">
            Periodo: <strong>{meta.fecha_inicio}</strong> → <strong>{meta.fecha_fin}</strong>
            {loading ? ' · actualizando…' : null}
          </p>

          <div className="landing-g03-stats" role="list">
            <div className="landing-g03-stat" role="listitem">
              <span className="landing-g03-stat-label">Con coordenada</span>
              <span className="landing-g03-stat-value">{fmtInt(meta.con_ubicacion)}</span>
            </div>
            <div className="landing-g03-stat" role="listitem">
              <span className="landing-g03-stat-label">Match comuna (polígono)</span>
              <span className="landing-g03-stat-value">{fmtPct(meta.pct_match_comuna)}</span>
              <span className="muted small">{fmtInt(meta.match_comuna_espacial)} incidentes</span>
            </div>
            <div className="landing-g03-stat" role="listitem">
              <span className="landing-g03-stat-label">Match barrio (polígono)</span>
              <span className="landing-g03-stat-value">{fmtPct(meta.pct_match_barrio)}</span>
              <span className="muted small">{fmtInt(meta.match_barrio_espacial)} incidentes</span>
            </div>
            <div className="landing-g03-stat landing-g03-stat-warn" role="listitem">
              <span className="landing-g03-stat-label">Discrepancia registro ≠ mapa</span>
              <span className="landing-g03-stat-value">{fmtPct(meta.pct_discrepancia_cualquiera)}</span>
              <span className="muted small">{fmtInt(meta.discrepancia_cualquiera)} incidentes</span>
            </div>
          </div>

          <details className="landing-g03-details">
            <summary>Ejemplos de discrepancia ({ejemplos.length})</summary>
            {ejemplos.length === 0 ? (
              <p className="muted small">Sin ejemplos en este periodo con los filtros actuales.</p>
            ) : (
              <div className="cmp-table-wrap">
                <table className="table cmp-table landing-g03-table">
                  <thead>
                    <tr>
                      <th>Radicado</th>
                      <th>Fecha</th>
                      <th>Comuna (Mede → polígono)</th>
                      <th>Barrio (Mede → polígono)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ejemplos.map((row) => (
                      <tr key={row.radicado}>
                        <td>{row.radicado}</td>
                        <td>{row.fecha_incidente ?? '—'}</td>
                        <td>
                          {row.comuna_registro ?? '—'} → {row.comuna_espacial ?? '—'}
                        </td>
                        <td>
                          {row.barrio_registro ?? '—'} → {row.barrio_espacial ?? '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </details>
        </>
      )}
    </section>
  )
}
