import {
  Box,
  Typography,
  Grid,
  Button,
  Switch,
  FormControlLabel,
} from '@mui/material'
import SettingsIcon from '@mui/icons-material/Settings'
import ScienceIcon from '@mui/icons-material/Science'
import StorageIcon from '@mui/icons-material/Storage'
import SecurityIcon from '@mui/icons-material/Security'
import NotificationsIcon from '@mui/icons-material/Notifications'
import PaletteIcon from '@mui/icons-material/Palette'
import TimelineIcon from '@mui/icons-material/Timeline'
import PsychologyIcon from '@mui/icons-material/Psychology'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSnackbar } from 'notistack'
import api from '@/api/endpoints'
import { useAuth } from '@/features/auth/useAuth'
import ConfigCanales from './ConfigCanales'
import ConfigIA from './ConfigIA'
import ConfigRAG from './ConfigRAG'
import ConfigSLA from './ConfigSLA'
import ConfigStorage from './ConfigStorage'
import ConfigSeguridad from './ConfigSeguridad'
import ConfigNotificaciones from './ConfigNotificaciones'
import ConfigBranding from './ConfigBranding'
import { Card, Badge, PageHeader } from '@/components/ui'

type ConfigStatus = 'no_configurado' | 'parcial' | 'validando' | 'activo' | 'error'

interface ConfigCardProps {
  title: string
  description: string
  status: ConfigStatus
  lastCheck?: string
  lastError?: string
  onConfigure: () => void
  onTest?: () => void
  canActivate?: boolean
  active?: boolean
  onToggleActive?: (v: boolean) => void
  toggleDisabled?: boolean
  icon: React.ReactNode
}

const statusVariant: Record<ConfigStatus, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
  no_configurado: 'default',
  parcial: 'info',
  validando: 'info',
  activo: 'success',
  error: 'error',
}

function ConfigCard({
  title,
  description,
  status,
  lastCheck,
  lastError,
  onConfigure,
  onTest,
  canActivate,
  active,
  onToggleActive,
  toggleDisabled,
  icon,
}: ConfigCardProps) {
  const statusLabel = {
    no_configurado: 'No configurado',
    parcial: 'Parcial',
    validando: 'Validando',
    activo: 'Activo',
    error: 'Error',
  }[status]

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <Box sx={{ color: 'text.secondary' }}>{icon}</Box>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          {title}
        </Typography>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, flex: 1 }}>
        {description}
      </Typography>
      <Box sx={{ mb: 1.5 }}>
        <Badge label={statusLabel} variant={statusVariant[status]} />
      </Box>
      {lastCheck && (
        <Typography variant="caption" display="block" color="text.secondary" sx={{ mb: 0.5 }}>
          Último check: {lastCheck}
        </Typography>
      )}
      {lastError && (
        <Typography variant="caption" color="error" display="block" sx={{ mb: 0.5 }}>
          {lastError}
        </Typography>
      )}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 'auto', pt: 2 }}>
        <Button size="small" variant="outlined" onClick={onConfigure} sx={{ borderRadius: 2 }}>
          {status === 'no_configurado' ? 'Configurar' : 'Editar'}
        </Button>
        {onTest && (
          <Button size="small" variant="outlined" onClick={onTest} sx={{ borderRadius: 2 }}>
            Probar
          </Button>
        )}
        {canActivate && onToggleActive != null && (
          <FormControlLabel
            control={
              <Switch
                size="small"
                checked={active ?? false}
                disabled={toggleDisabled}
                onChange={(_, v) => onToggleActive(v)}
              />
            }
            label="Activo"
          />
        )}
      </Box>
    </Card>
  )
}

export default function SettingsPage() {
  const [drawer, setDrawer] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const { enqueueSnackbar } = useSnackbar()
  const { isAdmin } = useAuth()
  const { data: iaList } = useQuery({
    queryKey: ['config', 'ia', null],
    queryFn: async () => {
      const { data } = await api.config.ia.list(undefined)
      return data
    },
  })
  const iaConfig = Array.isArray(iaList) && iaList.length > 0 ? iaList[0] : null
  const iaStatus: ConfigStatus = !iaConfig ? 'no_configurado' : iaConfig.status === 'active' ? 'activo' : 'parcial'
  const iaActive = iaConfig?.status === 'active'

  const iaToggleMutation = useMutation({
    mutationFn: (active: boolean) =>
      api.config.ia.patch({
        company_id: iaConfig?.company_id ?? null,
        status: active ? 'active' : 'draft',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config', 'ia'] })
      enqueueSnackbar('Estado de IA / Modelos actualizado', { variant: 'success' })
    },
    onError: (err: { response?: { data?: { message?: string } } }) => {
      enqueueSnackbar(err.response?.data?.message || 'Error al actualizar el estado', { variant: 'error' })
    },
  })

  const handleIAToggle = (active: boolean) => {
    if (!iaConfig) {
      setDrawer('ia')
      return
    }
    iaToggleMutation.mutate(active)
  }

  const { data: channelsResponse } = useQuery({
    queryKey: ['config', 'channels'],
    queryFn: async () => {
      const { data } = await api.config.channels.list()
      return data
    },
  })
  const channelsList = channelsResponse?.results ?? []
  const channelsStatus: ConfigStatus =
    channelsList.length === 0
      ? 'no_configurado'
      : channelsList.some((c) => c.status === 'active')
        ? 'activo'
        : channelsList.some((c) => c.status === 'validating')
          ? 'validando'
          : channelsList.some((c) => c.status === 'error')
            ? 'error'
            : 'parcial'
  const channelsActive = channelsList.some((c) => c.status === 'active')
  const firstChannelId = channelsList[0]?.id
  const firstActiveChannelId = channelsList.find((c) => c.status === 'active')?.id

  const channelToggleMutation = useMutation({
    mutationFn: ({ active, id }: { active: boolean; id: number }) =>
      active ? api.config.channels.activate(id) : api.config.channels.deactivate(id),
    onSuccess: (_, { active }) => {
      queryClient.invalidateQueries({ queryKey: ['config', 'channels'] })
      enqueueSnackbar(active ? 'Canal activado' : 'Canal desactivado', { variant: 'success' })
    },
    onError: (err: { response?: { data?: { message?: string } } }) => {
      enqueueSnackbar(err.response?.data?.message || 'Error al actualizar el canal', { variant: 'error' })
    },
  })

  const handleChannelsToggle = (active: boolean) => {
    if (channelsList.length === 0) {
      setDrawer('canales')
      return
    }
    if (active) {
      const idToActivate = channelsList.find((c) => c.status !== 'active')?.id ?? firstChannelId
      if (idToActivate != null) channelToggleMutation.mutate({ active: true, id: idToActivate })
    } else {
      if (firstActiveChannelId != null) channelToggleMutation.mutate({ active: false, id: firstActiveChannelId })
    }
  }

  const closeDrawer = () => setDrawer(null)

  if (!isAdmin) {
    return (
      <Box>
        <PageHeader title="Configuración" />
        <Typography color="text.secondary">
          Solo los usuarios con rol <strong>Administrador</strong> pueden ver y editar la configuración. Pedile a un administrador que asigne ese rol a tu usuario (Admin → Perfiles de agente).
        </Typography>
      </Box>
    )
  }

  return (
    <Box>
      <PageHeader
        title="Configuración"
        subtitle="Canales, IA, RAG, SLA, almacenamiento y seguridad. No es necesario editar archivos .env para operar."
      />
      <Grid container spacing={3}>
        <Grid item xs={12} md={6} lg={4}>
          <ConfigCard
            title="Canales"
            description="WhatsApp Meta, Telegram, Email SMTP/IMAP. Wizards guiados por canal."
            status={channelsStatus}
            onConfigure={() => setDrawer('canales')}
            onTest={
              firstChannelId != null
                ? () =>
                    api.config.channels
                      .test(firstChannelId)
                      .then((res) => {
                        const data = res?.data
                        queryClient.invalidateQueries({ queryKey: ['config', 'channels'] })
                        enqueueSnackbar(
                          data?.success ? (data?.message || 'Prueba correcta') : (data?.message || 'Error en la prueba'),
                          { variant: data?.success ? 'success' : 'error' }
                        )
                      })
                      .catch(() => enqueueSnackbar('Error al ejecutar la prueba', { variant: 'error' }))
                : undefined
            }
            canActivate
            active={channelsActive}
            onToggleActive={handleChannelsToggle}
            toggleDisabled={channelToggleMutation.isPending}
            icon={<SettingsIcon />}
          />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <ConfigCard
            title="IA / Modelos"
            description="Proveedor, API Key, modelo, límites. Activar para que el copiloto use OpenAI."
            status={iaStatus}
            onConfigure={() => setDrawer('ia')}
            onTest={() => {}}
            canActivate
            active={iaActive}
            onToggleActive={handleIAToggle}
            toggleDisabled={iaToggleMutation.isPending}
            icon={<PsychologyIcon />}
          />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <ConfigCard
            title="RAG / Conocimiento"
            description="Fuentes, top_k, política global+empresa, cache. Reindexar e ingestar."
            status="no_configurado"
            onConfigure={() => setDrawer('rag')}
            onTest={() => {}}
            icon={<ScienceIcon />}
          />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <ConfigCard
            title="SLA"
            description="Tiempo de respuesta por empresa y tipo. Warning 70–80%. Escalamiento."
            status="no_configurado"
            onConfigure={() => setDrawer('sla')}
            onTest={() => {}}
            icon={<TimelineIcon />}
          />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <ConfigCard
            title="Storage / Adjuntos"
            description="S3/MinIO: endpoint, bucket, credenciales. Tamaño y tipos permitidos."
            status="no_configurado"
            onConfigure={() => setDrawer('storage')}
            onTest={() => {}}
            icon={<StorageIcon />}
          />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <ConfigCard
            title="Seguridad operativa"
            description="Rate limits, anti-spam, política PII. Self-check."
            status="no_configurado"
            onConfigure={() => setDrawer('seguridad')}
            onTest={() => {}}
            icon={<SecurityIcon />}
          />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <ConfigCard
            title="Notificaciones y escalamiento"
            description="Gerencia/supervisores, mensajes SLA, canal de alertas."
            status="no_configurado"
            onConfigure={() => setDrawer('notificaciones')}
            icon={<NotificationsIcon />}
          />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <ConfigCard
            title="Branding / Mensajes"
            description="Nombre del asistente, saludo por empresa, idioma."
            status="no_configurado"
            onConfigure={() => setDrawer('branding')}
            icon={<PaletteIcon />}
          />
        </Grid>
      </Grid>

      {drawer === 'canales' && <ConfigCanales open onClose={closeDrawer} />}
      {drawer === 'ia' && <ConfigIA open onClose={closeDrawer} />}
      {drawer === 'rag' && <ConfigRAG open onClose={closeDrawer} />}
      {drawer === 'sla' && <ConfigSLA open onClose={closeDrawer} />}
      {drawer === 'storage' && <ConfigStorage open onClose={closeDrawer} />}
      {drawer === 'seguridad' && <ConfigSeguridad open onClose={closeDrawer} />}
      {drawer === 'notificaciones' && <ConfigNotificaciones open onClose={closeDrawer} />}
      {drawer === 'branding' && <ConfigBranding open onClose={closeDrawer} />}
    </Box>
  )
}
