import { Box, Button, IconButton, Toolbar, Typography } from '@mui/material'
import MenuIcon from '@mui/icons-material/Menu'
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft'
import DarkModeIcon from '@mui/icons-material/DarkMode'
import LightModeIcon from '@mui/icons-material/LightMode'
import { useContext } from 'react'
import { ThemeModeContext } from '@/app/ThemeProvider'

export interface TopbarProps {
  sidebarOpen: boolean
  onToggleSidebar: () => void
  title?: string
  actions?: React.ReactNode
  user?: { username: string; role?: string } | null
  onLogout?: () => void
}

export default function Topbar({
  sidebarOpen,
  onToggleSidebar,
  title,
  actions,
  user,
  onLogout,
}: TopbarProps) {
  const { mode, toggleMode } = useContext(ThemeModeContext)
  const isDark = mode === 'dark'

  return (
    <Box
      component="header"
      sx={{
        borderBottom: '1px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper',
        position: 'sticky',
        top: 0,
        zIndex: (t) => t.zIndex.appBar,
      }}
    >
      <Toolbar disableGutters sx={{ px: 2, py: 1, minHeight: { xs: 56, sm: 64 } }}>
        <IconButton
          color="inherit"
          onClick={onToggleSidebar}
          aria-label={sidebarOpen ? 'Cerrar menú' : 'Abrir menú'}
          sx={{ mr: 1 }}
        >
          {sidebarOpen ? <ChevronLeftIcon /> : <MenuIcon />}
        </IconButton>
        {title && (
          <Typography variant="h6" sx={{ fontWeight: 600, flex: 1 }}>
            {title}
          </Typography>
        )}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          {actions}
          <IconButton
            color="inherit"
            onClick={toggleMode}
            aria-label={isDark ? 'Usar tema claro' : 'Usar tema oscuro'}
          >
            {isDark ? <LightModeIcon /> : <DarkModeIcon />}
          </IconButton>
          {user && (
            <Typography variant="body2" color="text.secondary" sx={{ mr: 1 }}>
              {user.username}
              {user.role && ` (${user.role})`}
            </Typography>
          )}
          {onLogout && (
            <Button color="inherit" onClick={onLogout} size="small" aria-label="Cerrar sesión">
              Salir
            </Button>
          )}
        </Box>
      </Toolbar>
    </Box>
  )
}
