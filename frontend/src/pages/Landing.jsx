import { Link } from 'react-router-dom'
import heroMedellinImg from '../assets/hero-medellin-trafico.png'
import { LandingIncidentMap } from '../components/LandingIncidentMap.jsx'

export function Landing() {
  return (
    <>
      <section className="hero">
        <div className="hero-grid">
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
            </ul>
          </div>
          <figure className="hero-visual">
            <img
              src={heroMedellinImg}
              alt="Vista aérea de tráfico denso en una vía de Medellín, con buses, taxis y motos"
              width={960}
              height={540}
              loading="eager"
              decoding="async"
            />
            <figcaption className="hero-visual-caption">
              Contexto urbano del análisis: movilidad y accidentalidad en la ciudad.{' '}
              Imagen:{' '}
              <a
                href="https://www.pexels.com/es-es/foto/trafico-de-un-solo-sentido-en-medellin-colombia-sudamerica-33265018/"
                target="_blank"
                rel="noopener noreferrer"
              >
                Pexels — tráfico en Medellín, Colombia
              </a>
              .
            </figcaption>
          </figure>
        </div>
      </section>

      <section className="landing-map-block panel" aria-labelledby="landing-map-title">
        <h2 id="landing-map-title">Concentración geográfica</h2>
        <p className="muted small">
          Mapa por territorio (coroplética G01) con filtros de periodo, comuna, barrio y clase. Modo{' '}
          <strong>Territorio</strong> resume por comuna/barrio; <strong>Detalle</strong> muestra incidentes
          individuales; <strong>Hotspots</strong> (P14) localiza focos en celdas de 300–500 m.
        </p>
        <LandingIncidentMap />
      </section>
    </>
  )
}