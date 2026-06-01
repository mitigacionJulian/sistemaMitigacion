import { useState } from 'react'
import { Link } from 'react-router-dom'
import { requestPasswordReset } from '../api/client.js'
import { PhoneCoInput } from '../components/PhoneCoInput.jsx'

export function ForgotPassword() {
  const [username, setUsername] = useState('')
  const [telefono, setTelefono] = useState('')
  const [error, setError] = useState(null)
  const [pending, setPending] = useState(false)
  const [result, setResult] = useState(null)

  async function onSubmit(e) {
    e.preventDefault()
    setError(null)
    setPending(true)
    try {
      const body = await requestPasswordReset({ username, telefono })
      setResult(body)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al solicitar recuperación')
    } finally {
      setPending(false)
    }
  }

  if (result) {
    return (
      <div className="auth-card auth-card-wide">
        <h1>Recuperar contraseña</h1>
        <p className="muted small">{result.detail}</p>
        <p className="auth-reset-url-wrap">
          <a href={result.whatsapp_url} className="btn btn-primary btn-block" target="_blank" rel="noopener noreferrer">
            Abrir WhatsApp (+57)
          </a>
        </p>
        <p className="muted small">
          También puede copiar este enlace:
          <br />
          <a href={result.reset_url} className="auth-reset-link">
            {result.reset_url}
          </a>
        </p>
        <p className="auth-links muted small">
          <Link to="/login">Volver a iniciar sesión</Link>
        </p>
      </div>
    )
  }

  return (
    <div className="auth-card auth-card-wide">
      <h1>Recuperar contraseña</h1>
      <p className="muted small">
        Indique su usuario y el celular registrado. Se abrirá WhatsApp con un mensaje que incluye el enlace
        de restablecimiento (prefijo +57 automático).
      </p>
      <form onSubmit={onSubmit} className="form">
        {error && <p className="form-error">{error}</p>}
        <label>
          Usuario
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
        </label>
        <label>
          Celular registrado
          <PhoneCoInput id="forgot-telefono" value={telefono} onChange={setTelefono} />
        </label>
        <button type="submit" className="btn btn-primary btn-block" disabled={pending}>
          {pending ? 'Generando enlace…' : 'Enviar enlace por WhatsApp'}
        </button>
      </form>
      <p className="auth-links muted small">
        <Link to="/login">Volver a iniciar sesión</Link>
      </p>
    </div>
  )
}
