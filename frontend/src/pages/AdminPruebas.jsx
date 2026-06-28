import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchAdminPruebasEstado, fetchAdminPruebasReporte, iniciarAdminPruebas } from '../api/client.js'
import { GenerarReporteButton } from '../components/reportes/GenerarReporteButton.jsx'

function formatFecha(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('es-CO', {
      dateStyle: 'short',
      timeStyle: 'short',
    })
  } catch {
    return iso
  }
}

function formatDuracion(ms) {
  if (ms == null || ms <= 0) return '—'
  if (ms < 1000) return `${ms} ms`
  const s = Math.round(ms / 1000)
  if (s < 60) return `${s} s`
  const m = Math.floor(s / 60)
  const rest = s % 60
  return `${m} min ${rest} s`
}

function estadoEtiqueta(estado, ejecutando) {
  if (ejecutando || estado === 'running') return 'En ejecución'
  if (estado === 'done') return 'Completada'
  if (estado === 'error') return 'Finalizada con fallos'
  return 'Sin ejecución reciente'
}

function estadoClass(estado, ejecutando) {
  if (ejecutando || estado === 'running') return 'admin-pruebas-estado--running'
  if (estado === 'done') return 'admin-pruebas-estado--ok'
  if (estado === 'error') return 'admin-pruebas-estado--error'
  return 'admin-pruebas-estado--idle'
}

function estadoCasoLabel(estado) {
  const map = {
    passed: 'Pasó',
    failed: 'Falló',
    broken: 'Roto',
    skipped: 'Omitido',
  }
  return map[estado] || estado
}

function estadoCasoClass(estado) {
  if (estado === 'passed') return 'admin-pruebas-caso--ok'
  if (estado === 'failed' || estado === 'broken') return 'admin-pruebas-caso--bad'
  if (estado === 'skipped') return 'admin-pruebas-caso--skip'
  return ''
}

export function AdminPruebas() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [mensaje, setMensaje] = useState(null)
  const [pending, setPending] = useState(false)
  const [filtroEstado, setFiltroEstado] = useState('')
  const pollRef = useRef(null)

  const cargar = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    setError(null)
    try {
      const payload = await fetchAdminPruebasEstado()
      setData(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cargar el estado de pruebas')
    } finally {
      if (!silent) setLoading(false)
    }
  }, [])

  useEffect(() => {
    void cargar()
  }, [cargar])

  const ejecutando = Boolean(data?.ejecutando)

  useEffect(() => {
    if (!ejecutando) {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
      return undefined
    }
    pollRef.current = setInterval(() => {
      void cargar(true)
    }, 2500)
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [ejecutando, cargar])

  const resumen = data?.resumen
  const kpis = useMemo(
    () => [
      { label: 'Total', value: resumen?.total ?? 0 },
      { label: 'Pasaron', value: resumen?.pasaron ?? 0, tone: 'ok' },
      { label: 'Fallaron', value: resumen?.fallaron ?? 0, tone: 'bad' },
      { label: 'Rotos', value: resumen?.rotos ?? 0, tone: 'warn' },
      { label: 'Omitidos', value: resumen?.omitidos ?? 0 },
    ],
    [resumen],
  )

  const casosFiltrados = useMemo(() => {
    const casos = resumen?.casos ?? []
    if (!filtroEstado) return casos
    return casos.filter((c) => c.estado === filtroEstado)
  }, [resumen?.casos, filtroEstado])

  const onEjecutar = async () => {
    const ok = window.confirm(
      '¿Ejecutar toda la suite pytest? Los resultados se guardarán localmente y se mostrarán aquí. Puede tardar varios minutos.',
    )
    if (!ok) return
    setPending(true)
    setMensaje(null)
    setError(null)
    try {
      const payload = await iniciarAdminPruebas()
      setData(payload)
      setMensaje(payload.mensaje_inicio || 'Ejecución iniciada.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo iniciar la ejecución')
      await cargar(true)
    } finally {
      setPending(false)
    }
  }

  return (
    <section className="admin-usuarios-page admin-pruebas-page">
      <header className="admin-usuarios-header admin-pruebas-header">
        <div>
          <p className="eyebrow">Administración</p>
          <h1>Pruebas del sistema</h1>
          <p className="muted small">
            Ejecute la suite pytest del backend y revise los resultados organizados por módulo y caso.
            Puede exportar un reporte imprimible como en el tablero, mapa y predicciones.
          </p>
        </div>
        <div className="admin-pruebas-header-actions">
          <Link to="/admin/usuarios" className="btn btn-secondary">
            Usuarios
          </Link>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => void cargar()}
            disabled={loading || pending}
          >
            Actualizar
          </button>
        </div>
      </header>

      {error && (
        <p className="admin-usuarios-alert" role="alert">
          {error}
        </p>
      )}
      {mensaje && <p className="admin-usuarios-success">{mensaje}</p>}

      {loading && !data ? (
        <p className="muted">Cargando estado de pruebas…</p>
      ) : (
        <>
          <div className="panel admin-pruebas-panel">
            <div className="admin-pruebas-panel-head">
              <h2>Estado de ejecución</h2>
              <span className={`admin-pruebas-estado ${estadoClass(data?.estado, ejecutando)}`}>
                {estadoEtiqueta(data?.estado, ejecutando)}
              </span>
            </div>
            <dl className="admin-usuarios-meta admin-pruebas-meta">
              <div>
                <dt>Ejecución desde UI</dt>
                <dd>{data?.puede_ejecutar ? 'Habilitada (desarrollo)' : 'Deshabilitada en este servidor'}</dd>
              </div>
              <div>
                <dt>Última ejecución</dt>
                <dd>{formatFecha(data?.finalizado_en || data?.iniciado_en)}</dd>
              </div>
              <div>
                <dt>Iniciada por</dt>
                <dd>{data?.iniciado_por || '—'}</dd>
              </div>
              <div>
                <dt>Código salida pytest</dt>
                <dd>{data?.codigo_salida ?? '—'}</dd>
              </div>
              <div>
                <dt>Resultados guardados</dt>
                <dd>{formatFecha(data?.resumen?.ultima_modificacion)}</dd>
              </div>
            </dl>

            <div className="admin-pruebas-actions">
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => void onEjecutar()}
                disabled={!data?.puede_ejecutar || ejecutando || pending}
              >
                {ejecutando ? 'Ejecutando pruebas…' : 'Ejecutar suite'}
              </button>
              <GenerarReporteButton
                seccion="pruebas"
                seccionEtiqueta="Pruebas del sistema"
                className="btn btn-secondary"
                disabled={!resumen?.hay_resultados || ejecutando || pending}
                customFetch={fetchAdminPruebasReporte}
              />
            </div>

            {!data?.puede_ejecutar && (
              <p className="muted small admin-pruebas-hint">
                Para habilitar la ejecución, use <code>DJANGO_DEBUG=1</code> o{' '}
                <code>ALLOW_ADMIN_TEST_RUNNER=1</code> en el archivo <code>.env</code> y reinicie el backend.
              </p>
            )}
          </div>

          <div className="admin-pruebas-kpis">
            {kpis.map((kpi) => (
              <div key={kpi.label} className={`admin-pruebas-kpi admin-pruebas-kpi--${kpi.tone || 'neutral'}`}>
                <span className="admin-pruebas-kpi-label">{kpi.label}</span>
                <strong className="admin-pruebas-kpi-value">{kpi.value}</strong>
              </div>
            ))}
            <div className="admin-pruebas-kpi admin-pruebas-kpi--neutral">
              <span className="admin-pruebas-kpi-label">Duración total</span>
              <strong className="admin-pruebas-kpi-value">{formatDuracion(resumen?.duracion_ms)}</strong>
            </div>
          </div>

          {resumen?.por_epic?.length > 0 && (
            <div className="panel admin-pruebas-panel">
              <h2>Resumen por módulo</h2>
              <div className="admin-usuarios-table-wrap">
                <table className="admin-usuarios-table admin-pruebas-table">
                  <thead>
                    <tr>
                      <th>Módulo</th>
                      <th>Total</th>
                      <th>Pasaron</th>
                      <th>Fallaron</th>
                      <th>Rotos</th>
                      <th>Omitidos</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resumen.por_epic.map((row) => (
                      <tr key={row.epic}>
                        <td>{row.epic}</td>
                        <td>{row.total}</td>
                        <td>{row.pasaron}</td>
                        <td>{row.fallaron}</td>
                        <td>{row.rotos}</td>
                        <td>{row.omitidos}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {resumen?.fallos?.length > 0 && (
            <div className="panel admin-pruebas-panel">
              <h2>Fallos y errores ({resumen.fallos.length})</h2>
              <div className="admin-usuarios-table-wrap">
                <table className="admin-usuarios-table admin-pruebas-table">
                  <thead>
                    <tr>
                      <th>Prueba</th>
                      <th>Estado</th>
                      <th>Módulo</th>
                      <th>Feature</th>
                      <th>Mensaje</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resumen.fallos.map((row) => (
                      <tr key={`${row.epic}-${row.nombre}`}>
                        <td>{row.nombre}</td>
                        <td>{estadoCasoLabel(row.estado)}</td>
                        <td>{row.epic}</td>
                        <td>{row.feature}</td>
                        <td className="admin-pruebas-msg-cell">{row.mensaje || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {resumen?.casos?.length > 0 && (
            <div className="panel admin-pruebas-panel">
              <div className="admin-pruebas-panel-head">
                <h2>Detalle de casos ({casosFiltrados.length})</h2>
                <label className="filter-field admin-pruebas-filtro-estado">
                  <span className="muted small">Filtrar por estado</span>
                  <select value={filtroEstado} onChange={(e) => setFiltroEstado(e.target.value)}>
                    <option value="">Todos</option>
                    <option value="passed">Pasaron</option>
                    <option value="failed">Fallaron</option>
                    <option value="broken">Rotos</option>
                    <option value="skipped">Omitidos</option>
                  </select>
                </label>
              </div>
              <div className="admin-usuarios-table-wrap">
                <table className="admin-usuarios-table admin-pruebas-table">
                  <thead>
                    <tr>
                      <th>Prueba</th>
                      <th>Estado</th>
                      <th>Módulo</th>
                      <th>Feature</th>
                      <th>Categoría</th>
                      <th>Duración</th>
                    </tr>
                  </thead>
                  <tbody>
                    {casosFiltrados.map((row, i) => (
                      <tr key={`${row.epic}-${row.nombre}-${i}`}>
                        <td>{row.nombre}</td>
                        <td>
                          <span className={`admin-pruebas-caso ${estadoCasoClass(row.estado)}`}>
                            {estadoCasoLabel(row.estado)}
                          </span>
                        </td>
                        <td>{row.epic}</td>
                        <td>{row.feature}</td>
                        <td>{row.categoria}</td>
                        <td>{formatDuracion(row.duracion_ms)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {!resumen?.hay_resultados && !ejecutando && (
            <p className="muted">
              Aún no hay resultados. Pulse <strong>Ejecutar suite</strong> para correr las pruebas y ver el detalle aquí.
            </p>
          )}
        </>
      )}
    </section>
  )
}
