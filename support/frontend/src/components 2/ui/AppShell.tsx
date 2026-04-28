import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Box } from '@mui/material'
import Sidebar, { type SidebarSectionConfig } from './Sidebar'
import Topbar from './Topbar'
import { useAuth } from '@/features/auth/useAuth'
import DashboardIcon from '@mui/icons-material/Dashboard'
import AssignmentIcon from '@mui/icons-material/Assignment'
import BusinessIcon from '@mui/icons-material/Business'
import PeopleIcon from '@mui/icons-material/People'
import SupportAgentIcon from '@mui/icons-material/SupportAgent'
import BarChartIcon from '@mui/icons-material/BarChart'
import SettingsIcon from '@mui/icons-material/Settings'

const mainSections: SidebarSectionConfig[] = [
  {
    title: 'Menú principal',
    items: [
      { path: '/dashboard', label: 'Dashboard', icon: <DashboardIcon /> },
      { path: '/casos', label: 'Casos', icon: <AssignmentIcon /> },
      { path: '/empresas', label: 'Empresas', icon: <BusinessIcon />, adminOnly: true },
      { path: '/usuarios', label: 'Usuarios', icon: <PeopleIcon />, adminOnly: true },
      { path: '/agentes', label: 'Agentes', icon: <SupportAgentIcon /> },
      { path: '/metricas', label: 'Métricas', icon: <BarChartIcon /> },
      { path: '/configuracion', label: 'Configuración', icon: <SettingsIcon /> },
    ],
  },
]

export default function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { user, isAdmin, logout } = useAuth()

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((o) => !o)}
        sections={mainSections}
        isAdmin={!!isAdmin}
      />
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Topbar
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen((o) => !o)}
          title="Synap Support"
          user={user}
          onLogout={logout}
        />
        <Box
          component="main"
          sx={{
            flex: 1,
            p: 3,
            transition: (t) => t.transitions.create('margin', { duration: 200 }),
          }}
        >
          <Outlet />
        </Box>
      </Box>
    </Box>
  )
}
