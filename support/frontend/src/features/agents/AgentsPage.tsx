import { useQuery } from '@tanstack/react-query'
import { Box } from '@mui/material'
import api from '@/api/endpoints'
import { PageHeader, DataTable, Badge } from '@/components/ui'

type Agent = { id: number; username: string; email: string; role: string }

export default function AgentsPage() {
  const { data: list, isLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: async () => {
      const { data } = await api.agents.list()
      return data
    },
  })

  const agents: Agent[] = Array.isArray(list) ? list : []
  const columns = [
    { id: 'username', label: 'Usuario', render: (a: Agent) => a.username },
    { id: 'email', label: 'Email', render: (a: Agent) => a.email || '—' },
    {
      id: 'role',
      label: 'Rol',
      render: (a: Agent) => <Badge label={a.role} variant="default" />,
    },
  ]

  return (
    <Box>
      <PageHeader
        title="Agentes"
        subtitle="Usuarios del backoffice con perfil de agente (para asignación a casos)."
      />
      <DataTable<Agent>
        columns={columns}
        rows={agents}
        keyField="id"
        loading={isLoading}
        emptyMessage="No hay agentes."
      />
    </Box>
  )
}
