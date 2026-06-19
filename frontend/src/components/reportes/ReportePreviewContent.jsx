import { ReporteLayout } from './ReporteLayout.jsx'
import { ReporteAsistente } from './ReporteAsistente.jsx'
import { ReporteMapa } from './ReporteMapa.jsx'
import { ReportePredicciones } from './ReportePredicciones.jsx'
import { ReporteTablero } from './ReporteTablero.jsx'

export function ReportePreviewContent({ reporte }) {
  if (!reporte?.meta) {
    return <p className="muted">No hay datos de reporte para mostrar.</p>
  }

  const { meta, cuerpo } = reporte

  return (
    <ReporteLayout meta={meta}>
      {cuerpo?.tipo === 'tablero' ? (
        <ReporteTablero cuerpo={cuerpo} />
      ) : cuerpo?.tipo === 'mapa' ? (
        <ReporteMapa cuerpo={cuerpo} />
      ) : cuerpo?.tipo === 'predicciones' ? (
        <ReportePredicciones cuerpo={cuerpo} />
      ) : cuerpo?.tipo === 'asistente' ? (
        <ReporteAsistente cuerpo={cuerpo} />
      ) : cuerpo?.tipo === 'placeholder' ? (
        <section className="reporte-placeholder panel">
          <p>{cuerpo.mensaje}</p>
          <p className="muted small">
            Sección solicitada: <strong>{cuerpo.seccion_solicitada}</strong>.
          </p>
        </section>
      ) : (
        <section className="reporte-placeholder panel">
          <p className="muted">Contenido del reporte no disponible.</p>
        </section>
      )}
    </ReporteLayout>
  )
}