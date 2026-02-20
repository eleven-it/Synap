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
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useSnackbar } from 'notistack'
import api from '@/api/endpoints'
import type { ChannelConfig } from '@/types'

interface ConfigCanalesProps {
  open: boolean
  onClose: () => void
  channelsList: ChannelConfig[]
}

const STEPS = ['WhatsApp Meta', 'Telegram', 'Email SMTP/IMAP']

export default function ConfigCanales({ open, onClose, channelsList }: ConfigCanalesProps) {
  const [activeStep, setActiveStep] = useState(0)
  const [telegramToken, setTelegramToken] = useState('')
  const queryClient = useQueryClient()
  const { enqueueSnackbar } = useSnackbar()

  const telegramChannel = channelsList.find((c) => c.channel_type === 'telegram')

  const saveTelegramMutation = useMutation({
    mutationFn: async (token: string) => {
      const config = { token: token.trim() }
      if (telegramChannel) {
        return api.config.channels.patch(telegramChannel.id, { config })
      }
      return api.config.channels.create({
        channel_type: 'telegram',
        display_name: 'Telegram',
        config,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config', 'channels'] })
      enqueueSnackbar('Token de Telegram guardado (cifrado)', { variant: 'success' })
      setTelegramToken('')
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      enqueueSnackbar(err.response?.data?.detail || 'Error al guardar el token', { variant: 'error' })
    },
  })

  const handleSaveTelegram = () => {
    if (!telegramToken.trim()) {
      enqueueSnackbar('Escribí el token del bot', { variant: 'warning' })
      return
    }
    saveTelegramMutation.mutate(telegramToken)
  }

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
          Los tokens se guardan cifrados en el backend. Probar desde la card Canales tras guardar.
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
            <TextField
              label="Bot token"
              type="password"
              fullWidth
              size="small"
              placeholder={telegramChannel ? 'Dejar vacío para no cambiar' : 'Token de @BotFather'}
              value={telegramToken}
              onChange={(e) => setTelegramToken(e.target.value)}
              helperText={telegramChannel?.config_masked?.token ? 'Actual: ' + String(telegramChannel.config_masked.token) : undefined}
            />
            <Typography variant="caption" color="text.secondary">
              Crear bot con @BotFather y configurar webhook: POST /api/webhooks/telegram/
            </Typography>
            <Button
              variant="contained"
              onClick={handleSaveTelegram}
              disabled={saveTelegramMutation.isPending || !telegramToken.trim()}
            >
              {saveTelegramMutation.isPending ? 'Guardando…' : 'Guardar token (cifrado)'}
            </Button>
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
              Cerrar
            </Button>
          )}
        </Box>
      </Box>
    </Drawer>
  )
}
