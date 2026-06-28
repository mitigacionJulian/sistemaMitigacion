import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  createAdminUsuario,
  deleteAdminUsuario,
  fetchAdminRoles,
  fetchAdminUsuarios,
  updateAdminUsuario,
} from '../api/client.js'
import { useAuth } from '../context/AuthContext.jsx'

const EMPTY_FORM = {
  username: '',
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  telefono: '',
  organizacion: '',
  rol_codigo: 'ciudadano',
  is_active: true,
}

function formatFecha(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('es-CO', {
      dateStyle: 'short',
      timeStyle: 'short',
    })
  } catch {
    return iso
  }
}

function userToForm(user) {
  if (!user) return { ...EMPTY_FORM, username: '', password: '' }
  return {
    username: user.username || '',
    email: user.email || '',
    password: '',
    first_name: user.first_name || '',
    last_name: user.last_name || '',
    telefono: user.perfil?.telefono || '',
    organizacion: user.perfil?.organizacion || '',
    rol_codigo: user.perfil?.rol_codigo || 'ciudadano',
    is_active: user.is_active !== false,
  }
}

export function AdminUsuarios() {
  const { user: sessionUser } = useAuth()
  const [roles, setRoles] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filtroQ, setFiltroQ] = useState('')
  const [filtroRol, setFiltroRol] = useState('')
  const [filtroActivo, setFiltroActivo] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [modo, setModo] = useState('lista')
  const [form, setForm] = useState(EMPTY_FORM)
  const [pending, setPending] = useState(false)
  const [mensaje, setMensaje] = useState(null)

  const selectedUser = useMemo(
    () => usuarios.find((u) => u.id === selectedId) ?? null,
    [usuarios, selectedId],
  )

  const cargar = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filtroQ.trim()) params.q = filtroQ.trim()
      if (filtroRol) params.rol = filtroRol
      if (filtroActivo === 'true' || filtroActivo === 'false') params.activo = filtroActivo === 'true'
      const [rolesData, usuariosData] = await Promise.all([
        fetchAdminRoles(),
        fetchAdminUsuarios(params),
      ])
      setRoles(rolesData)
      setUsuarios(usuariosData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar usuarios')
    } finally {
      setLoading(false)
    }
  }, [filtroQ, filtroRol, filtroActivo])

  useEffect(() => {
    void cargar()
  }, [cargar])

  const hayFiltros = Boolean(filtroQ.trim() || filtroRol || filtroActivo)

  const limpiarFiltros = () => {
    setFiltroQ('')
    setFiltroRol('')
    setFiltroActivo('')
  }

  const abrirDetalle = (usuario) => {
    setSelectedId(usuario.id)
    setForm(userToForm(usuario))
    setModo('editar')
    setMensaje(null)
  }

  const abrirCrear = () => {
    setSelectedId(null)
    setForm(EMPTY_FORM)
    setModo('crear')
    setMensaje(null)
  }

  const volverLista = () => {
    setModo('lista')
    setSelectedId(null)
    setForm(EMPTY_FORM)
    setMensaje(null)
  }

  const onChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const guardar = async (e) => {
    e.preventDefault()
    setPending(true)
    setMensaje(null)
    setError(null)
    try {
      if (modo === 'crear') {
        await createAdminUsuario({
          username: form.username.trim(),
          email: form.email.trim(),
          password: form.password,
          first_name: form.first_name.trim(),
          last_name: form.last_name.trim(),
          telefono: form.telefono.trim(),
          organizacion: form.organizacion.trim(),
          rol_codigo: form.rol_codigo,
          is_active: form.is_active,
        })
        setMensaje('Usuario creado correctamente.')
        await cargar()
        volverLista()
      } else if (selectedUser) {
        const payload = {
          email: form.email.trim(),
          first_name: form.first_name.trim(),
          last_name: form.last_name.trim(),
          telefono: form.telefono.trim(),
          organizacion: form.organizacion.trim(),
          rol_codigo: form.rol_codigo,
          is_active: form.is_active,
        }
        if (form.password.trim()) payload.password = form.password
        const updated = await updateAdminUsuario(selectedUser.id, payload)
        setUsuarios((prev) => prev.map((u) => (u.id === updated.id ? updated : u)))
        setMensaje('Cambios guardados.')
        setForm(userToForm(updated))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo guardar')
    } finally {
      setPending(false)
    }
  }

  const toggleActivo = async (usuario) => {
    if (usuario.id === sessionUser?.id) {
      setError('No puede deshabilitar su propia cuenta.')
      return
    }
    setPending(true)
    setError(null)
    try {
      const updated = await updateAdminUsuario(usuario.id, { is_active: !usuario.is_active })
      setUsuarios((prev) => prev.map((u) => (u.id === updated.id ? updated : u)))
      if (selectedId === updated.id) setForm(userToForm(updated))
      setMensaje(updated.is_active ? 'Usuario habilitado.' : 'Usuario deshabilitado.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cambiar el estado')
    } finally {
      setPending(false)
    }
  }

  const eliminar = async (usuario) => {
    if (usuario.id === sessionUser?.id) {
      setError('No puede eliminar su propia cuenta.')
      return
    }
    const ok = window.confirm(
      `¿Eliminar permanentemente al usuario «${usuario.username}»? Esta acción no se puede deshacer.`,
    )
    if (!ok) return
    setPending(true)
    setError(null)
    try {
      await deleteAdminUsuario(usuario.id)
      setUsuarios((prev) => prev.filter((u) => u.id !== usuario.id))
      if (selectedId === usuario.id) volverLista()
      setMensaje('Usuario eliminado.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo eliminar')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="admin-usuarios-page">
      <header className="admin-usuarios-header">
        <div>
          <h1>Gestión de usuarios</h1>
          <p className="muted small">
            Administre cuentas registradas: consulte datos, cambie roles, habilite o deshabilite acceso y elimine
            usuarios. Solo visible para administradores.
          </p>
        </div>
        {modo === 'lista' && (
          <div className="admin-pruebas-header-actions">
            <Link to="/admin/pruebas" className="btn btn-secondary">
              Pruebas Allure
            </Link>
            <button type="button" className="btn btn-primary" onClick={abrirCrear}>
              Nuevo usuario
            </button>
          </div>
        )}
      </header>

      {error && <p className="form-error admin-usuarios-alert">{error}</p>}
      {mensaje && <p className="admin-usuarios-success" role="status">{mensaje}</p>}

      {modo === 'lista' ? (
        <>
          <section className="panel filter-panel admin-usuarios-filtros">
            <div className="admin-usuarios-filtros-head">
              <div>
                <h2>Filtros de búsqueda</h2>
                <p className="muted small filter-help">
                  Busque por usuario, correo o nombre y acote el listado por rol o estado de la cuenta.
                </p>
              </div>
              {!loading && (
                <span className="admin-usuarios-count-badge" aria-live="polite">
                  {usuarios.length} {usuarios.length === 1 ? 'usuario' : 'usuarios'}
                </span>
              )}
            </div>
            <div className="admin-usuarios-filtros-bar">
              <label className="filter-field admin-usuarios-field-search">
                Buscar
                <input
                  type="search"
                  value={filtroQ}
                  onChange={(e) => setFiltroQ(e.target.value)}
                  placeholder="Usuario, correo o nombre…"
                  autoComplete="off"
                />
              </label>
              <label className="filter-field admin-usuarios-field-select">
                Rol
                <select value={filtroRol} onChange={(e) => setFiltroRol(e.target.value)}>
                  <option value="">Todos los roles</option>
                  {roles.map((rol) => (
                    <option key={rol.codigo} value={rol.codigo}>
                      {rol.nombre}
                    </option>
                  ))}
                </select>
              </label>
              <label className="filter-field admin-usuarios-field-select">
                Estado
                <select value={filtroActivo} onChange={(e) => setFiltroActivo(e.target.value)}>
                  <option value="">Todos</option>
                  <option value="true">Solo activos</option>
                  <option value="false">Solo deshabilitados</option>
                </select>
              </label>
              <div className="admin-usuarios-filtros-actions">
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={limpiarFiltros}
                  disabled={!hayFiltros || pending}
                >
                  Limpiar filtros
                </button>
              </div>
            </div>
          </section>

          <section className="panel admin-usuarios-tabla-panel">
            {loading ? (
              <p className="muted">Cargando usuarios…</p>
            ) : usuarios.length === 0 ? (
              <p className="muted">No hay usuarios que coincidan con los filtros.</p>
            ) : (
              <div className="admin-usuarios-table-wrap">
                <table className="table admin-usuarios-table">
                  <thead>
                    <tr>
                      <th>Usuario</th>
                      <th>Nombre</th>
                      <th>Correo</th>
                      <th>Rol</th>
                      <th>Estado</th>
                      <th>Registro</th>
                      <th aria-label="Acciones" />
                    </tr>
                  </thead>
                  <tbody>
                    {usuarios.map((u) => (
                      <tr key={u.id} className={!u.is_active ? 'admin-usuarios-row-inactivo' : undefined}>
                        <td>
                          <strong>{u.username}</strong>
                          {u.id === sessionUser?.id && (
                            <span className="admin-usuarios-yo-badge">Usted</span>
                          )}
                        </td>
                        <td>{[u.first_name, u.last_name].filter(Boolean).join(' ') || '—'}</td>
                        <td>{u.email || '—'}</td>
                        <td>
                          <span className="badge-rol">{u.perfil?.rol_nombre ?? '—'}</span>
                        </td>
                        <td>
                          <span
                            className={`admin-usuarios-estado ${
                              u.is_active ? 'admin-usuarios-estado--activo' : 'admin-usuarios-estado--inactivo'
                            }`}
                          >
                            {u.is_active ? 'Activo' : 'Deshabilitado'}
                          </span>
                        </td>
                        <td className="muted small">{formatFecha(u.date_joined)}</td>
                        <td className="admin-usuarios-acciones">
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={() => abrirDetalle(u)}
                          >
                            Detalle
                          </button>
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            disabled={pending || u.id === sessionUser?.id}
                            onClick={() => void toggleActivo(u)}
                          >
                            {u.is_active ? 'Deshabilitar' : 'Habilitar'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : (
        <section className="panel admin-usuarios-form-panel">
          <div className="admin-usuarios-form-header">
            <h2>{modo === 'crear' ? 'Nuevo usuario' : `Editar: ${selectedUser?.username ?? ''}`}</h2>
            <button type="button" className="btn btn-ghost" onClick={volverLista}>
              Volver al listado
            </button>
          </div>

          <form className="form admin-usuarios-form" onSubmit={(e) => void guardar(e)}>
            <div className="admin-usuarios-form-grid">
              <label>
                Usuario *
                <input
                  value={form.username}
                  onChange={(e) => onChange('username', e.target.value)}
                  required
                  disabled={modo === 'editar'}
                  autoComplete="off"
                />
              </label>
              <label>
                Correo *
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => onChange('email', e.target.value)}
                  required
                />
              </label>
              <label>
                {modo === 'crear' ? 'Contraseña *' : 'Nueva contraseña (opcional)'}
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => onChange('password', e.target.value)}
                  required={modo === 'crear'}
                  autoComplete="new-password"
                />
              </label>
              <label>
                Rol *
                <select
                  value={form.rol_codigo}
                  onChange={(e) => onChange('rol_codigo', e.target.value)}
                  required
                >
                  {roles.map((rol) => (
                    <option key={rol.codigo} value={rol.codigo}>
                      {rol.nombre}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Nombre
                <input value={form.first_name} onChange={(e) => onChange('first_name', e.target.value)} />
              </label>
              <label>
                Apellido
                <input value={form.last_name} onChange={(e) => onChange('last_name', e.target.value)} />
              </label>
              <label>
                Celular
                <input value={form.telefono} onChange={(e) => onChange('telefono', e.target.value)} />
              </label>
              <label>
                Organización
                <input value={form.organizacion} onChange={(e) => onChange('organizacion', e.target.value)} />
              </label>
            </div>

            <label className="checkbox-inline admin-usuarios-checkbox">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => onChange('is_active', e.target.checked)}
                disabled={modo === 'editar' && selectedUser?.id === sessionUser?.id}
              />
              Cuenta activa (puede iniciar sesión)
            </label>

            {modo === 'editar' && selectedUser && (
              <dl className="admin-usuarios-meta muted small">
                <div>
                  <dt>ID</dt>
                  <dd>{selectedUser.id}</dd>
                </div>
                <div>
                  <dt>Registrado</dt>
                  <dd>{formatFecha(selectedUser.date_joined)}</dd>
                </div>
                <div>
                  <dt>Último acceso</dt>
                  <dd>{formatFecha(selectedUser.last_login)}</dd>
                </div>
              </dl>
            )}

            <div className="admin-usuarios-form-actions">
              <button type="submit" className="btn btn-primary" disabled={pending}>
                {pending ? 'Guardando…' : modo === 'crear' ? 'Crear usuario' : 'Guardar cambios'}
              </button>
              {modo === 'editar' && selectedUser && selectedUser.id !== sessionUser?.id && (
                <button
                  type="button"
                  className="btn btn-danger"
                  disabled={pending}
                  onClick={() => void eliminar(selectedUser)}
                >
                  Eliminar usuario
                </button>
              )}
            </div>
          </form>
        </section>
      )}
    </div>
  )
}
