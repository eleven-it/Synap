import { useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Grid,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  TextField,
  Divider,
} from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSnackbar } from 'notistack'
import { useState } from 'react'
import api from '@/api/endpoints'
import type { CaseStatus } from '@/types'
import CopilotPanel from '@/features/copilot/CopilotPanel'
import { Card, Badge, SlaBar, PageHeader } from '@/components/ui'
import type { SlaStatus } from '@/components/ui/SlaBar'
import type { Message } from '@/types'
import { Skeleton } from '@/components/ui'

const STATUS_LABELS: Record<string, string> = {
  iniciado: 'Iniciado',
  en_analisis_ia: 'En análisis IA',
  esperando_respuesta_usuario: 'Esperando respuesta',
  derivado_a_humano: 'Derivado a humano',
  asignado_a_agente_humano: 'Asignado',
  en_proceso_humano: 'En proceso',
  resuelto: 'Resuelto',
  cerrado: 'Cerrado',
  reabierto: 'Reabierto',
}

function getSlaStatus(row: { sla_breached_at?: string | null; sla_due_at?: string | null }): SlaStatus {
  if (row.sla_breached_at) return 'breached'
  if (row.sla_due_at) return 'ok'
  return 'none'
}

function ChannelChip({ channel }: { channel: string }) {
  const label = channel === 'whatsapp' ? 'WhatsApp' : channel === 'telegram' ? 'Telegram' : channel === 'email' ? 'Email' : channel
  return (
    <Box
      component="span"
      sx={{
        px: 0.75,
        py: 0.25,
        borderRadius: 1,
        typography: 'caption',
        fontWeight: 600,
        bgcolor: 'action.hover',
        color: 'text.secondary',
      }}
    >
      {label}
    </Box>
  )
}

export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { enqueueSnackbar } = useSnackbar()
  const [replyText, setReplyText] = useState('')

  const caseId = id ? parseInt(id, 10) : NaN
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['case', caseId] })
    queryClient.invalidateQueries({ queryKey: ['cases'] })
  }

  const { data: caseData, isLoading: caseLoading } = useQuery({
    queryKey: ['case', caseId],
    queryFn: async () => {
      const { data } = await api.cases.get(caseId)
      return data
    },
    enabled: Number.isInteger(caseId),
  })

  const { data: timelineData, isLoading: timelineLoading } = useQuery({
    queryKey: ['case', caseId, 'timeline'],
    queryFn: async () => {
      const { data } = await api.cases.timeline(caseId)
      return data
    },
    enabled: Number.isInteger(caseId),
  })

  const patchMutation = useMutation({
    mutationFn: (payload: { status?: string; assigned_to_id?: number | null }) =>
      api.cases.patch(caseId, payload),
    onSuccess: () => {
      invalidate()
      enqueueSnackbar('Caso actualizado', { variant: 'success' })
    },
    onError: (e: { response?: { data?: { message?: string } } }) => {
      enqueueSnackbar(e.response?.data?.message || 'Error al actualizar', { variant: 'error' })
    },
  })

  const sendMutation = useMutation({
    mutationFn: (texto: string) => api.cases.responseSend(caseId, texto),
    onSuccess: () => {
      setReplyText('')
      invalidate()
      queryClient.invalidateQueries({ queryKey: ['case', caseId, 'timeline'] })
      enqueueSnackbar('Respuesta enviada', { variant: 'success' })
    },
    onError: (e: { response?: { data?: { message?: string } } }) => {
      enqueueSnackbar(e.response?.data?.message || 'Error al enviar', { variant: 'error' })
    },
  })

  const case_ = caseData
  const timeline = timelineData

  if (!Number.isInteger(caseId)) {
    navigate('/casos')
    return null
  }

  return (
    <Box>
      <PageHeader
        title={`Caso ${case_?.number_display ?? id}`}
        subtitle="Contexto, timeline y copiloto IA"
        actions={
          <Button
            size="small"
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/casos')}
          >
            Volver a casos
          </Button>
        }
      />
      <Grid container spacing={3}>
        {/* Columna 1: Contexto */}
        <Grid item xs={12} md={3}>
          <Card sx={{ height: '100%' }}>
            {caseLoading ? (
              <Skeleton variant="rounded" height={280} />
            ) : case_ ? (
              <>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  {case_.number_display}
                </Typography>
                <Box sx={{ mt: 1 }}>
                  <Badge label={STATUS_LABELS[case_.status] ?? case_.status} variant="default" />
                </Box>
                <Box sx={{ mt: 2 }}>
                  <Typography variant="caption" color="text.secondary" display="block">
                    Empresa
                  </Typography>
                  <Typography variant="body2">
                    {case_.company?.prefix ?? case_.company?.synap_id ?? '—'}
                  </Typography>
                </Box>
                <Box sx={{ mt: 1 }}>
                  <Typography variant="caption" color="text.secondary" display="block">
                    Asignado
                  </Typography>
                  <Typography variant="body2">
                    {case_.assigned_to?.username ?? 'Sin asignar'}
                  </Typography>
                </Box>
                <Box sx={{ mt: 1 }}>
                  <Typography variant="caption" color="text.secondary" display="block">
                    SLA
                  </Typography>
                  <SlaBar
                    status={getSlaStatus(case_)}
                    dueAt={case_.sla_due_at}
                    breachedAt={case_.sla_breached_at}
                  />
                </Box>
                <Divider sx={{ my: 2 }} />
                <FormControl fullWidth size="small">
                  <InputLabel>Estado</InputLabel>
                  <Select
                    value={case_.status}
                    label="Estado"
                    onChange={(e) => patchMutation.mutate({ status: e.target.value as CaseStatus })}
                    disabled={patchMutation.isPending}
                    sx={{ borderRadius: 2 }}
                  >
                    {(Object.keys(STATUS_LABELS) as string[]).map((s) => (
                      <MenuItem key={s} value={s}>{STATUS_LABELS[s]}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </>
            ) : (
              <Typography color="error">Caso no encontrado</Typography>
            )}
          </Card>
        </Grid>

        {/* Columna 2: Timeline + Respuesta */}
        <Grid item xs={12} md={5}>
          <Card sx={{ display: 'flex', flexDirection: 'column', maxHeight: 640 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
              Timeline
            </Typography>
            <Box sx={{ flex: 1, overflow: 'auto', minHeight: 200 }}>
              {timelineLoading ? (
                <Skeleton variant="rounded" height={300} />
              ) : (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  {(timeline?.messages ?? []).map((m: Message) => (
                    <Box
                      key={m.id}
                      sx={{
                        alignSelf: m.direction === 'outbound' ? 'flex-end' : 'flex-start',
                        maxWidth: '85%',
                        p: 1.5,
                        borderRadius: 2,
                        bgcolor: m.direction === 'outbound' ? 'primary.main' : 'action.hover',
                        color: m.direction === 'outbound' ? 'primary.contrastText' : 'text.primary',
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                        <ChannelChip channel={m.channel_type} />
                        <Typography variant="caption" sx={{ opacity: 0.9 }}>
                          {new Date(m.created_at).toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' })}
                        </Typography>
                      </Box>
                      <Typography variant="body2">{m.content}</Typography>
                    </Box>
                  ))}
                  {(timeline?.summaries ?? []).map((s) => (
                    <Box
                      key={s.id}
                      sx={{
                        p: 1.5,
                        borderRadius: 2,
                        bgcolor: 'action.hover',
                        border: '1px solid',
                        borderColor: 'divider',
                      }}
                    >
                      <Typography variant="caption" color="text.secondary">
                        Resumen IA
                      </Typography>
                      <Typography variant="body2">{s.summary_text}</Typography>
                    </Box>
                  ))}
                  {(timeline?.messages?.length ?? 0) === 0 && (timeline?.summaries?.length ?? 0) === 0 && (
                    <Typography color="text.secondary" variant="body2">
                      Sin mensajes aún
                    </Typography>
                  )}
                </Box>
              )}
            </Box>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
              Responder
            </Typography>
            <TextField
              fullWidth
              multiline
              minRows={2}
              placeholder="Escribí tu respuesta…"
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              sx={{ mb: 1, '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
            />
            <Button
              variant="contained"
              endIcon={<SendIcon />}
              onClick={() => replyText.trim() && sendMutation.mutate(replyText.trim())}
              disabled={!replyText.trim() || sendMutation.isPending}
              sx={{ borderRadius: 2 }}
            >
              Enviar
            </Button>
          </Card>
        </Grid>

        {/* Columna 3: Copiloto IA */}
        <Grid item xs={12} md={4}>
          <CopilotPanel caseId={caseId} />
        </Grid>
      </Grid>
    </Box>
  )
}
