import { Box, List, ListItemButton, ListItemIcon, ListItemText, Typography } from '@mui/material'
import { useNavigate, useLocation } from 'react-router-dom'

const SIDEBAR_WIDTH = 260
const SIDEBAR_COLLAPSED = 72

export interface SidebarItemConfig {
  path: string
  label: string
  icon: React.ReactNode
  adminOnly?: boolean
}

export interface SidebarSectionConfig {
  title?: string
  items: SidebarItemConfig[]
}

export interface SidebarProps {
  open: boolean
  onToggle?: () => void
  sections: SidebarSectionConfig[]
  isAdmin: boolean
  footer?: React.ReactNode
}

export function SidebarItem({
  label,
  icon,
  isActive,
  onClick,
  open,
}: {
  path: string
  label: string
  icon: React.ReactNode
  isActive: boolean
  onClick: () => void
  open: boolean
}) {
  return (
    <ListItemButton
      onClick={onClick}
      selected={isActive}
      aria-current={isActive ? 'page' : undefined}
      aria-label={label}
      title={!open ? label : undefined}
      sx={{
        borderRadius: 2,
        mx: 1,
        mb: 0.5,
        py: 1.25,
        justifyContent: open ? 'flex-start' : 'center',
        ...(isActive && {
          bgcolor: 'primary.main',
          color: 'primary.contrastText',
          '&:hover': { bgcolor: 'primary.dark' },
          '&.Mui-selected': { bgcolor: 'primary.main' },
        }),
        transition: 'background-color 0.2s ease',
      }}
    >
      <ListItemIcon sx={{ minWidth: 40, color: 'inherit' }}>{icon}</ListItemIcon>
      {open && <ListItemText primary={label} primaryTypographyProps={{ fontWeight: 500 }} />}
    </ListItemButton>
  )
}

export function SidebarSection({ title, items, isAdmin, navigate, location, open }: {
  title?: string
  items: SidebarItemConfig[]
  isAdmin: boolean
  navigate: (path: string) => void
  location: { pathname: string }
  open: boolean
}) {
  const visible = items.filter((i) => !i.adminOnly || isAdmin)
  if (visible.length === 0) return null
  return (
    <>
      {title && open && (
        <Typography
          variant="caption"
          sx={{
            px: 2,
            py: 1,
            color: 'text.secondary',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            display: 'block',
          }}
        >
          {title}
        </Typography>
      )}
      {visible.map((item) => (
        <SidebarItem
          key={item.path}
          path={item.path}
          label={item.label}
          icon={item.icon}
          isActive={location.pathname === item.path || location.pathname.startsWith(item.path + '/')}
          onClick={() => navigate(item.path)}
          open={open}
        />
      ))}
    </>
  )
}

export default function Sidebar({ open, sections, isAdmin, footer }: SidebarProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const width = open ? SIDEBAR_WIDTH : SIDEBAR_COLLAPSED

  return (
    <Box
      component="nav"
      aria-label="Menú principal"
      sx={{
        width,
        flexShrink: 0,
        borderRight: '1px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper',
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        transition: (t) => t.transitions.create('width', { duration: 200 }),
        overflow: 'hidden',
      }}
    >
      <Box sx={{ py: 2, px: open ? 2 : 1.5 }}>
        <Typography
          variant="h6"
          sx={{
            fontWeight: 700,
            color: 'primary.main',
            fontSize: open ? '1.25rem' : '1rem',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {open ? 'Synap Support' : 'Synap'}
        </Typography>
      </Box>
      <List component="div" sx={{ flex: 1, py: 0, px: 0 }}>
        {sections.map((sec, i) => (
          <SidebarSection
            key={i}
            title={sec.title}
            items={sec.items}
            isAdmin={isAdmin}
            navigate={navigate}
            location={location}
            open={open}
          />
        ))}
      </List>
      {footer && (
        <Box sx={{ p: 1.5, borderTop: '1px solid', borderColor: 'divider' }}>
          {footer}
        </Box>
      )}
    </Box>
  )
}

export { SIDEBAR_WIDTH, SIDEBAR_COLLAPSED }
