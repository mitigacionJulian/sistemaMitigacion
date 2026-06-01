import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [pending, setPending] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError(null)
    setPending(true)
    try {
      const u = await login(username, password)
      if (from) {
        navigate(from, { replace: true })
      } else if (u?.perfil?.rol_codigo === 'analista') {
        navigate('/predicciones', { replace: true })
      } else {
        navigate('/tablero', { replace: true })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="auth-card">
      <h1>Iniciar sesión</h1>
      <form onSubmit={onSubmit} className="form">
        {error && <p className="form-error">{error}</p>}
        <label>
          Usuario
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label>
          Contraseña
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        <button type="submit" className="btn btn-primary btn-block" disabled={pending}>
          {pending ? 'Ingresando…' : 'Ingresar'}
        </button>
      </form>
      <p className="auth-links muted small">
        <Link to="/recuperar-clave">¿Olvidó su contraseña?</Link>
        {' · '}
        <Link to="/registro">Crear cuenta</Link>
      </p>
    </div>
  )
}
