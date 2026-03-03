import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, FormControl, InputLabel, Select, MenuItem } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import api from '@/api/endpoints'
import type { CaseListItem, CaseStatus } from '@/types'
import { PageHeader, DataTable, Badge, SlaBar } from '@/components/ui'
import type { SlaStatus } from '@/components/ui/SlaBar'

const STATUS_LABELS: Record<CaseStatus, string> = {
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

function getSlaStatus(row: CaseListItem): SlaStatus {
  if (row.sla_breached_at) return 'breached'
  if (row.sla_due_at) return 'ok'
  return 'none'
}

export default function CasesListPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(20)
  const [statusFilter, setStatusFilter] = useState<string>('')

  const { data, isLoading } = useQuery({
    queryKey: ['cases', page, rowsPerPage, statusFilter],
    queryFn: async () => {
      const { data: d } = await api.cases.list({
        limit: rowsPerPage,
        offset: page * rowsPerPage,
        ordering: '-created_at',
        ...(statusFilter ? { status: statusFilter } : {}),
      })
      return d
    },
  })

  const rows = data?.results ?? []
  const columns = [
    { id: 'number_display', label: 'Número', render: (r: CaseListItem) => r.number_display },
    {
      id: 'status',
      label: 'Estado',
      render: (r: CaseListItem) => (
        <Badge label={STATUS_LABELS[r.status as CaseStatus] ?? r.status} variant="default" />
      ),
    },
    {
      id: 'company',
      label: 'Empresa',
      render: (r: CaseListItem) => r.company?.prefix ?? r.company?.synap_id ?? '—',
    },
    {
      id: 'assigned_to',
      label: 'Asignado',
      render: (r: CaseListItem) => r.assigned_to?.username ?? '—',
    },
    {
      id: 'sla',
      label: 'SLA',
      render: (r: CaseListItem) => (
        <SlaBar
          status={getSlaStatus(r)}
          dueAt={r.sla_due_at}
          breachedAt={r.sla_breached_at}
        />
      ),
    },
    {
      id: 'updated_at',
      label: 'Actualizado',
      render: (r: CaseListItem) =>
        r.updated_at
          ? new Date(r.updated_at).toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' })
          : '—',
    },
  ]

  return (
    <Box>
      <PageHeader
        title="Casos"
        subtitle="Listado de casos con filtros y SLA"
        actions={
          <FormControl size="small" sx={{ minWidth: 200 }} variant="outlined">
            <InputLabel id="filter-status">Estado</InputLabel>
            <Select
              labelId="filter-status"
              value={statusFilter}
              label="Estado"
              onChange={(e) => {
                setStatusFilter(e.target.value)
                setPage(0)
              }}
              sx={{ borderRadius: 2 }}
            >
              <MenuItem value="">Todos</MenuItem>
              {(Object.keys(STATUS_LABELS) as CaseStatus[]).map((s) => (
                <MenuItem key={s} value={s}>
                  {STATUS_LABELS[s]}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        }
      />
      <DataTable<CaseListItem>
        columns={columns}
        rows={rows}
        keyField="id"
        loading={isLoading}
        emptyMessage="No hay casos"
        pagination={{
          page,
          rowsPerPage,
          totalRows: data?.count ?? 0,
          onPageChange: setPage,
          onRowsPerPageChange: (r) => {
            setRowsPerPage(r)
            setPage(0)
          },
          rowsPerPageOptions: [10, 20, 50],
        }}
        onRowClick={(row) => navigate(`/casos/${row.id}`)}
      />
    </Box>
  )
}
