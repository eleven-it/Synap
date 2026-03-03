import { useQuery } from '@tanstack/react-query'
import { Box } from '@mui/material'
import api from '@/api/endpoints'
import { PageHeader, DataTable } from '@/components/ui'

type SupportUser = { id?: number; name?: string; company?: { prefix?: string } }

export default function UsersPage() {
  const { data: list, isLoading } = useQuery({
    queryKey: ['support-users'],
    queryFn: async () => {
      const { data } = await api.supportUsers.list()
      return data
    },
  })

  const users: SupportUser[] = Array.isArray(list) ? (list as SupportUser[]) : []
  const columns = [
    { id: 'id', label: 'ID', render: (u: SupportUser) => u.id ?? '—' },
    { id: 'name', label: 'Nombre', render: (u: SupportUser) => u.name ?? '—' },
    { id: 'company', label: 'Empresa', render: (u: SupportUser) => u.company?.prefix ?? '—' },
  ]

  return (
    <Box>
      <PageHeader title="Usuarios de soporte" subtitle="Usuarios asociados a empresas" />
      <DataTable<SupportUser>
        columns={columns}
        rows={users}
        keyField="id"
        loading={isLoading}
        emptyMessage="No hay usuarios de soporte."
      />
    </Box>
  )
}
