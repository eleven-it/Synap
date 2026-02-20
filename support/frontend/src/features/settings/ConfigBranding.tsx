import { useEffect, useState } from 'react'
import { Drawer, Typography, Box, IconButton, TextField, Button, Alert, CircularProgress } from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/api/endpoints'
import type { BrandingConfig } from '@/types'

interface ConfigBrandingProps {
  open: boolean
  onClose: () => void
  companyId?: number | null
}

export default function ConfigBranding({ open, onClose, companyId = null }: ConfigBrandingProps) {
  const queryClient = useQueryClient()
  const [assistantName, setAssistantName] = useState('')
  const [welcomeMessage, setWelcomeMessage] = useState('')
  const [defaultLanguage, setDefaultLanguage] = useState('es')
  const [saveMessage, setSaveMessage] = useState<string | null>(null)

  const { data: list, isLoading } = useQuery({
    queryKey: ['config', 'branding', companyId],
    queryFn: async () => {
      const { data } = await api.config.branding.list(companyId ?? undefined)
      return data
    },
    enabled: open,
  })

  const config: BrandingConfig | null = Array.isArray(list) && list.length > 0 ? list[0] : null

  useEffect(() => {
    if (config) {
      setAssistantName(config.assistant_name ?? '')
      setWelcomeMessage(config.welcome_message ?? '')
      setDefaultLanguage(config.default_language ?? 'es')
    } else if (!isLoading && open) {
      setAssistantName('')
      setWelcomeMessage('')
      setDefaultLanguage('es')
    }
  }, [config, isLoading, open])

  const patchMutation = useMutation({
    mutationFn: (payload: Parameters<typeof api.config.branding.patch>[0]) => api.config.branding.patch(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config', 'branding'] })
      setSaveMessage('Configuración de branding guardada. El copiloto usará el nombre del asistente y el mensaje de bienvenida.')
    },
    onError: (err: { response?: { data?: { message?: string; detail?: string } } }) => {
      setSaveMessage(err.response?.data?.message || err.response?.data?.detail || 'Error al guardar.')
    },
  })

  const handleSave = () => {
    setSaveMessage(null)
    patchMutation.mutate({
      company_id: companyId ?? null,
      assistant_name: assistantName.trim(),
      welcome_message: welcomeMessage.trim(),
      default_language: defaultLanguage.trim() || 'es',
    })
  }

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
          Nombre del asistente y mensaje de bienvenida que usa el copiloto IA. Por empresa o global (sin empresa).
        </Typography>

        {isLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
            <CircularProgress size={24} />
          </Box>
        )}

        {!isLoading && (
          <>
            <TextField
              label="Nombre del asistente"
              fullWidth
              size="small"
              sx={{ mb: 1 }}
              placeholder="ej. administraNET Bot"
              value={assistantName}
              onChange={(e) => setAssistantName(e.target.value)}
            />
            <TextField
              label="Mensaje de saludo / bienvenida"
              fullWidth
              multiline
              minRows={2}
              size="small"
              sx={{ mb: 1 }}
              placeholder="Opcional: texto que el asistente puede usar al presentarse"
              value={welcomeMessage}
              onChange={(e) => setWelcomeMessage(e.target.value)}
            />
            <TextField
              label="Idioma por defecto"
              fullWidth
              size="small"
              sx={{ mb: 2 }}
              placeholder="es"
              value={defaultLanguage}
              onChange={(e) => setDefaultLanguage(e.target.value)}
            />
            {saveMessage && (
              <Alert
                severity={patchMutation.isError ? 'error' : 'success'}
                sx={{ mb: 2 }}
                onClose={() => setSaveMessage(null)}
              >
                {saveMessage}
              </Alert>
            )}
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button variant="contained" onClick={handleSave} disabled={patchMutation.isPending}>
                {patchMutation.isPending ? 'Guardando…' : 'Guardar'}
              </Button>
              <Button onClick={onClose}>Cerrar</Button>
            </Box>
          </>
        )}
      </Box>
    </Drawer>
  )
}
