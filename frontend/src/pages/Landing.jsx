import { Link } from 'react-router-dom'
import { LandingIncidentMap } from '../components/LandingIncidentMap.jsx'

export function Landing() {
  return (
    <>
      <section className="hero">
        <div className="hero-inner">
          <p className="eyebrow">Medellín · Análisis de accidentalidad</p>
          <h1>Prioriza vías y puntos críticos con información clara</h1>
          <p className="lead">
            Explora un tablero de indicadores alineados con el modelo de datos del proyecto: KPIs, tendencias
            temporales, distribución geográfica y priorización para control vial. En la base cargada, el mapa de
            inicio muestra una <strong>muestra</strong> de incidentes con coordenadas para visualizar concentraciones.
          </p>
          <div className="hero-actions">
            <Link to="/tablero" className="btn btn-primary">
              Ver tablero
            </Link>
            <Link to="/registro" className="btn btn-secondary">
              Crear cuenta
            </Link>
          </div>
          <ul className="feature-list">
            <li>Mapa en inicio y tablero con filtros por periodo y territorio</li>
            <li>Series temporales y patrones por día y hora</li>
            <li>Perfiles de usuario enlazados a roles (ciudadano, autoridad, analista…)</li>
          </ul>
        </div>
      </section>

      <section className="landing-map-block panel" aria-labelledby="landing-map-title">
        <h2 id="landing-map-title">Concentración geográfica</h2>
        <p className="muted small">
          Cada registro corresponde a coordenadas en base (no geocodificación por dirección en tiempo real). El
          periodo y los filtros de comuna, barrio y clase son los mismos que en el tablero (
          <strong>catalogos</strong>, <strong>barrios</strong>, <strong>incidentes-mapa</strong>). La vista combina{' '}
          <strong>calor</strong> (densidad aparente) y <strong>clusters</strong> al acercar zoom; es exploratoria, no
          un modelo de kernel ni inferencia causal.
        </p>
        <LandingIncidentMap />
      </section>
    </>
  )
}