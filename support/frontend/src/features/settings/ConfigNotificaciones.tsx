import { Drawer, Typography, Box, IconButton, TextField, Button } from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'

interface ConfigNotificacionesProps {
  open: boolean
  onClose: () => void
}

export default function ConfigNotificaciones({ open, onClose }: ConfigNotificacionesProps) {
  return (
    <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: '100%', sm: 420 } } }}>
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Notificaciones y escalamiento</Typography>
          <IconButton onClick={onClose} aria-label="Cerrar">
            <CloseIcon />
          </IconButton>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Endpoints esperados: GET/PATCH /api/config/notifications/. Gerencia y canal de alertas interno.
        </Typography>
        <TextField label="Email alertas internas" fullWidth size="small" sx={{ mb: 1 }} />
        <TextField label="Mensaje estándar SLA por vencer" fullWidth multiline size="small" sx={{ mb: 1 }} />
        <TextField label="Mensaje estándar SLA vencido" fullWidth multiline size="small" sx={{ mb: 2 }} />
        <Button variant="contained" onClick={onClose}>Guardar</Button>
      </Box>
    </Drawer>
  )
}
