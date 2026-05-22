import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout.jsx'
import { RouteErrorBoundary } from './components/RouteErrorBoundary.jsx'
import { AuthProvider } from './context/AuthContext.jsx'
import { Dashboard } from './pages/Dashboard.jsx'
import { Landing } from './pages/Landing.jsx'
import { Login } from './pages/Login.jsx'
import { Register } from './pages/Register.jsx'

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
            <Route path="tablero" element={<Dashboard />} />
            <Route
              path="predicciones"
              element={
                <RouteErrorBoundary>
                  <Suspense fallback={<p className="muted">Cargando predicciones…</p>}>
                    <Predicciones />
                  </Suspense>
                </RouteErrorBoundary>
              }
            />
            <Route path="login" element={<Login />} />
            <Route path="registro" element={<Register />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
