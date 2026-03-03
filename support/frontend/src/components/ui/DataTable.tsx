import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Paper,
  type TableProps,
} from '@mui/material'

export interface DataTableColumn<T> {
  id: string
  label: string
  align?: 'left' | 'right' | 'center'
  render?: (row: T) => React.ReactNode
  minWidth?: number
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[]
  rows: T[]
  keyField: keyof T | ((row: T) => string | number)
  loading?: boolean
  emptyMessage?: string
  emptyAction?: React.ReactNode
  pagination?: {
    page: number
    rowsPerPage: number
    totalRows: number
    onPageChange: (page: number) => void
    onRowsPerPageChange?: (rowsPerPage: number) => void
    rowsPerPageOptions?: number[]
  }
  onRowClick?: (row: T) => void
  size?: TableProps['size']
}

function getKey<T>(row: T, keyField: keyof T | ((row: T) => string | number)): string | number {
  return typeof keyField === 'function' ? keyField(row) : (row[keyField] as string | number)
}

export default function DataTable<T>({
  columns,
  rows,
  keyField,
  loading,
  emptyMessage = 'No hay datos',
  emptyAction,
  pagination,
  onRowClick,
  size = 'medium',
}: DataTableProps<T>) {
  return (
    <TableContainer
      component={Paper}
      elevation={0}
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 2,
        overflow: 'auto',
      }}
    >
      <Table size={size} stickyHeader aria-label="Tabla de datos">
        <TableHead>
          <TableRow>
            {columns.map((col) => (
              <TableCell
                key={col.id}
                align={col.align}
                sx={{
                  fontWeight: 600,
                  bgcolor: 'background.default',
                  borderBottom: '1px solid',
                  borderColor: 'divider',
                  whiteSpace: 'nowrap',
                  minWidth: col.minWidth,
                }}
              >
                {col.label}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {loading
            ? Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {columns.map((col) => (
                    <TableCell key={col.id}>
                      <Box sx={{ height: 24, bgcolor: 'action.hover', borderRadius: 1 }} />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            : rows.length === 0
              ? (
                <TableRow>
                  <TableCell colSpan={columns.length} align="center" sx={{ py: 4 }}>
                    {emptyMessage}
                    {emptyAction && <Box sx={{ mt: 1 }}>{emptyAction}</Box>}
                  </TableCell>
                </TableRow>
              )
              : rows.map((row) => (
                <TableRow
                  key={getKey(row, keyField)}
                  hover
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  sx={{
                    cursor: onRowClick ? 'pointer' : undefined,
                    transition: 'background-color 0.15s ease',
                  }}
                >
                  {columns.map((col) => (
                    <TableCell key={col.id} align={col.align}>
                      {col.render ? col.render(row) : (row as Record<string, unknown>)[col.id] as React.ReactNode}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
        </TableBody>
      </Table>
      {pagination && !loading && rows.length > 0 && (
        <TablePagination
          component="div"
          count={pagination.totalRows}
          page={pagination.page}
          onPageChange={(_, p) => pagination.onPageChange(p)}
          rowsPerPage={pagination.rowsPerPage}
          onRowsPerPageChange={
            pagination.onRowsPerPageChange
              ? (e) => pagination.onRowsPerPageChange?.(Number(e.target.value))
              : undefined
          }
          rowsPerPageOptions={pagination.rowsPerPageOptions ?? [10, 20, 50]}
          labelRowsPerPage="Filas:"
          labelDisplayedRows={({ from, to, count }) => `${from}-${to} de ${count}`}
        />
      )}
    </TableContainer>
  )
}
