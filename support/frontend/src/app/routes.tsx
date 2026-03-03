import { createBrowserRouter, Navigate } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import { AuthGuard } from '@/features/auth/AuthGuard'
import { AppShell } from '@/components/ui'
import LoginPage from '@/features/auth/LoginPage'

const DashboardPage = lazy(() => import('@/features/dashboard/DashboardPage'))
const CasesListPage = lazy(() => import('@/features/cases/CasesListPage'))
const CaseDetailPage = lazy(() => import('@/features/cases/CaseDetailPage'))
const CompaniesPage = lazy(() => import('@/features/companies/CompaniesPage'))
const UsersPage = lazy(() => import('@/features/users/UsersPage'))
const AgentsPage = lazy(() => import('@/features/agents/AgentsPage'))
const MetricsPage = lazy(() => import('@/features/metrics/MetricsPage'))
const SettingsPage = lazy(() => import('@/features/settings/SettingsPage'))

function PageFallback() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
      <span aria-live="polite">Cargando…</span>
    </div>
  )
}

export const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/dashboard" replace /> },
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: (
      <AuthGuard>
        <AppShell />
      </AuthGuard>
    ),
    children: [
      {
        path: 'dashboard',
        element: (
          <Suspense fallback={<PageFallback />}>
            <DashboardPage />
          </Suspense>
        ),
      },
      {
        path: 'casos',
        element: (
          <Suspense fallback={<PageFallback />}>
            <CasesListPage />
          </Suspense>
        ),
      },
      {
        path: 'casos/:id',
        element: (
          <Suspense fallback={<PageFallback />}>
            <CaseDetailPage />
          </Suspense>
        ),
      },
      {
        path: 'empresas',
        element: (
          <AuthGuard requireAdmin>
            <Suspense fallback={<PageFallback />}>
              <CompaniesPage />
            </Suspense>
          </AuthGuard>
        ),
      },
      {
        path: 'usuarios',
        element: (
          <AuthGuard requireAdmin>
            <Suspense fallback={<PageFallback />}>
              <UsersPage />
            </Suspense>
          </AuthGuard>
        ),
      },
      {
        path: 'agentes',
        element: (
          <Suspense fallback={<PageFallback />}>
            <AgentsPage />
          </Suspense>
        ),
      },
      {
        path: 'metricas',
        element: (
          <Suspense fallback={<PageFallback />}>
            <MetricsPage />
          </Suspense>
        ),
      },
      {
        path: 'configuracion',
        element: (
          <Suspense fallback={<PageFallback />}>
            <SettingsPage />
          </Suspense>
        ),
      },
    ],
  },
  { path: '*', element: <Navigate to="/dashboard" replace /> },
])
