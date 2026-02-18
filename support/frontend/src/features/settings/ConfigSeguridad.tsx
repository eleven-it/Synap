import { Drawer, Typography, Box, IconButton, FormControlLabel, Switch, Button } from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'

interface ConfigSeguridadProps {
  open: boolean
  onClose: () => void
}

export default function ConfigSeguridad({ open, onClose }: ConfigSeguridadProps) {
  return (
    <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: '100%', sm: 420 } } }}>
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Seguridad operativa</Typography>
          <IconButton onClick={onClose} aria-label="Cerrar">
            <CloseIcon />
          </IconButton>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Endpoints esperados: GET/PATCH /api/config/security/, POST /api/config/security/self-check/
        </Typography>
        <FormControlLabel control={<Switch />} label="Rate limit por canal" sx={{ display: 'block', mb: 1 }} />
        <FormControlLabel control={<Switch />} label="Anti-spam / flood" sx={{ display: 'block', mb: 1 }} />
        <FormControlLabel control={<Switch />} label="Advertencia PII en mensajes" sx={{ display: 'block', mb: 2 }} />
        <Button variant="outlined" sx={{ mr: 1 }}>Ejecutar self-check</Button>
        <Button variant="contained" onClick={onClose}>Guardar</Button>
      </Box>
    </Drawer>
  )
}
