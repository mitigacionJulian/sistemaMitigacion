import { useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ReportePreviewContent } from '../components/reportes/ReportePreviewContent.jsx'

function usaMargenesPaginaImpresion() {
  return /Chrome|Edg\//.test(navigator.userAgent)
}

export function ReportePreview() {
  const location = useLocation()
  const navigate = useNavigate()
  const reporte = location.state?.reporte

  useEffect(() => {
    if (!reporte) return undefined

    const activarMargenes = () => {
      if (usaMargenesPaginaImpresion()) {
        document.documentElement.classList.add('reporte-print-margin-boxes')
      }
    }
    const desactivarMargenes = () => {
      document.documentElement.classList.remove('reporte-print-margin-boxes')
    }

    window.addEventListener('beforeprint', activarMargenes)
    window.addEventListener('afterprint', desactivarMargenes)
    return () => {
      window.removeEventListener('beforeprint', activarMargenes)
      window.removeEventListener('afterprint', desactivarMargenes)
      desactivarMargenes()
    }
  }, [reporte])

  const handlePrint = () => {
    if (usaMargenesPaginaImpresion()) {
      document.documentElement.classList.add('reporte-print-margin-boxes')
    }
    const limpiar = () => document.documentElement.classList.remove('reporte-print-margin-boxes')
    window.addEventListener('afterprint', limpiar, { once: true })
    // Un frame para que el navegador aplique la clase antes del diálogo de impresión.
    requestAnimationFrame(() => {
      window.print()
    })
  }

  if (!reporte) {
    return (
      <div className="reporte-preview-page">
        <section className="panel">
          <h1>Vista previa del reporte</h1>
          <p className="muted">
            No hay un reporte en memoria. Genere uno desde el tablero, mapa, predicciones, asistente o pruebas (admin) con el botón{' '}
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
