import { Drawer, Typography, Box, IconButton, TextField, Button } from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'

interface ConfigBrandingProps {
  open: boolean
  onClose: () => void
}

export default function ConfigBranding({ open, onClose }: ConfigBrandingProps) {
  return (
    <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: '100%', sm: 420 } } }}>
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Branding / Mensajes</Typography>
          <IconButton onClick={onClose} aria-label="Cerrar">
            <CloseIcon />
          </IconButton>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Opcional. Endpoints esperados: GET/PATCH /api/config/branding/ (por empresa o global).
        </Typography>
        <TextField label="Nombre del asistente" fullWidth size="small" sx={{ mb: 1 }} />
        <TextField label="Mensaje de saludo" fullWidth multiline size="small" sx={{ mb: 1 }} />
        <TextField label="Idioma por defecto" fullWidth size="small" sx={{ mb: 2 }} placeholder="es" />
        <Button variant="contained" onClick={onClose}>Guardar</Button>
      </Box>
    </Drawer>
  )
}
