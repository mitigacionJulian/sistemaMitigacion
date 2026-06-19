import { useEffect, useId, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchReporteForSeccion } from '../../api/reportClient.js'
import {
  filtrosReporteEntries,
  formatFiltroValor,
  labelFiltroReporte,
} from './filtrosReporte.js'

export function ReporteModal({
  open,
  onClose,
  seccion,
  seccionEtiqueta,
  filtros = {},
  query = {},
  captureMapSnapshot,
  mapaLeyenda = null,
  customFetch,
}) {
  const titleId = useId()
  const navigate = useNavigate()
  const [titulo, setTitulo] = useState('')
  const [notas, setNotas] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)

  useEffect(() => {
    if (!open) return undefined
    setTitulo('')
    setNotas('')
    setErr(null)
    const onKeyDown = (e) => {
      if (e.key === 'Escape' && !loading) onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open, loading, onClose])

  if (!open) return null

  const filtrosLista = filtrosReporteEntries(filtros)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setErr(null)
    try {
      let mapaImagen = null
      if (seccion === 'mapa' && captureMapSnapshot) {
        mapaImagen = await captureMapSnapshot()
      }

      const reporte = customFetch
        ? await customFetch({ titulo: titulo.trim(), notas: notas.trim(), filtros, query })
        : await fetchReporteForSeccion({
            seccion,
            titulo: titulo.trim(),
            notas: notas.trim(),
            filtros,
            query,
          })

      if (seccion === 'mapa' && reporte.cuerpo?.tipo === 'mapa') {
        if (mapaImagen) {
          reporte.cuerpo.mapa_imagen = mapaImagen
        }
        if (mapaLeyenda) {
          reporte.cuerpo.mapa_leyenda = mapaLeyenda
        }
      }

      onClose()
      navigate('/reporte/vista', { state: { reporte } })
    } catch (error) {
      setErr(error instanceof Error ? error.message : 'Error al generar el reporte')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="reporte-modal-backdrop" role="presentation" onClick={() => !loading && onClose()}>
      <div
        className="reporte-modal panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="reporte-modal-header">
          <h2 id={titleId}>Generar reporte</h2>
          <p className="muted small">
            Sección: <strong>{seccionEtiqueta || seccion}</strong>. Los filtros se toman de la pantalla actual.
            {seccion === 'mapa' && (
              <>
                {' '}
                Se incluirá una captura del mapa visible al generar el informe.
              </>
            )}
          </p>
        </header>

        <form className="reporte-modal-form" onSubmit={(e) => void handleSubmit(e)}>
          <section className="reporte-modal-filtros">
            <h3>Filtros que se incluirán</h3>
            {filtrosLista.length === 0 ? (
              <p className="muted small">Sin filtros adicionales (vista general).</p>
            ) : (
              <dl className="reporte-filtros-grid reporte-filtros-grid-compact">
                {filtrosLista.map(([key, value]) => (
                  <div key={key}>
                    <dt>{labelFiltroReporte(key)}</dt>
                    <dd>{formatFiltroValor(value)}</dd>
                  </div>
                ))}
              </dl>
            )}
          </section>

          <label className="filter-field">
            Título del reporte (opcional)
            <input
              type="text"
              value={titulo}
              onChange={(e) => setTitulo(e.target.value)}
              placeholder={seccionEtiqueta || 'Reporte'}
              maxLength={200}
              disabled={loading}
            />
          </label>

          <label className="filter-field">
            Notas (opcional)
            <textarea
              value={notas}
              onChange={(e) => setNotas(e.target.value)}
              rows={3}
              placeholder="Contexto, alcance o comentarios para el lector del informe…"
              maxLength={2000}
              disabled={loading}
            />
          </label>

          {err && <p className="form-error">{err}</p>}

          <div className="reporte-modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Generando…' : 'Ver vista previa'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
