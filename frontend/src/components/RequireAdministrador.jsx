import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export function RequireAdministrador({ children }) {
  const { user, loading, isAdministrador } = useAuth()
  const location = useLocation()

  if (loading) {
    return <p className="muted auth-loading">Verificando sesión…</p>
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (!isAdministrador) {
    return (
      <div className="auth-card auth-card-wide">
        <h1>Acceso restringido</h1>
        <p className="muted">
          La gestión de usuarios está disponible solo para el rol{' '}
          <strong>administrador</strong>. Su rol actual es{' '}
          <strong>{user.perfil?.rol_nombre ?? 'sin rol'}</strong>.
        </p>
        <p>
          <a href="/tablero" className="btn btn-primary">
            Ir al tablero
          </a>
        </p>
      </div>
    )
  }

  return children
}
