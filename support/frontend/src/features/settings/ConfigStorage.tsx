import { Drawer, Typography, Box, IconButton, TextField, Button } from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'

interface ConfigStorageProps {
  open: boolean
  onClose: () => void
}

export default function ConfigStorage({ open, onClose }: ConfigStorageProps) {
  return (
    <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: '100%', sm: 420 } } }}>
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Storage / Adjuntos</Typography>
          <IconButton onClick={onClose} aria-label="Cerrar">
            <CloseIcon />
          </IconButton>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Endpoints esperados: GET/PATCH /api/config/storage/, POST /api/config/storage/test/ (subir archivo de prueba o generar URL firmada).
        </Typography>
        <TextField label="Endpoint S3/MinIO" fullWidth size="small" sx={{ mb: 1 }} />
        <TextField label="Bucket" fullWidth size="small" sx={{ mb: 1 }} />
        <TextField label="Access Key" fullWidth size="small" sx={{ mb: 1 }} />
        <TextField label="Secret Key" type="password" fullWidth size="small" sx={{ mb: 1 }} />
        <TextField label="Tamaño máx. (bytes)" type="number" fullWidth size="small" sx={{ mb: 2 }} />
        <Button variant="outlined" sx={{ mr: 1 }}>Probar conexión</Button>
        <Button variant="contained" onClick={onClose}>Guardar</Button>
      </Box>
    </Drawer>
  )
}
