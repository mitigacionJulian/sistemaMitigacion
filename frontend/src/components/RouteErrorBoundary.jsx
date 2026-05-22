import { Component } from 'react'
import { Link } from 'react-router-dom'

export class RouteErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('Error en la vista:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <section className="panel" style={{ marginTop: '1rem' }}>
          <h2>No se pudo mostrar esta página</h2>
          <p className="form-error" role="alert">
            {this.state.error?.message || String(this.state.error)}
          </p>
          <p className="muted small">
            Abra la consola del navegador (F12) para más detalle. Puede volver al{' '}
            <Link to="/tablero">Tablero</Link> o recargar la página.
          </p>
          <button
            type="button"
            className="btn btn-primary"
            style={{ marginTop: '0.75rem' }}
            onClick={() => this.setState({ error: null })}
          >
            Reintentar
          </button>
        </section>
      )
    }
    return this.props.children
  }
}
