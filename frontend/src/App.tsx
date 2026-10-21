import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthProvider'
import { useAuth } from './auth/context'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { AppShell } from './layouts/AppShell'

const LoginPage = lazy(() => import('./pages/LoginPage').then(module => ({ default: module.LoginPage })))
const AdminDashboardPage = lazy(() => import('./pages/AdminDashboardPage').then(module => ({ default: module.AdminDashboardPage })))
const AdminOperationsPage = lazy(() => import('./pages/AdminOperationsPage').then(module => ({ default: module.AdminOperationsPage })))
const UserDashboardPage = lazy(() => import('./pages/UserDashboardPage').then(module => ({ default: module.UserDashboardPage })))

function RouteLoading() {
  return <p role="status" aria-live="polite">Carregando página...</p>
}

function Home() {
  const { state } = useAuth()
  if (state.status === 'loading') return <p role="status">Verificando sessão...</p>
  return <Navigate to={state.status === 'authenticated' ? state.user.role === 'ADMIN' ? '/admin' : '/user' : '/login'} replace />
}
export function App() {
  return <AuthProvider><Suspense fallback={<RouteLoading />}><Routes>
    <Route path="/" element={<Home />} />
    <Route path="/login" element={<LoginPage />} />
    <Route element={<ProtectedRoute role="ADMIN" />}>
      <Route path="/admin" element={<AdminDashboardPage />} />
      <Route path="/admin/operacao" element={<AdminOperationsPage />} />
    </Route>
    <Route element={<ProtectedRoute role="USER" />}><Route path="/user" element={<UserDashboardPage />} /></Route>
    <Route path="/forbidden" element={<AppShell><section className="panel"><h1>Acesso não permitido</h1><p>Seu perfil não tem acesso a esta área.</p><a href="/">Voltar</a></section></AppShell>} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></Suspense></AuthProvider>
}
