import { useEffect } from 'react'
import { createPortal } from 'react-dom'

/**
 * Capa de impresión en document.body para que position:fixed se repita en cada hoja del PDF.
 * Dentro de .reporte-document el pie solo aparecía al final del flujo impreso.
 */
export function ReportePrintLayer({ tituloDisplay }) {
  useEffect(() => {
    document.body.classList.add('reporte-print-layer-active')
    return () => document.body.classList.remove('reporte-print-layer-active')
  }, [])

  if (!tituloDisplay) return null

  return createPortal(
    <>
      <div className="reporte-print-watermark" aria-hidden="true">
        CONFIDENCIAL
      </div>
      <footer className="reporte-running-footer" aria-hidden="true">
        <span className="reporte-running-footer-title">{tituloDisplay}</span>
        <span className="reporte-running-footer-page" />
      </footer>
    </>,
    document.body,
  )
}
