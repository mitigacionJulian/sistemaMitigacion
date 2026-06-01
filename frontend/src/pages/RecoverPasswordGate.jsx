import { useSearchParams } from 'react-router-dom'
import { ForgotPassword } from './ForgotPassword.jsx'
import { ResetPassword } from './ResetPassword.jsx'

/** /recuperar-clave sin token → solicitud; con ?token= → nueva contraseña */
export function RecoverPasswordGate() {
  const [search] = useSearchParams()
  if (search.get('token')) return <ResetPassword />
  return <ForgotPassword />
}
