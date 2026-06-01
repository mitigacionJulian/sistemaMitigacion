import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { PhoneCoInput } from '../components/PhoneCoInput.jsx'
import { useAuth } from '../context/AuthContext.jsx'

export function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [telefono, setTelefono] = useState('')
  const [rolCodigo, setRolCodigo] = useState('ciudadano')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [error, setError] = useState(null)
  const [pending, setPending] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError(null)
    setPending(true)
    try {
      const u = await register({
        username,
        email,
        first_name: firstName,
        last_name: lastName,
        telefono,
        rol_codigo: rolCodigo,
        password,
        password_confirm: passwordConfirm,
      })
      if (u?.perfil?.rol_codigo === 'analista') {
        navigate('/predicciones', { replace: true })
      } else {
        navigate('/tablero', { replace: true })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al registrar')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="auth-card auth-card-wide">
      <h1>Crear cuenta</h1>
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
          Correo
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
          />
        </label>
        <div className="form-row">
          <label>
            Nombre
            <input value={firstName} onChange={(e) => setFirstName(e.target.value)} />
          </label>
          <label>
            Apellido
            <input value={lastName} onChange={(e) => setLastName(e.target.value)} />
          </label>
        </div>
        <label>
          Celular (WhatsApp)
          <PhoneCoInput id="reg-telefono" value={telefono} onChange={setTelefono} />
        </label>
        <label>
          Rol
          <select value={rolCodigo} onChange={(e) => setRolCodigo(e.target.value)} required>
            <option value="ciudadano">Ciudadano — consulta tablero e inicio</option>
            <option value="analista">Analista — incluye predicciones</option>
          </select>
        </label>
        <label>
          Contraseña
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
        <button type="submit" className="btn btn-primary btn-block" disabled={pending}>
          {pending ? 'Creando cuenta…' : 'Registrarme'}
        </button>
      </form>
      <p className="auth-links muted small">
        ¿Ya tiene cuenta? <Link to="/login">Iniciar sesión</Link>
      </p>
    </div>
  )
}
