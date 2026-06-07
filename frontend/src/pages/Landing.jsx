import { Link } from 'react-router-dom'
import heroMedellinImg from '../assets/hero-medellin-trafico.png'

export function Landing() {
  return (
    <section className="hero">
      <div className="hero-grid">
        <div className="hero-inner">
          <p className="eyebrow">Medellín · Análisis de accidentalidad</p>
          <h1>Prioriza vías y puntos críticos con información clara</h1>
          <p className="lead">
            Explora un tablero de indicadores alineados con el modelo de datos del proyecto: KPIs, tendencias
            temporales, distribución geográfica y priorización para control vial. El mapa geoespacial con hotspots,
            densidad y calidad territorial está en una sección dedicada para una carga más ordenada.
          </p>
          <div className="hero-actions">
            <Link to="/tablero" className="btn btn-primary">
              Ver tablero
            </Link>
            <Link to="/mapa" className="btn btn-secondary">
              Ver mapa
            </Link>
            <Link to="/registro" className="btn btn-secondary">
              Crear cuenta
            </Link>
          </div>
          <ul className="feature-list">
            <li>Mapa con filtros por periodo, comuna, barrio y clase de incidente</li>
            <li>Tablero con series temporales y patrones por día y hora</li>
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
  )
}
