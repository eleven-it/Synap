import { Box, Typography } from '@mui/material'

export type SlaStatus = 'ok' | 'at_risk' | 'breached' | 'none'

export interface SlaBarProps {
  status: SlaStatus
  dueAt?: string | null
  breachedAt?: string | null
  label?: string
}

const statusConfig: Record<SlaStatus, { color: string; bg: string; label: string }> = {
  ok: { color: 'success.main', bg: 'success.light', label: 'Activo' },
  at_risk: { color: 'warning.dark', bg: 'warning.light', label: 'En riesgo' },
  breached: { color: 'error.main', bg: 'error.light', label: 'Vencido' },
  none: { color: 'text.secondary', bg: 'action.hover', label: '—' },
}

export default function SlaBar({ status, dueAt, breachedAt, label }: SlaBarProps) {
  const config = statusConfig[status]
  const displayLabel = label ?? config.label
  const sub = status === 'breached' && breachedAt
    ? new Date(breachedAt).toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' })
    : status !== 'none' && dueAt
      ? new Date(dueAt).toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' })
      : null

  return (
    <Box
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 1,
        px: 1,
        py: 0.5,
        borderRadius: 1,
        bgcolor: config.bg,
        color: config.color,
      }}
    >
      <Box
        sx={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          bgcolor: config.color,
        }}
      />
      <Typography variant="caption" fontWeight={600}>
        {displayLabel}
      </Typography>
      {sub && (
        <Typography variant="caption" sx={{ opacity: 0.9 }}>
          {sub}
        </Typography>
      )}
    </Box>
  )
}
