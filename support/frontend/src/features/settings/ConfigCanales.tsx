import {
  Drawer,
  Typography,
  Box,
  IconButton,
  Stepper,
  Step,
  StepLabel,
  Button,
  TextField,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import { useState } from 'react'

interface ConfigCanalesProps {
  open: boolean
  onClose: () => void
}

const STEPS = ['WhatsApp Meta', 'Telegram', 'Email SMTP/IMAP']

export default function ConfigCanales({ open, onClose }: ConfigCanalesProps) {
  const [activeStep, setActiveStep] = useState(0)

  return (
    <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: '100%', sm: 420 } } }}>
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Configurar canales</Typography>
          <IconButton onClick={onClose} aria-label="Cerrar">
            <CloseIcon />
          </IconButton>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Los endpoints para guardar y probar esta configuración se documentan en README (Endpoints esperados → Canales).
        </Typography>
        <Stepper activeStep={activeStep} sx={{ mb: 2 }}>
          {STEPS.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>
        {activeStep === 0 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant="subtitle2">WhatsApp Meta (Cloud API)</Typography>
            <TextField label="Token de acceso" type="password" fullWidth size="small" placeholder="Configurar en backend" />
            <TextField label="Webhook verify token" fullWidth size="small" />
            <Typography variant="caption" color="text.secondary">
              Instrucciones: registrar webhook en Meta Developer y pegar la URL del backend + verify token.
            </Typography>
          </Box>
        )}
        {activeStep === 1 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant="subtitle2">Telegram</Typography>
            <TextField label="Bot token" type="password" fullWidth size="small" placeholder="Configurar en backend" />
            <Typography variant="caption" color="text.secondary">
              Crear bot con @BotFather y configurar webhook: POST /api/webhooks/telegram/
            </Typography>
          </Box>
        )}
        {activeStep === 2 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant="subtitle2">Email SMTP / IMAP</Typography>
            <TextField label="SMTP host" fullWidth size="small" />
            <TextField label="SMTP puerto" type="number" fullWidth size="small" />
            <TextField label="Usuario" fullWidth size="small" />
            <TextField label="Contraseña" type="password" fullWidth size="small" />
            <TextField label="IMAP host (entrada)" fullWidth size="small" />
          </Box>
        )}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
          <Button disabled={activeStep === 0} onClick={() => setActiveStep((s) => s - 1)}>
            Atrás
          </Button>
          {activeStep < STEPS.length - 1 ? (
            <Button variant="contained" onClick={() => setActiveStep((s) => s + 1)}>
              Siguiente
            </Button>
          ) : (
            <Button variant="contained" onClick={onClose}>
              Guardar borrador
            </Button>
          )}
        </Box>
      </Box>
    </Drawer>
  )
}
