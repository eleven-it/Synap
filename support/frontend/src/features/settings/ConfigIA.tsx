import { useEffect, useState, useRef } from 'react'
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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Paper,
  List,
  ListItem,
  ListItemText,
  ToggleButtonGroup,
  ToggleButton,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import SendIcon from '@mui/icons-material/Send'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/api/endpoints'
import type { IAConfig } from '@/types'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

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
  const [chatModalOpen, setChatModalOpen] = useState(false)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatSistema, setChatSistema] = useState<'' | 'synap' | 'administranet'>('')
  const chatEndRef = useRef<HTMLDivElement>(null)

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

  const chatMutation = useMutation({
    mutationFn: ({ texto, sistema }: { texto: string; sistema?: 'synap' | 'administranet' }) =>
      api.copiloto.mensaje(texto, sistema),
    onSuccess: (res, { texto }) => {
      setChatMessages((prev) => [
        ...prev,
        { role: 'user', content: texto },
        { role: 'assistant', content: res?.data?.respuesta_ia ?? '' },
      ])
      setChatInput('')
    },
    onError: (err: { response?: { data?: { message?: string; detail?: string } } }) => {
      setChatMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: err.response?.data?.message || err.response?.data?.detail || 'Error al obtener respuesta del modelo.',
        },
      ])
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
    setChatMessages([])
    setChatModalOpen(true)
  }

  const handleSendChat = () => {
    const texto = chatInput.trim()
    if (!texto || chatMutation.isPending) return
    chatMutation.mutate({ texto, sistema: chatSistema || undefined })
  }

  const handleCloseChatModal = () => {
    setChatModalOpen(false)
    setChatMessages([])
    setChatInput('')
  }

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

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
                disabled={!provider.trim() || !model.trim()}
              >
                Probar LLM
              </Button>
              <Button variant="contained" onClick={handleSave} disabled={patchMutation.isPending}>
                {patchMutation.isPending ? 'Guardando…' : 'Guardar'}
              </Button>
              <Button onClick={onClose}>Cerrar</Button>
            </Box>
          </>
        )}
      </Box>

      <Dialog
        open={chatModalOpen}
        onClose={handleCloseChatModal}
        maxWidth="sm"
        fullWidth
        PaperProps={{ sx: { maxHeight: '85vh' } }}
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span>Probar modelo</span>
          <IconButton onClick={handleCloseChatModal} aria-label="Cerrar" size="small">
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers sx={{ p: 0, display: 'flex', flexDirection: 'column', minHeight: 320 }}>
          <Typography variant="body2" color="text.secondary" sx={{ px: 2, py: 1 }}>
            Conversá con el modelo para probar la configuración. Guardá los cambios antes si acabás de editar.
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ px: 2, pt: 0.5 }}>
            Pregunta sobre:
          </Typography>
          <Box sx={{ px: 2, py: 1 }}>
            <ToggleButtonGroup
              value={chatSistema}
              exclusive
              onChange={(_, v: '' | 'synap' | 'administranet' | null) => v != null && setChatSistema(v)}
              size="small"
            >
              <ToggleButton value="">Ambos</ToggleButton>
              <ToggleButton value="synap">Synap</ToggleButton>
              <ToggleButton value="administranet">AdministraNET (VB6)</ToggleButton>
            </ToggleButtonGroup>
          </Box>
          <Paper variant="outlined" sx={{ flex: 1, m: 2, overflow: 'auto', minHeight: 200 }}>
            <List dense sx={{ py: 1 }}>
              {chatMessages.length === 0 && (
                <ListItem>
                  <ListItemText
                    primary="Escribí un mensaje y pulsá Enviar para probar."
                    primaryTypographyProps={{ variant: 'body2', color: 'text.secondary' }}
                  />
                </ListItem>
              )}
              {chatMessages.map((msg, i) => (
                <ListItem key={i} alignItems="flex-start" sx={{ flexDirection: 'column', alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                  <Typography variant="caption" color="text.secondary">
                    {msg.role === 'user' ? 'Vos' : 'Modelo'}
                  </Typography>
                  <ListItemText
                    primary={msg.content}
                    primaryTypographyProps={{ variant: 'body2', sx: { whiteSpace: 'pre-wrap' } }}
                    sx={{ maxWidth: '100%' }}
                  />
                </ListItem>
              ))}
              <div ref={chatEndRef} />
            </List>
          </Paper>
          <Box sx={{ display: 'flex', gap: 1, p: 2, pt: 0 }}>
            <TextField
              placeholder="Escribí un mensaje…"
              size="small"
              fullWidth
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSendChat())}
              disabled={chatMutation.isPending}
            />
            <Button
              variant="contained"
              onClick={handleSendChat}
              disabled={!chatInput.trim() || chatMutation.isPending}
              endIcon={chatMutation.isPending ? <CircularProgress size={16} /> : <SendIcon />}
            >
              Enviar
            </Button>
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 2, py: 1 }}>
          <Button onClick={handleCloseChatModal}>Cerrar</Button>
        </DialogActions>
      </Dialog>
    </Drawer>
  )
}
