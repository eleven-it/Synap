import { useQuery } from '@tanstack/react-query'
import { Box } from '@mui/material'
import api from '@/api/endpoints'
import type { Company } from '@/types'
import { PageHeader, DataTable } from '@/components/ui'

export default function CompaniesPage() {
  const { data: list, isLoading } = useQuery({
    queryKey: ['companies'],
    queryFn: async () => {
      const { data } = await api.companies.list()
      return data
    },
  })

  const companies: Company[] = Array.isArray(list) ? list : []
  const columns = [
    { id: 'prefix', label: 'Prefijo', render: (c: Company) => c.prefix },
    { id: 'synap_id', label: 'Synap ID', render: (c: Company) => c.synap_id },
    { id: 'language', label: 'Idioma', render: (c: Company) => c.language },
    { id: 'is_active', label: 'Activa', render: (c: Company) => (c.is_active ? 'Sí' : 'No') },
  ]

  return (
    <Box>
      <PageHeader title="Empresas" subtitle="Listado de empresas configuradas" />
      <DataTable<Company>
        columns={columns}
        rows={companies}
        keyField="id"
        loading={isLoading}
        emptyMessage="No hay empresas. Configurá desde Admin o API."
      />
    </Box>
  )
}
