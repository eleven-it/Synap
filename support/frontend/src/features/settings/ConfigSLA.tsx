import { Drawer, Typography, Box, IconButton, TextField, Button } from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'

interface ConfigSLAProps {
  open: boolean
  onClose: () => void
}

export default function ConfigSLA({ open, onClose }: ConfigSLAProps) {
  return (
    <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: '100%', sm: 420 } } }}>
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">SLA</Typography>
          <IconButton onClick={onClose} aria-label="Cerrar">
            <CloseIcon />
          </IconButton>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Configuración por empresa y tipo de caso. Backend: ConfigSLA en DB. Endpoints esperados: GET/POST/PATCH /api/config/sla/, POST /api/config/sla/test/ (simular vencimiento).
        </Typography>
        <TextField label="Tiempo respuesta (min)" type="number" fullWidth size="small" sx={{ mb: 1 }} />
        <TextField label="Warning %" type="number" fullWidth size="small" sx={{ mb: 1 }} placeholder="70 u 80" />
        <TextField label="Escalar a (gerencia)" fullWidth size="small" sx={{ mb: 2 }} />
        <Button variant="outlined" sx={{ mr: 1 }}>Simular vencimiento</Button>
        <Button variant="contained" onClick={onClose}>Guardar</Button>
      </Box>
    </Drawer>
  )
}
