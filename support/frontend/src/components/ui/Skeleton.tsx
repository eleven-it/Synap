import { Box, Skeleton as MuiSkeleton, type SkeletonProps } from '@mui/material'

/** Skeleton para líneas de texto. */
export function SkeletonText({ lines = 3, ...rest }: SkeletonProps & { lines?: number }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {Array.from({ length: lines }).map((_, i) => (
        <MuiSkeleton key={i} variant="text" width={i === lines - 1 && lines > 1 ? '60%' : '100%'} {...rest} />
      ))}
    </Box>
  )
}

/** Skeleton para una fila de tabla. */
export function SkeletonTableRow({ cols = 5 }: { cols?: number }) {
  return (
    <Box sx={{ display: 'flex', gap: 2, p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
      {Array.from({ length: cols }).map((_, i) => (
        <MuiSkeleton key={i} variant="rounded" height={24} sx={{ flex: 1 }} />
      ))}
    </Box>
  )
}

/** Skeleton para una card de estadística. */
export function SkeletonStatCard() {
  return (
    <Box sx={{ p: 2, borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
      <MuiSkeleton variant="text" width="40%" height={20} />
      <MuiSkeleton variant="text" width="60%" height={36} sx={{ mt: 1 }} />
    </Box>
  )
}

export default MuiSkeleton
