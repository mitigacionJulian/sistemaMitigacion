import { useCallback, useState } from 'react'

import { Link } from 'react-router-dom'

import { LandingIncidentMap } from '../components/LandingIncidentMap.jsx'

import { GenerarReporteButton } from '../components/reportes/GenerarReporteButton.jsx'

import { captureMapElement, waitForMapPaint } from '../map/mapCapture.js'



export function Mapa() {

  const [reporteCtx, setReporteCtx] = useState({ filtros: {}, query: {}, mapaLeyenda: null })
  const [forceCellIdsForCapture, setForceCellIdsForCapture] = useState(false)

  const captureMapSnapshot = useCallback(async () => {
    setForceCellIdsForCapture(true)
    await waitForMapPaint()
    await new Promise((resolve) => setTimeout(resolve, 180))
    try {
      return await captureMapElement('#map-page-shell')
    } finally {
      setForceCellIdsForCapture(false)
    }
  }, [])



  return (

    <section className="map-page">

      <header className="map-page-header panel">

        <p className="eyebrow">Exploración geoespacial</p>

        <h1>Mapa de accidentalidad</h1>

        <p className="muted small map-page-lead">

          Territorio (G01), detalle de incidentes, hotspots (P14), calidad territorial (G03) y rankings (G02, G06).

          Al entrar se precargan en caché mapa e indicadores (barra de progreso). Cambiar modo de vista o métrica

          suele ser instantáneo; si cambia fechas o territorio, pulse «Aplicar filtros» (usa caché si ya cargó esa

          combinación).

        </p>

        <div className="map-page-header-actions">

          <Link to="/tablero" className="btn btn-secondary">

            Ir al tablero

          </Link>

          <GenerarReporteButton

            seccion="mapa"

            seccionEtiqueta="Mapa de accidentalidad"

            filtros={reporteCtx.filtros}

            query={reporteCtx.query}

            captureMapSnapshot={captureMapSnapshot}

            mapaLeyenda={reporteCtx.mapaLeyenda}

          />

        </div>

      </header>



      <LandingIncidentMap
        variant="page"
        onReportContextChange={setReporteCtx}
        forceShowHotspotCellIds={forceCellIdsForCapture}
      />

    </section>

  )

}

