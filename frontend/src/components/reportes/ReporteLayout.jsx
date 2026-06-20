import {
  filtrosReporteEntries,
  formatFiltroValor,
  labelFiltroReporte,
} from './filtrosReporte.js'
import { formatReporteFecha } from './reporteFormat.js'
import { ReportePrintLayer } from './ReportePrintLayer.jsx'
import { resolveReporteTitulo } from './reporteTitulo.js'

export const REPORTE_DISCLAIMER =
  'Informe exploratorio basado en datos históricos depurados (Mede). No establece relaciones causales ni sustituye estudios técnicos oficiales. Las proyecciones, cuando aplique, son estimaciones modeladas y no hechos observados.'

const LOGO_MINTRANSPORTE = '/images/reportes/logo-mintransporte.png'
const LOGO_UNIVERSIDAD = '/images/reportes/logo-universidad.png'

export function ReporteLayout({ meta, children }) {
  const { titulo_display } = resolveReporteTitulo(meta)
  const filtros = filtrosReporteEntries(meta?.filtros)

  return (
    <>
      <ReportePrintLayer tituloDisplay={titulo_display} />
      <article className="reporte-document">
        <header className="reporte-header">
        <div className="reporte-logos">
          <img
            src={LOGO_MINTRANSPORTE}
            alt="Ministerio de Transporte — Colombia"
            className="reporte-logo reporte-logo-mintransporte"
          />
          <img
            src={LOGO_UNIVERSIDAD}
            alt="Universidad de San Buenaventura"
            className="reporte-logo reporte-logo-universidad"
          />
        </div>
        <p className="reporte-sistema">{meta?.sistema}</p>
        <h1 className="reporte-titulo">{titulo_display}</h1>
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
          {meta?.numero_reporte ? (
            <div>
              <dt>N.º reporte</dt>
              <dd>{meta.numero_reporte}</dd>
            </div>
          ) : null}
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
            {titulo_display} — Documento generado por {meta?.usuario} ({meta?.rol}) —{' '}
            {formatReporteFecha(meta?.generado_en)}
          </p>
        </footer>
      </article>
    </>
  )
}
