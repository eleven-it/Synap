import { Paper, type PaperProps } from '@mui/material'

/**
 * Card/Panel Kora-like: sombra suave, radius y borde sutil.
 * Usar para contenedores de contenido (dashboard, detalle caso, configuración).
 */
export default function Card({ children, sx, ...rest }: PaperProps) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        borderRadius: 2,
        border: '1px solid',
        borderColor: 'divider',
        boxShadow: (t) => t.shadows[1],
        ...sx,
      }}
      {...rest}
    >
      {children}
    </Paper>
  )
}
