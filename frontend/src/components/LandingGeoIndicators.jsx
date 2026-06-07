import { useEffect, useRef, useState } from 'react'
import {
  fetchDashboardDensidadTerritorial,
  fetchDashboardHotspotsRanking,
} from '../api/client.js'
import { useInView } from '../hooks/useInView.js'

function queryId(v) {
  if (v === '' || v === undefined || v === null) return undefined
  const n = Number(v)
  return Number.isFinite(n) ? n : undefined
}

function baseParams({ desde, hasta, comunaId, barrioId, claseId, modoTerritorio, tamanoCeldaM }) {
  const comunaQ = queryId(comunaId)
  const barrioQ = queryId(barrioId)
  const claseQ = queryId(claseId)
  return {
    desde,
    hasta,
    tamano_celda_m: Number(tamanoCeldaM) || 300,
    ...(comunaQ !== undefined ? { comuna_id: comunaQ } : {}),
    ...(barrioQ !== undefined ? { barrio_id: barrioQ } : {}),
    ...(claseQ !== undefined ? { clase_incidente_id: claseQ } : {}),
    ...(modoTerritorio === 'espacial' ? { territorio: 'espacial' } : {}),
  }
}

function fmtNum(v, digits = 1) {
  if (v == null || Number.isNaN(Number(v))) return '—'
  return Number(v).toLocaleString('es-CO', { maximumFractionDigits: digits })
}

/**
 * F5 — G01/G02 densidad territorial y G06 ranking celdas (G04 omitido: sin catálogo).
 */
export function LandingGeoIndicators({
  desde,
  hasta,
  comunaId,
  barrioId,
  claseId,
  modoTerritorio,
  tamanoCeldaM,
  enabled,
  onFocusCell,
  controlled = false,
  externalDensidad = null,
  externalRanking = null,
  externalLoading = false,
  externalErr = null,
  nivelDensidad: nivelDensidadProp,
  onNivelDensidadChange,
}) {
  const sectionRef = useRef(null)
  const inView = useInView(sectionRef)
  const [nivelDensidadLocal, setNivelDensidadLocal] = useState('comuna')
  const [densidad, setDensidad] = useState(null)
  const [ranking, setRanking] = useState(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)

  const nivelDensidad = controlled && nivelDensidadProp != null ? nivelDensidadProp : nivelDensidadLocal
  const setNivelDensidad = controlled && onNivelDensidadChange ? onNivelDensidadChange : setNivelDensidadLocal

  const displayDensidad = controlled ? externalDensidad : densidad
  const displayRanking = controlled ? externalRanking : ranking
  const displayLoading = controlled ? externalLoading : loading
  const displayErr = controlled ? externalErr : err

  useEffect(() => {
    if (controlled) return undefined
    if (!enabled || !inView || !desde || !hasta) return

    let alive = true
    const t = window.setTimeout(async () => {
      setLoading(true)
      setErr(null)
      const params = baseParams({
        desde,
        hasta,
        comunaId,
        barrioId,
        claseId,
        modoTerritorio,
        tamanoCeldaM,
      })
      try {
        const [densP, rankP] = await Promise.all([
          fetchDashboardDensidadTerritorial({ ...params, nivel: nivelDensidad, limite: 12 }),
          fetchDashboardHotspotsRanking({ ...params, limite: 10, orden: 'densidad' }),
        ])
        if (!alive) return
        setDensidad(densP)
        setRanking(rankP)
      } catch (e) {
        if (!alive) return
        setErr(e instanceof Error ? e.message : 'No se pudieron cargar indicadores geoespaciales')
        setDensidad(null)
        setRanking(null)
      } finally {
        if (alive) setLoading(false)
      }
    }, 550)

    return () => {
      alive = false
      window.clearTimeout(t)
    }
  }, [
    desde,
    hasta,
    comunaId,
    barrioId,
    claseId,
    modoTerritorio,
    tamanoCeldaM,
    nivelDensidad,
    enabled,
    inView,
    controlled,
  ])

  const densMeta = displayDensidad?.meta
  const rankMeta = displayRanking?.meta

  return (
    <div ref={sectionRef} className="landing-geo-stack">
      {displayLoading && !densMeta && (
        <p className="muted small" role="status">
          Cargando indicadores G01–G02 y G06…
        </p>
      )}
      {displayErr && <p className="form-error">{displayErr}</p>}

      <section className="landing-g03 panel" aria-labelledby="landing-g01-title">
        <h3 id="landing-g01-title">Densidad territorial (G01–G02)</h3>
        <p className="muted small landing-g03-lead">
          Incidentes del periodo divididos entre el área del polígono oficial (km²).{' '}
          <strong>G02</strong> = ratio respecto a la densidad promedio de la ciudad en el mismo periodo.
        </p>
        <label className="filter-field" style={{ maxWidth: '14rem', marginBottom: '0.75rem' }}>
          Nivel
          <select value={nivelDensidad} onChange={(e) => setNivelDensidad(e.target.value)}>
            <option value="comuna">Comuna</option>
            <option value="barrio">Barrio</option>
          </select>
        </label>
        {densMeta && (
          <>
            <p className="muted small landing-g03-period">
              Densidad ciudad: <strong>{fmtNum(densMeta.densidad_ciudad_km2)}</strong> inc./km² ·{' '}
              {densMeta.territorios_devueltos} territorios en ranking
              {displayLoading ? ' · actualizando…' : null}
            </p>
            {(displayDensidad?.ranking ?? []).length === 0 ? (
              <p className="muted small">Sin territorios con incidentes y polígono para estos filtros.</p>
            ) : (
              <div className="cmp-table-wrap">
                <table className="table cmp-table landing-g03-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>{nivelDensidad === 'barrio' ? 'Barrio' : 'Comuna'}</th>
                      <th>Inc.</th>
                      <th>Inc./km²</th>
                      <th>Ratio G02</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayDensidad.ranking.map((row) => (
                      <tr key={row.territorio_id}>
                        <td>{row.rank}</td>
                        <td>
                          {row.nombre}
                          {row.comuna_nombre && (
                            <span className="muted small"> ({row.comuna_nombre})</span>
                          )}
                        </td>
                        <td>{fmtNum(row.incidentes, 0)}</td>
                        <td>{fmtNum(row.densidad_km2)}</td>
                        <td>{fmtNum(row.ratio_vs_ciudad, 2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </section>

      <section className="landing-g03 panel" aria-labelledby="landing-g06-title">
        <h3 id="landing-g06-title">Top celdas calientes (G06)</h3>
        <p className="muted small landing-g03-lead">
          Ranking de la cuadrícula P14 (celda {rankMeta?.tamano_celda_m ?? tamanoCeldaM ?? 300} m) por densidad.
          Pulse el nombre de la comuna para centrar la celda en el mapa (modo Hotspots).
        </p>
        {rankMeta && (
          <>
            {(displayRanking?.ranking ?? []).length === 0 ? (
              <p className="muted small">Sin celdas con incidentes en este periodo.</p>
            ) : (
              <div className="cmp-table-wrap">
                <table className="table cmp-table landing-g03-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Inc.</th>
                      <th>Inc./km²</th>
                      <th>Comuna</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayRanking.ranking.map((row) => (
                      <tr key={row.rank}>
                        <td>{row.rank}</td>
                        <td>{fmtNum(row.conteo, 0)}</td>
                        <td>{fmtNum(row.densidad_por_km2)}</td>
                        <td className="landing-g06-comuna-cell">
                          {row.latitud != null &&
                          row.longitud != null &&
                          onFocusCell &&
                          row.comuna_nombre ? (
                            <button
                              type="button"
                              className="link-button"
                              onClick={() => onFocusCell(row.latitud, row.longitud)}
                              title="Ver celda en mapa (Hotspots)"
                            >
                              {row.comuna_nombre}
                            </button>
                          ) : (
                            <span>{row.comuna_nombre ?? '—'}</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  )
}
