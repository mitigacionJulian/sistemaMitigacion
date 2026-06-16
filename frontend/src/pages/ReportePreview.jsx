import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ReportePreviewContent } from '../components/reportes/ReportePreviewContent.jsx'

export function ReportePreview() {
  const location = useLocation()
  const navigate = useNavigate()
  const reporte = location.state?.reporte

  const handlePrint = () => {
    window.print()
  }

  if (!reporte) {
    return (
      <div className="reporte-preview-page">
        <section className="panel">
          <h1>Vista previa del reporte</h1>
          <p className="muted">
            No hay un reporte en memoria. Genere uno desde el tablero u otra sección con el botón{' '}
            <strong>Generar reporte</strong>.
          </p>
          <p>
            <Link to="/tablero" className="btn btn-primary">
              Ir al tablero
            </Link>
          </p>
        </section>
      </div>
    )
  }

  return (
    <div className="reporte-preview-page">
      <div className="reporte-toolbar no-print">
        <button type="button" className="btn btn-ghost" onClick={() => navigate(-1)}>
          Volver
        </button>
        <div className="reporte-toolbar-actions">
          <button type="button" className="btn btn-secondary" onClick={handlePrint}>
            Imprimir / Guardar PDF
          </button>
        </div>
      </div>
      <ReportePreviewContent reporte={reporte} />
    </div>
  )
}
