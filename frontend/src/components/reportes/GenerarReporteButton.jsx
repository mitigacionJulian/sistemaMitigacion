import { useState } from 'react'
import { useAuth } from '../../context/AuthContext.jsx'
import { ReporteModal } from './ReporteModal.jsx'

export function GenerarReporteButton({
  seccion,
  seccionEtiqueta,
  filtros = {},
  query = {},
  captureMapSnapshot,
  mapaLeyenda = null,
  className = 'btn btn-secondary',
  label = 'Generar reporte',
  disabled = false,
  visibleForAll = false,
  customFetch,
}) {
  const { user, isAnalista } = useAuth()
  const [open, setOpen] = useState(false)

  if (!visibleForAll && (!user || !isAnalista)) return null

  return (
    <>
      <button
        type="button"
        className={className}
        onClick={() => setOpen(true)}
        disabled={disabled}
      >
        {label}
      </button>
      <ReporteModal
        open={open}
        onClose={() => setOpen(false)}
        seccion={seccion}
        seccionEtiqueta={seccionEtiqueta}
        filtros={filtros}
        query={query}
        captureMapSnapshot={captureMapSnapshot}
        mapaLeyenda={mapaLeyenda}
        customFetch={customFetch}
      />
    </>
  )
}
