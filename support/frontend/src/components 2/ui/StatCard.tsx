import { Box, Typography, type SxProps, type Theme } from '@mui/material'

export interface StatCardProps {
  title: string
  value: string | number
  icon?: React.ReactNode
  badge?: { label: string; variant?: 'success' | 'warning' | 'error' | 'info' }
  loading?: boolean
  valueVariant?: 'h4' | 'body2'
  sx?: SxProps<Theme>
}

type BadgeVariant = 'success' | 'warning' | 'error' | 'info'
const badgeSx: Record<BadgeVariant, { bgcolor: string; color: string }> = {
  success: { bgcolor: 'success.light', color: 'success.dark' },
  warning: { bgcolor: 'warning.light', color: 'warning.dark' },
  error: { bgcolor: 'error.light', color: 'error.dark' },
  info: { bgcolor: 'info.light', color: 'info.dark' },
}

export default function StatCard({ title, value, icon, badge, loading, valueVariant = 'h4', sx }: StatCardProps) {
  return (
    <Box
      sx={{
        p: 2,
        borderRadius: 2,
        border: '1px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper',
        boxShadow: (t) => t.shadows[1],
        height: '100%',
        position: 'relative',
        ...sx,
      }}
    >
      {badge && (
        <Box
          sx={{
            position: 'absolute',
            top: 12,
            right: 12,
            px: 1,
            py: 0.25,
            borderRadius: 1,
            typography: 'caption',
            fontWeight: 600,
            ...badgeSx[badge.variant ?? 'info'],
          }}
        >
          {badge.label}
        </Box>
      )}
      {icon && (
        <Box sx={{ color: 'text.secondary', mb: 1, opacity: 0.8 }}>{icon}</Box>
      )}
      <Typography variant="body2" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: '0.02em', fontWeight: 500 }}>
        {title}
      </Typography>
      {loading ? (
        <Box sx={{ height: 40, width: '60%', bgcolor: 'action.hover', borderRadius: 1, mt: 0.5 }} />
      ) : (
        <Typography variant={valueVariant} sx={{ fontWeight: 700, mt: 0.5 }}>
          {value}
        </Typography>
      )}
    </Box>
  )
}
