import { formatReporteFecha } from './reporteFormat.js'

function ConsultaBlock({ item }) {
  return (
    <article className="reporte-asistente-consulta">
      <header className="reporte-asistente-consulta-header">
        <h3 className="reporte-subtitle">Consulta {item.numero}</h3>
        <p className="muted small">{formatReporteFecha(item.fecha)}</p>
      </header>
      <div className="reporte-asistente-bloque">
        <p className="reporte-asistente-rol">Pregunta</p>
        <p className="reporte-asistente-texto">{item.pregunta}</p>
      </div>
      <div className="reporte-asistente-bloque">
        <p className="reporte-asistente-rol">Respuesta</p>
        <p className="reporte-asistente-texto reporte-asistente-respuesta">{item.respuesta}</p>
      </div>
      {(item.modelo || item.from_cache) && (
        <p className="muted small reporte-asistente-meta">
          {item.modelo ? <>Modelo: {item.modelo}</> : null}
          {item.modelo && item.from_cache ? ' · ' : null}
          {item.from_cache ? 'Origen: caché' : null}
        </p>
      )}
    </article>
  )
}

export function ReporteAsistente({ cuerpo }) {
  const conversacion = cuerpo?.conversacion || []

  return (
    <div className="reporte-asistente">
      <section className="reporte-section">
        <h2 className="reporte-section-title">Resumen</h2>
        <p className="reporte-section-hint">
          Total de consultas incluidas: <strong>{cuerpo?.total_consultas ?? conversacion.length}</strong>
        </p>
        {cuerpo?.interpretacion ? (
          <p className="reporte-section-hint">{cuerpo.interpretacion}</p>
        ) : null}
      </section>

      {conversacion.length === 0 ? (
        <section className="reporte-section">
          <p className="muted">No hay consultas para mostrar.</p>
        </section>
      ) : (
        conversacion.map((item) => <ConsultaBlock key={`${item.numero}-${item.fecha}`} item={item} />)
      )}

      {cuerpo?.limitaciones ? (
        <section className="reporte-section">
          <p className="muted small reporte-note">{cuerpo.limitaciones}</p>
        </section>
      ) : null}
    </div>
  )
}
