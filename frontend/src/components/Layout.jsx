import { useCallback, useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

const navClass = ({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')

export function Layout() {
  const { user, logout, isAnalista } = useAuth()
  const location = useLocation()
  const [navOpen, setNavOpen] = useState(false)

  const closeNav = useCallback(() => setNavOpen(false), [])

  useEffect(() => {
    closeNav()
  }, [location.pathname, closeNav])

  useEffect(() => {
    if (!navOpen) return undefined
    const onKeyDown = (e) => {
      if (e.key === 'Escape') closeNav()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [navOpen, closeNav])

  const handleLogout = () => {
    closeNav()
    void logout()
  }

  return (
    <div className={`app-shell${navOpen ? ' is-nav-open' : ''}`}>
      <header className={`topbar${navOpen ? ' is-nav-open' : ''}`}>
        <Link to="/" className="brand" onClick={closeNav}>
          <span className="brand-full">SG Mitigación — Medellín</span>
          <span className="brand-short">SG Medellín</span>
        </Link>
        <button
          type="button"
          className="nav-toggle"
          aria-expanded={navOpen}
          aria-controls="main-nav"
          aria-label={navOpen ? 'Cerrar menú' : 'Abrir menú'}
          onClick={() => setNavOpen((open) => !open)}
        >
          <span className="nav-toggle-bar" aria-hidden="true" />
          <span className="nav-toggle-bar" aria-hidden="true" />
          <span className="nav-toggle-bar" aria-hidden="true" />
        </button>
        <nav id="main-nav" className="nav" aria-label="Principal">
          <NavLink to="/" end className={navClass} onClick={closeNav}>
            Inicio
          </NavLink>
          <NavLink to="/tablero" className={navClass} onClick={closeNav}>
            Tablero
          </NavLink>
          <NavLink to="/mapa" className={navClass} onClick={closeNav}>
            Mapa
          </NavLink>
          <NavLink to="/agente" className={navClass} onClick={closeNav}>
            Asistente
          </NavLink>
          {(!user || isAnalista) && (
            <NavLink to="/predicciones" className={navClass} onClick={closeNav}>
              Predicciones
            </NavLink>
          )}
          {!user && (
            <>
              <NavLink to="/login" className={navClass} onClick={closeNav}>
                Ingresar
              </NavLink>
              <NavLink to="/registro" className={navClass} onClick={closeNav}>
                Registro
              </NavLink>
            </>
          )}
          {user && (
            <div className="nav-user">
              <span className="nav-user-name">{user.username}</span>
              <span className="badge-rol">{user.perfil.rol_nombre}</span>
              <button type="button" className="btn btn-ghost nav-logout" onClick={handleLogout}>
                Salir
              </button>
            </div>
          )}
        </nav>
      </header>
      <main className="main">
        <Outlet />
      </main>
      <footer className="footer">
        <p>
          Proyecto académico — datos del tablero en modo demostración hasta integrar fuentes
          oficiales.
        </p>
      </footer>
    </div>
  )
}
