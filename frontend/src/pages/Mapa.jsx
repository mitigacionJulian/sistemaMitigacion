import { Link } from 'react-router-dom'
import { LandingIncidentMap } from '../components/LandingIncidentMap.jsx'

export function Mapa() {
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
        </div>
      </header>

      <LandingIncidentMap variant="page" />
    </section>
  )
}
