import { Link, NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

const navClass = ({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')

export function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/" className="brand">
          SG Mitigación — Medellín
        </Link>
        <nav className="nav">
          <NavLink to="/" end className={navClass}>
            Inicio
          </NavLink>
          <NavLink to="/tablero" className={navClass}>
            Tablero
          </NavLink>
          <NavLink to="/predicciones" className={navClass}>
            Predicciones
          </NavLink>
          {!user && (
            <>
              <NavLink to="/login" className={navClass}>
                Ingresar
              </NavLink>
              <NavLink to="/registro" className={navClass}>
                Registro
              </NavLink>
            </>
          )}
          {user && (
            <span className="nav-user">
              <span className="nav-user-name">{user.username}</span>
              <span className="badge-rol">{user.perfil.rol_nombre}</span>
              <button type="button" className="btn btn-ghost" onClick={() => void logout()}>
                Salir
              </button>
            </span>
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
