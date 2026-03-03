import { useState } from 'react'
import { Box, Typography, TextField, Button, FormControlLabel, Checkbox, ToggleButtonGroup, ToggleButton } from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSnackbar } from 'notistack'
import api from '@/api/endpoints'
import { Card } from '@/components/ui'

type SistemaRAG = '' | 'synap' | 'administranet'

interface CopilotPanelProps {
  caseId: number
}

export default function CopilotPanel({ caseId }: CopilotPanelProps) {
  const [input, setInput] = useState('')
  const [saveAsKnowledge, setSaveAsKnowledge] = useState(false)
  const [sistema, setSistema] = useState<SistemaRAG>('')
  const queryClient = useQueryClient()
  const { enqueueSnackbar } = useSnackbar()

  const { data: messagesData } = useQuery({
    queryKey: ['case', caseId, 'copilot'],
    queryFn: async () => {
      const { data } = await api.cases.copilotMessages(caseId)
      return data
    },
    enabled: Number.isInteger(caseId),
  })

  const postMutation = useMutation({
    mutationFn: (texto: string) =>
      api.cases.copilotPost(caseId, texto, saveAsKnowledge, sistema || undefined),
    onSuccess: (res) => {
      setInput('')
      queryClient.invalidateQueries({ queryKey: ['case', caseId, 'copilot'] })
      const payload = res?.data
      if (payload?.guardado_como_conocimiento) {
        enqueueSnackbar('Respuesta guardada como conocimiento', { variant: 'success' })
      }
    },
    onError: (e: { response?: { data?: { message?: string } } }) => {
      enqueueSnackbar(e.response?.data?.message || 'Error al enviar', { variant: 'error' })
    },
  })

  const messages = messagesData?.messages ?? []

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 400 }}>
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
        Copiloto IA
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
        Chat agente ↔ IA para este caso
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
        Pregunta sobre:
      </Typography>
      <ToggleButtonGroup
        value={sistema}
        exclusive
        onChange={(_, v: SistemaRAG | null) => v != null && setSistema(v)}
        size="small"
        sx={{ mb: 2 }}
      >
        <ToggleButton value="">Ambos</ToggleButton>
        <ToggleButton value="synap">Synap</ToggleButton>
        <ToggleButton value="administranet">AdministraNET (VB6)</ToggleButton>
      </ToggleButtonGroup>
      <Box sx={{ flex: 1, overflow: 'auto', mb: 2 }}>
        {messages.map((m) => (
          <Box
            key={m.id}
            sx={{
              p: 1.5,
              mb: 1,
              borderRadius: 2,
              bgcolor: m.role === 'assistant' ? 'action.hover' : 'primary.main',
              color: m.role === 'assistant' ? 'text.primary' : 'primary.contrastText',
            }}
          >
            <Typography variant="caption" sx={{ opacity: 0.9 }}>
              {m.role === 'user' ? 'Tú' : 'IA'}
              {m.saved_to_knowledge && ' · Guardado como conocimiento'}
            </Typography>
            <Typography variant="body2" sx={{ mt: 0.5 }}>{m.content}</Typography>
          </Box>
        ))}
        {messages.length === 0 && (
          <Typography color="text.secondary" variant="body2">
            Escribí una pregunta para el copiloto (ej. cómo redactar la respuesta).
          </Typography>
        )}
      </Box>
      <Box
        sx={{
          py: 1,
          px: 1.5,
          borderRadius: 2,
          bgcolor: 'action.hover',
          border: '1px solid',
          borderColor: 'divider',
          mb: 2,
        }}
      >
        <FormControlLabel
          control={
            <Checkbox
              checked={saveAsKnowledge}
              onChange={(e) => setSaveAsKnowledge(e.target.checked)}
              size="small"
            />
          }
          label="Guardar respuesta como conocimiento"
        />
      </Box>
      <TextField
        fullWidth
        size="small"
        placeholder="Pregunta al copiloto…"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            if (input.trim()) postMutation.mutate(input.trim())
          }
        }}
        sx={{ mb: 1, '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
      />
      <Button
        variant="contained"
        endIcon={<SendIcon />}
        onClick={() => input.trim() && postMutation.mutate(input.trim())}
        disabled={!input.trim() || postMutation.isPending}
        sx={{ borderRadius: 2 }}
      >
        Enviar
      </Button>
    </Card>
  )
}
