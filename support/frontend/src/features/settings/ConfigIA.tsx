import { useEffect, useState } from 'react'
import {
  Drawer,
  Typography,
  Box,
  IconButton,
  TextField,
  Button,
  Alert,
  FormControlLabel,
  Switch,
  CircularProgress,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/api/endpoints'
import type { IAConfig } from '@/types'

interface ConfigIAProps {
  open: boolean
  onClose: () => void
  companyId?: number | null
}

export default function ConfigIA({ open, onClose, companyId = null }: ConfigIAProps) {
  const queryClient = useQueryClient()
  const [provider, setProvider] = useState('')
  const [model, setModel] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [maxTokens, setMaxTokens] = useState<string>('1024')
  const [status, setStatus] = useState<string>('draft')
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
  const [testMessage, setTestMessage] = useState<string | null>(null)

  const { data: list, isLoading } = useQuery({
    queryKey: ['config', 'ia', companyId],
    queryFn: async () => {
      const { data } = await api.config.ia.list(companyId ?? undefined)
      return data
    },
    enabled: open,
  })

  const config: IAConfig | null = Array.isArray(list) && list.length > 0 ? list[0] : null

  useEffect(() => {
    if (config) {
      setProvider(config.provider || '')
      setModel(config.model || '')
      setApiKey('')
      setMaxTokens(String((config.limits_json as { max_tokens?: number })?.max_tokens ?? 1024))
      setStatus(config.status || 'draft')
    } else if (!isLoading && open) {
      setProvider('')
      setModel('gpt-4o-mini')
      setApiKey('')
      setMaxTokens('1024')
      setStatus('draft')
    }
  }, [config, isLoading, open])

  const patchMutation = useMutation({
    mutationFn: (payload: Parameters<typeof api.config.ia.patch>[0]) => api.config.ia.patch(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config', 'ia'] })
      setSaveMessage('Configuración guardada. El copiloto usará esta IA cuando el estado sea Activo.')
      setApiKey('')
    },
    onError: (err: { response?: { data?: { message?: string } } }) => {
      setSaveMessage(err.response?.data?.message || 'Error al guardar.')
    },
  })

  const testMutation = useMutation({
    mutationFn: () => api.config.ia.test(companyId ?? undefined),
    onSuccess: (res) => {
      const data = res?.data
      setTestMessage(data?.success ? 'Conexión con el proveedor correcta.' : (data?.message || 'Error en la prueba.'))
    },
    onError: (err: { response?: { data?: { message?: string } } }): void => {
      setTestMessage(err.response?.data?.message || 'Error al probar.')
    },
  })

  const handleSave = () => {
    setSaveMessage(null)
    setTestMessage(null)
    const payload: Parameters<typeof api.config.ia.patch>[0] = {
      company_id: companyId ?? null,
      provider: provider.trim() || undefined,
      model: model.trim() || undefined,
      status: status || undefined,
      limits_json: { max_tokens: parseInt(maxTokens, 10) || 1024 },
    }
    if (apiKey.trim()) payload.api_key = apiKey.trim()
    patchMutation.mutate(payload)
  }

  const handleTest = () => {
    setTestMessage(null)
    if (!provider.trim() || !model.trim()) {
      setTestMessage('Indique proveedor y modelo y guarde antes de probar.')
      return
    }
    testMutation.mutate()
  }

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{ sx: { width: { xs: '100%', sm: 420 } } }}
    >
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">IA / Modelos</Typography>
          <IconButton onClick={onClose} aria-label="Cerrar">
            <CloseIcon />
          </IconButton>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Configure el proveedor (p. ej. OpenAI) para que el copiloto genere respuestas. Sin configuración activa se muestra un mensaje en el chat.
        </Typography>

        {isLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
            <CircularProgress size={24} />
          </Box>
        )}

        {!isLoading && (
          <>
            <TextField
              label="Proveedor"
              fullWidth
              size="small"
              sx={{ mb: 1 }}
              placeholder="openai"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
            />
            <TextField
              label="Modelo"
              fullWidth
              size="small"
              sx={{ mb: 1 }}
              placeholder="gpt-4o-mini, gpt-4o"
              value={model}
              onChange={(e) => setModel(e.target.value)}
            />
            <TextField
              label="API Key"
              type="password"
              fullWidth
              size="small"
              sx={{ mb: 1 }}
              placeholder={config?.api_key_masked ? config.api_key_masked : 'sk-...'}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              helperText="Dejar vacío para no cambiar la actual"
            />
            <TextField
              label="Límite tokens"
              type="number"
              fullWidth
              size="small"
              sx={{ mb: 2 }}
              value={maxTokens}
              onChange={(e) => setMaxTokens(e.target.value)}
              inputProps={{ min: 256, max: 4096 }}
            />
            <FormControlLabel
              control={
                <Switch
                  checked={status === 'active'}
                  onChange={(_, checked) => setStatus(checked ? 'active' : 'draft')}
                />
              }
              label="Activo (el copiloto usará esta configuración)"
              sx={{ mb: 2, display: 'block' }}
            />
            {saveMessage && (
              <Alert severity={patchMutation.isError ? 'error' : 'success'} sx={{ mb: 2 }} onClose={() => setSaveMessage(null)}>
                {saveMessage}
              </Alert>
            )}
            {testMessage && (
              <Alert severity={testMutation.isError ? 'error' : 'info'} sx={{ mb: 2 }} onClose={() => setTestMessage(null)}>
                {testMessage}
              </Alert>
            )}
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Button
                variant="outlined"
                onClick={handleTest}
                disabled={testMutation.isPending || !provider.trim() || !model.trim()}
              >
                {testMutation.isPending ? 'Probando…' : 'Probar LLM'}
              </Button>
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
