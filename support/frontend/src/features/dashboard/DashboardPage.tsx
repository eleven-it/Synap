import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Box, Grid, Typography } from '@mui/material'
import AssignmentIcon from '@mui/icons-material/Assignment'
import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import StackedBarChartIcon from '@mui/icons-material/StackedBarChart'
import api from '@/api/endpoints'
import { Card, StatCard, PageHeader, DataTable, Badge, SkeletonStatCard } from '@/components/ui'
import type { CaseListItem, CaseStatus } from '@/types'

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

export default function DashboardPage() {
  const navigate = useNavigate()

  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const { data: d } = await api.dashboard()
      return d
    },
  })

  const { data: atencionData, isLoading: atencionLoading } = useQuery({
    queryKey: ['cases', 'atencion', 5],
    queryFn: async () => {
      const { data: d } = await api.cases.list({
        limit: 5,
        offset: 0,
        ordering: '-updated_at',
      })
      return d
    },
  })

  if (error) {
    return (
      <Typography color="error">
        No se pudo cargar el resumen. Reintentá más tarde.
      </Typography>
    )
  }

  const rows = atencionData?.results ?? []
  const columns = [
    {
      id: 'number_display',
      label: 'Número',
      render: (row: CaseListItem) => row.number_display,
    },
    {
      id: 'status',
      label: 'Estado',
      render: (row: CaseListItem) => (
        <Badge label={STATUS_LABELS[row.status as CaseStatus] ?? row.status} variant="default" />
      ),
    },
    {
      id: 'company',
      label: 'Empresa',
      render: (row: CaseListItem) => row.company?.prefix ?? row.company?.synap_id ?? '—',
    },
    {
      id: 'sla',
      label: 'SLA',
      render: (row: CaseListItem) =>
        row.sla_breached_at ? 'Vencido' : row.sla_due_at ? 'Activo' : '—',
    },
  ]

  return (
    <Box>
      <PageHeader
        title="Dashboard"
        subtitle="Resumen del día y casos que requieren atención"
      />
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          {isLoading ? (
            <SkeletonStatCard />
          ) : (
            <StatCard
              title="Casos abiertos"
              value={data?.open_count ?? 0}
              icon={<AssignmentIcon sx={{ fontSize: 28 }} />}
            />
          )}
        </Grid>
        <Grid item xs={12} md={4}>
          {isLoading ? (
            <SkeletonStatCard />
          ) : (
            <StatCard
              title="SLA en riesgo"
              value={data?.sla_at_risk_count ?? 0}
              icon={<WarningAmberIcon sx={{ fontSize: 28 }} color="warning" />}
              badge={
                (data?.sla_at_risk_count ?? 0) > 0
                  ? { label: 'Revisar', variant: 'warning' }
                  : undefined
              }
            />
          )}
        </Grid>
        <Grid item xs={12} md={4}>
          {isLoading ? (
            <SkeletonStatCard />
          ) : (
            <StatCard
              title="Por estado"
              valueVariant="body2"
              value={
                data?.cases_by_status
                  ? Object.entries(data.cases_by_status)
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(' · ') || '—'
                  : '—'
              }
              icon={<StackedBarChartIcon sx={{ fontSize: 28 }} />}
            />
          )}
        </Grid>
        <Grid item xs={12}>
          <Card sx={{ overflow: 'hidden' }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
              Requiere atención
            </Typography>
            <DataTable<CaseListItem>
              columns={columns}
              rows={rows}
              keyField="id"
              loading={atencionLoading}
              emptyMessage="No hay casos que requieran atención"
              emptyAction={
                <Typography variant="body2" color="text.secondary">
                  Los casos recientes aparecerán aquí.
                </Typography>
              }
              onRowClick={(row) => navigate(`/casos/${row.id}`)}
            />
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
