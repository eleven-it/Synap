import { Drawer, Typography, IconButton, Box } from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'

export interface SidePanelProps {
  open: boolean
  onClose: () => void
  title: string
  subtitle?: string
  children: React.ReactNode
  width?: number | string
}

/**
 * Panel lateral tipo Kora para configuración (reemplaza modal/drawer genérico).
 */
export default function SidePanel({
  open,
  onClose,
  title,
  subtitle,
  children,
  width = 420,
}: SidePanelProps) {
  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      ModalProps={{ BackdropProps: { transitionDuration: 200 } }}
      sx={{
        '& .MuiDrawer-paper': {
          width: { xs: '100%', sm: width },
          maxWidth: '100%',
          boxSizing: 'border-box',
          borderLeft: '1px solid',
          borderColor: 'divider',
          borderRadius: 0,
          transition: 'transform 0.2s ease',
        },
      }}
    >
      <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 1 }}>
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {title}
          </Typography>
          {subtitle && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {subtitle}
            </Typography>
          )}
        </Box>
        <IconButton size="small" onClick={onClose} aria-label="Cerrar">
          <CloseIcon />
        </IconButton>
      </Box>
      <Box sx={{ p: 2, overflow: 'auto', flex: 1 }}>
        {children}
      </Box>
    </Drawer>
  )
}
