import {
  filtrosReporteEntries,
  formatFiltroValor,
  labelFiltroReporte,
} from './filtrosReporte.js'
import { formatReporteFecha } from './reporteFormat.js'

export const REPORTE_DISCLAIMER =
  'Informe exploratorio basado en datos históricos depurados (Mede). No establece relaciones causales ni sustituye estudios técnicos oficiales. Las proyecciones, cuando aplique, son estimaciones modeladas y no hechos observados.'

export function ReporteLayout({ meta, children }) {
  const titulo = meta?.titulo || meta?.seccion_etiqueta || 'Reporte'
  const filtros = filtrosReporteEntries(meta?.filtros)

  return (
    <article className="reporte-document">
      <header className="reporte-header">
        <p className="reporte-sistema">{meta?.sistema}</p>
        <h1 className="reporte-titulo">{titulo}</h1>
        <dl className="reporte-meta-grid">
          <div>
            <dt>Usuario</dt>
            <dd>{meta?.usuario}</dd>
          </div>
          <div>
            <dt>Rol</dt>
            <dd>{meta?.rol}</dd>
          </div>
          <div>
            <dt>Generado</dt>
            <dd>{formatReporteFecha(meta?.generado_en)}</dd>
          </div>
          <div>
            <dt>Sección</dt>
            <dd>{meta?.seccion_etiqueta}</dd>
          </div>
        </dl>
        {filtros.length > 0 && (
          <section className="reporte-filtros">
            <h2 className="reporte-filtros-title">Filtros aplicados</h2>
            <dl className="reporte-filtros-grid">
              {filtros.map(([key, value]) => (
                <div key={key}>
                  <dt>{labelFiltroReporte(key)}</dt>
                  <dd>{formatFiltroValor(value)}</dd>
                </div>
              ))}
            </dl>
          </section>
        )}
        {meta?.notas ? (
          <section className="reporte-notas">
            <h2 className="reporte-notas-title">Notas del analista</h2>
            <p>{meta.notas}</p>
          </section>
        ) : null}
      </header>

      <div className="reporte-body">{children}</div>

      <footer className="reporte-footer">
        <p className="reporte-disclaimer">{REPORTE_DISCLAIMER}</p>
        <p className="reporte-footer-meta muted small">
          Documento generado por {meta?.usuario} ({meta?.rol}) — {formatReporteFecha(meta?.generado_en)}
        </p>
      </footer>
    </article>
  )
}
