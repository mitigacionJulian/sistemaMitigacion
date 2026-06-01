import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { confirmPasswordReset } from '../api/client.js'

export function ResetPassword() {
  const [search] = useSearchParams()
  const token = search.get('token') || ''
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [error, setError] = useState(null)
  const [pending, setPending] = useState(false)
  const [done, setDone] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    if (!token) {
      setError('Falta el token en el enlace. Solicite recuperación de nuevo.')
      return
    }
    setError(null)
    setPending(true)
    try {
      await confirmPasswordReset({
        token,
        password,
        password_confirm: passwordConfirm,
      })
      setDone(true)
      setTimeout(() => navigate('/login', { replace: true }), 2500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo actualizar la contraseña')
    } finally {
      setPending(false)
    }
  }

  if (done) {
    return (
      <div className="auth-card">
        <h1>Contraseña actualizada</h1>
        <p className="muted">Redirigiendo al inicio de sesión…</p>
        <Link to="/login" className="btn btn-primary btn-block">
          Ingresar ahora
        </Link>
      </div>
    )
  }

  return (
    <div className="auth-card">
      <h1>Nueva contraseña</h1>
      <form onSubmit={onSubmit} className="form">
        {error && <p className="form-error">{error}</p>}
        {!token && (
          <p className="form-error">Enlace incompleto. Use el enlace recibido por WhatsApp.</p>
        )}
        <label>
          Nueva contraseña
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            required
            minLength={8}
          />
        </label>
        <label>
          Confirmar contraseña
          <input
            type="password"
            value={passwordConfirm}
            onChange={(e) => setPasswordConfirm(e.target.value)}
            autoComplete="new-password"
            required
          />
        </label>
        <button type="submit" className="btn btn-primary btn-block" disabled={pending || !token}>
          {pending ? 'Guardando…' : 'Guardar contraseña'}
        </button>
      </form>
      <p className="auth-links muted small">
        <Link to="/recuperar-clave">Solicitar nuevo enlace</Link>
      </p>
    </div>
  )
}
