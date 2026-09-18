import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './context'
import type { Role } from '../api/client'

export function ProtectedRoute({ role }: { role: Role }) {
  const { state } = useAuth()
  const location = useLocation()
  if (state.status === 'loading') return <p role="status">Verificando sessão...</p>
  if (state.status === 'anonymous') return <Navigate to="/login" state={{ from: location.pathname }} replace />
  if (state.user.role !== role) return <Navigate to="/forbidden" replace />
  return <Outlet />
}
