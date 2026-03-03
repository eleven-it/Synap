import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  AppBar,
  IconButton,
  Typography,
} from '@mui/material'
import MenuIcon from '@mui/icons-material/Menu'
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft'
import DashboardIcon from '@mui/icons-material/Dashboard'
import AssignmentIcon from '@mui/icons-material/Assignment'
import BusinessIcon from '@mui/icons-material/Business'
import PeopleIcon from '@mui/icons-material/People'
import SupportAgentIcon from '@mui/icons-material/SupportAgent'
import BarChartIcon from '@mui/icons-material/BarChart'
import SettingsIcon from '@mui/icons-material/Settings'
import { useAuth } from '@/features/auth/useAuth'

const DRAWER_WIDTH = 260

const navItems: { path: string; label: string; icon: React.ReactNode; adminOnly?: boolean }[] = [
  { path: '/dashboard', label: 'Dashboard', icon: <DashboardIcon /> },
  { path: '/casos', label: 'Casos', icon: <AssignmentIcon /> },
  { path: '/empresas', label: 'Empresas', icon: <BusinessIcon />, adminOnly: true },
  { path: '/usuarios', label: 'Usuarios', icon: <PeopleIcon />, adminOnly: true },
  { path: '/agentes', label: 'Agentes', icon: <SupportAgentIcon /> },
  { path: '/metricas', label: 'Métricas', icon: <BarChartIcon /> },
  { path: '/configuracion', label: 'Configuración', icon: <SettingsIcon /> },
]

export default function Layout() {
  const [open, setOpen] = useState(true)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, isAdmin, logout } = useAuth()

  const items = navItems.filter((item) => !item.adminOnly || isAdmin)

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label={open ? 'Cerrar menú' : 'Abrir menú'}
            onClick={() => setOpen(!open)}
            edge="start"
            sx={{ mr: 1 }}
          >
            {open ? <ChevronLeftIcon /> : <MenuIcon />}
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            Synap Support
          </Typography>
          <Typography variant="body2" sx={{ mr: 1 }}>
            {user?.username} ({user?.role})
          </Typography>
          <IconButton color="inherit" onClick={logout} aria-label="Cerrar sesión">
            Salir
          </IconButton>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        open={open}
        sx={{
          width: open ? DRAWER_WIDTH : 0,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
            top: 64,
            height: 'calc(100vh - 64px)',
            transition: (theme) => theme.transitions.create('width', { duration: 150 }),
            overflowX: 'hidden',
          },
        }}
      >
        <List component="nav" sx={{ pt: 1 }}>
          {items.map((item) => (
            <ListItemButton
              key={item.path}
              selected={location.pathname === item.path || location.pathname.startsWith(item.path + '/')}
              onClick={() => navigate(item.path)}
              sx={{ borderRadius: 1, mx: 1, mb: 0.5 }}
            >
              <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          ))}
        </List>
      </Drawer>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 2,
          width: open ? `calc(100% - ${DRAWER_WIDTH}px)` : '100%',
          mt: 8,
          transition: (theme) => theme.transitions.create('margin', { duration: 150 }),
        }}
      >
        <Outlet />
      </Box>
    </Box>
  )
}
