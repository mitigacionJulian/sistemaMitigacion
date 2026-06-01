import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export function RequireAnalista({ children }) {
  const { user, loading, isAnalista } = useAuth()
  const location = useLocation()

  if (loading) {
    return <p className="muted auth-loading">Verificando sesión…</p>
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (!isAnalista) {
    return (
      <div className="auth-card auth-card-wide">
        <h1>Acceso restringido</h1>
        <p className="muted">
          La sección <strong>Predicciones</strong> está disponible solo para usuarios con rol{' '}
          <strong>analista</strong>. Su rol actual es{' '}
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
