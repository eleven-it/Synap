import { Chip, type ChipProps } from '@mui/material'

export type BadgeVariant = 'success' | 'warning' | 'error' | 'info' | 'default'

const variantMap: Record<BadgeVariant, ChipProps['color']> = {
  success: 'success',
  warning: 'warning',
  error: 'error',
  info: 'info',
  default: 'default',
}

export interface BadgeProps extends Omit<ChipProps, 'color' | 'variant'> {
  variant?: BadgeVariant
}

/**
 * Chip/Badge semántico unificado (estado de caso, SLA, etc.).
 */
export default function Badge({ variant = 'default', ...rest }: BadgeProps) {
  const chipColor = variantMap[variant]
  return (
    <Chip
      size="small"
      sx={{ borderRadius: 1, fontWeight: 500 }}
      color={chipColor}
      variant={variant === 'default' ? 'outlined' : 'filled'}
      {...rest}
    />
  )
}
