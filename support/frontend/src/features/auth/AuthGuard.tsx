import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './useAuth'

interface AuthGuardProps {
  children: React.ReactNode
  requireAdmin?: boolean
}

export function AuthGuard({ children, requireAdmin = false }: AuthGuardProps) {
  const location = useLocation()
  const { user, isLoading, isAdmin, isAgentOrAdmin } = useAuth()

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <span aria-live="polite">Cargando…</span>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (requireAdmin && !isAdmin) {
    return <Navigate to="/dashboard" replace />
  }

  if (!requireAdmin && !isAgentOrAdmin) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
