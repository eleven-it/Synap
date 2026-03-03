import { useState } from 'react'
import { Box, Grid, FormControl, InputLabel, Select, MenuItem } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import api from '@/api/endpoints'
import { PageHeader, StatCard, SkeletonStatCard } from '@/components/ui'
import TimelineIcon from '@mui/icons-material/Timeline'
import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import PercentIcon from '@mui/icons-material/Percent'

export default function MetricsPage() {
  const [companyId, setCompanyId] = useState<number | ''>('')
  const desde = new Date()
  desde.setDate(desde.getDate() - 30)
  const hasta = new Date()

  const { data: metrics, isLoading } = useQuery({
    queryKey: ['metrics', companyId, desde.toISOString().slice(0, 10), hasta.toISOString().slice(0, 10)],
    queryFn: async () => {
      const { data } = await api.metrics({
        desde_fecha: desde.toISOString().slice(0, 10),
        hasta_fecha: hasta.toISOString().slice(0, 10),
        ...(companyId ? { empresa_id: Number(companyId) } : {}),
      })
      return data
    },
  })

  return (
    <Box>
      <PageHeader
        title="Métricas"
        subtitle="SLA y casos resueltos en el período"
        actions={
          <FormControl size="small" sx={{ minWidth: 200 }} variant="outlined">
            <InputLabel id="metrics-empresa">Empresa</InputLabel>
            <Select
              labelId="metrics-empresa"
              value={companyId}
              label="Empresa"
              onChange={(e) => setCompanyId(e.target.value === '' ? '' : Number(e.target.value))}
              sx={{ borderRadius: 2 }}
            >
              <MenuItem value="">Todas</MenuItem>
            </Select>
          </FormControl>
        }
      />
      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}>
          {isLoading ? (
            <SkeletonStatCard />
          ) : (
            <StatCard
              title="SLA inicios"
              value={metrics?.sla_inicios ?? 0}
              icon={<TimelineIcon sx={{ fontSize: 28 }} />}
            />
          )}
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          {isLoading ? (
            <SkeletonStatCard />
          ) : (
            <StatCard
              title="SLA vencidos"
              value={metrics?.sla_vencidos ?? 0}
              icon={<WarningAmberIcon sx={{ fontSize: 28 }} color="error" />}
              badge={(metrics?.sla_vencidos ?? 0) > 0 ? { label: 'Revisar', variant: 'error' } : undefined}
            />
          )}
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          {isLoading ? (
            <SkeletonStatCard />
          ) : (
            <StatCard
              title="Casos resueltos"
              value={metrics?.casos_resueltos ?? 0}
              icon={<CheckCircleIcon sx={{ fontSize: 28 }} color="success" />}
            />
          )}
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          {isLoading ? (
            <SkeletonStatCard />
          ) : (
            <StatCard
              title="Cumplimiento SLA %"
              value={`${metrics?.sla_cumplimiento_pct ?? 0}%`}
              icon={<PercentIcon sx={{ fontSize: 28 }} />}
            />
          )}
        </Grid>
      </Grid>
    </Box>
  )
}
