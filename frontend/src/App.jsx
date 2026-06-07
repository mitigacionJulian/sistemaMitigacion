import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout.jsx'
import { RouteErrorBoundary } from './components/RouteErrorBoundary.jsx'
import { AuthProvider } from './context/AuthContext.jsx'
import { Dashboard } from './pages/Dashboard.jsx'
import { Landing } from './pages/Landing.jsx'
import { Mapa } from './pages/Mapa.jsx'
import { Login } from './pages/Login.jsx'
import { Register } from './pages/Register.jsx'
import { RecoverPasswordGate } from './pages/RecoverPasswordGate.jsx'
import { RequireAnalista } from './components/RequireAnalista.jsx'
import { Agente } from './pages/Agente.jsx'

const Predicciones = lazy(() =>
  import('./pages/Predicciones.jsx').then((m) => ({ default: m.Predicciones })),
)

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Landing />} />
            <Route path="mapa" element={<Mapa />} />
            <Route path="tablero" element={<Dashboard />} />
            <Route path="agente" element={<Agente />} />
            <Route
              path="predicciones"
              element={
                <RequireAnalista>
                  <RouteErrorBoundary>
                    <Suspense fallback={<p className="muted">Cargando predicciones…</p>}>
                      <Predicciones />
                    </Suspense>
                  </RouteErrorBoundary>
                </RequireAnalista>
              }
            />
            <Route path="login" element={<Login />} />
            <Route path="registro" element={<Register />} />
            <Route path="recuperar-clave" element={<RecoverPasswordGate />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
