import { Box, Typography } from '@mui/material'

export interface PageHeaderProps {
  title: string
  subtitle?: string
  breadcrumbs?: React.ReactNode
  actions?: React.ReactNode
}

export default function PageHeader({ title, subtitle, breadcrumbs, actions }: PageHeaderProps) {
  return (
    <Box sx={{ mb: 3, display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: 2 }}>
      <Box>
        {breadcrumbs}
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          {title}
        </Typography>
        {subtitle && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {subtitle}
          </Typography>
        )}
      </Box>
      {actions && <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>{actions}</Box>}
    </Box>
  )
}
