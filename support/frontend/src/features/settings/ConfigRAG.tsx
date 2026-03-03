import { useState, useEffect } from 'react'
import {
  Drawer,
  Typography,
  Box,
  IconButton,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import CloudDownloadIcon from '@mui/icons-material/CloudDownload'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import MenuBookIcon from '@mui/icons-material/MenuBook'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSnackbar } from 'notistack'
import api from '@/api/endpoints'

interface ConfigRAGProps {
  open: boolean
  onClose: () => void
  companyId?: number | null
}

export default function ConfigRAG({ open, onClose, companyId }: ConfigRAGProps) {
  const queryClient = useQueryClient()
  const { enqueueSnackbar } = useSnackbar()

  const { data: ragList, isLoading } = useQuery({
    queryKey: ['config', 'rag', companyId ?? null],
    queryFn: async () => {
      const { data } = await api.config.rag.list(companyId ?? undefined)
      return data
    },
    enabled: open,
  })

  const rag = Array.isArray(ragList) && ragList.length > 0 ? ragList[0] : null

  const [topK, setTopK] = useState(10)
  const [chunksOffset, setChunksOffset] = useState(0)
  const [chunksSourceType, setChunksSourceType] = useState<string>('')
  const chunksLimit = 15
  useEffect(() => {
    if (rag?.top_k != null) setTopK(rag.top_k)
    else setTopK(10)
  }, [rag?.top_k])

  const {
    data: chunksData,
    isLoading: chunksLoading,
    isError: chunksError,
    error: chunksErrorDetail,
    refetch: refetchChunks,
  } = useQuery({
    queryKey: ['knowledge', 'chunks', chunksOffset, chunksSourceType || null, companyId ?? null],
    queryFn: async () => {
      const { data } = await api.knowledge.chunksList({
        limit: chunksLimit,
        offset: chunksOffset,
        ...(chunksSourceType ? { source_type: chunksSourceType } : {}),
        ...(companyId != null ? { company_id: companyId } : {}),
      })
      return data
    },
    enabled: open,
    retry: 1,
  })

  const patchMutation = useMutation({
    mutationFn: (payload: { company_id?: number | null; top_k?: number; status?: string }) =>
      api.config.rag.patch(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config', 'rag'] })
      enqueueSnackbar('Configuración RAG guardada', { variant: 'success' })
    },
    onError: (err: { response?: { data?: { message?: string } } }) => {
      enqueueSnackbar(err.response?.data?.message || 'Error al guardar', { variant: 'error' })
    },
  })

  const syncMutation = useMutation({
    mutationFn: () => api.knowledgeSyncFromSynap(companyId ?? null),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['config', 'rag'] })
      queryClient.invalidateQueries({ queryKey: ['knowledge', 'chunks'] })
      enqueueSnackbar(res?.data?.message ?? 'Conocimiento cargado desde Synap', { variant: 'success' })
    },
    onError: (err: { response?: { data?: { message?: string } } }) => {
      enqueueSnackbar(err.response?.data?.message || 'Error al cargar desde Synap', { variant: 'error' })
    },
  })

  const handleSave = () => {
    const k = Math.min(50, Math.max(1, topK))
    patchMutation.mutate({
      company_id: companyId ?? null,
      top_k: k,
      status: rag?.status === 'active' ? 'active' : 'draft',
    })
  }

  const handleToggleActive = (active: boolean) => {
    patchMutation.mutate({
      company_id: companyId ?? null,
      status: active ? 'active' : 'draft',
    })
  }

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{ sx: { width: { xs: '100%', sm: 520 } } }}
    >
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">RAG / Conocimiento</Typography>
          <IconButton onClick={onClose} aria-label="Cerrar">
            <CloseIcon />
          </IconButton>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Base de conocimiento para el copiloto. Podés activar RAG y cargar contenido desde Synap (ERP).
          Si Synap corre en otra URL, configurá <strong>SUPPORT_SYNAP_API_URL</strong> en el .env del backend Support.
        </Typography>

        {isLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
            <CircularProgress size={28} />
          </Box>
        )}

        {!isLoading && (
          <>
            <FormControlLabel
              control={
                <Switch
                  size="small"
                  checked={rag?.status === 'active'}
                  disabled={patchMutation.isPending}
                  onChange={(_, v) => handleToggleActive(v)}
                />
              }
              label="RAG activo"
              sx={{ mb: 2 }}
            />
            <TextField
              label="Top K"
              type="number"
              fullWidth
              size="small"
              sx={{ mb: 2 }}
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value, 10) || 10)}
              inputProps={{ min: 1, max: 50 }}
              helperText="Cantidad de fragmentos a usar como contexto (1–50)"
            />
            <Typography variant="caption" display="block" color="text.secondary" sx={{ mb: 2 }}>
              Fuentes: casos resueltos, notas, conocimiento desde Synap. Política: global + empresa.
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
              <Button
                variant="outlined"
                startIcon={<CloudDownloadIcon />}
                onClick={() => syncMutation.mutate()}
                disabled={syncMutation.isPending}
              >
                {syncMutation.isPending ? 'Cargando…' : 'Cargar desde Synap'}
              </Button>
              <Button variant="outlined" onClick={handleSave} disabled={patchMutation.isPending}>
                Guardar
              </Button>
            </Box>
            <Accordion disableGutters sx={{ boxShadow: 'none', '&:before': { display: 'none' }, mt: 2 }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ minHeight: 48 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <MenuBookIcon fontSize="small" color="action" />
                  <Typography variant="subtitle2">Conocimientos cargados</Typography>
                  {chunksData != null && (
                    <Chip label={chunksData.count} size="small" sx={{ ml: 0.5 }} />
                  )}
                </Box>
              </AccordionSummary>
              <AccordionDetails sx={{ pt: 0, pb: 2 }}>
                <FormControl size="small" fullWidth sx={{ mb: 2 }}>
                  <InputLabel>Filtrar por fuente</InputLabel>
                  <Select
                    value={chunksSourceType}
                    label="Filtrar por fuente"
                    onChange={(e) => {
                      setChunksSourceType(e.target.value)
                      setChunksOffset(0)
                    }}
                  >
                    <MenuItem value="">Todas</MenuItem>
                    <MenuItem value="synap">Synap</MenuItem>
                    <MenuItem value="human_note">Nota humana</MenuItem>
                    <MenuItem value="resolved_case">Caso resuelto</MenuItem>
                    <MenuItem value="caso">Caso</MenuItem>
                  </Select>
                </FormControl>
                {chunksLoading && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
                    <CircularProgress size={24} />
                  </Box>
                )}
                {!chunksLoading && chunksError && (
                  <Box sx={{ py: 2, textAlign: 'center' }}>
                    <Typography variant="body2" color="error" sx={{ mb: 1 }}>
                      No se pudieron cargar los conocimientos.
                    </Typography>
                    <Typography variant="caption" display="block" color="text.secondary" sx={{ mb: 1 }}>
                      {(chunksErrorDetail as { response?: { status?: number; data?: { message?: string } } })?.response?.data?.message ||
                        (chunksErrorDetail as Error)?.message ||
                        'Verificá que tu usuario tenga permisos de administrador.'}
                    </Typography>
                    {(chunksErrorDetail as { response?: { status?: number } })?.response?.status === 404 && (
                      <Typography variant="caption" display="block" color="text.secondary" sx={{ mb: 1 }}>
                        Si el backend Support se actualizó hace poco, reiniciá el contenedor para que cargue la ruta /api/knowledge/chunks/
                      </Typography>
                    )}
                    <Button size="small" variant="outlined" onClick={() => refetchChunks()}>
                      Reintentar
                    </Button>
                  </Box>
                )}
                {!chunksLoading && !chunksError && chunksData != null && (
                  <>
                    {chunksData.results.length === 0 && chunksData.message != null && (
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {chunksData.message}
                      </Typography>
                    )}
                    <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 320, mb: 1 }}>
                      <Table size="small" stickyHeader>
                        <TableHead>
                          <TableRow>
                            <TableCell>Tipo</TableCell>
                            <TableCell>Sistema</TableCell>
                            <TableCell>Vista previa</TableCell>
                            <TableCell align="center">Embed</TableCell>
                            <TableCell>Fecha</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {chunksData.results.length === 0 ? (
                            <TableRow>
                              <TableCell colSpan={5} align="center" sx={{ color: 'text.secondary', py: 3 }}>
                                {chunksData.message
                                  ? 'Usá la búsqueda (GET /api/knowledge/search?q=...) para ver fragmentos por consulta.'
                                  : 'No hay fragmentos. Cargá desde Synap o guardá respuestas como conocimiento.'}
                              </TableCell>
                            </TableRow>
                          ) : (
                            chunksData.results.map((c) => (
                              <TableRow key={c.id}>
                                <TableCell sx={{ whiteSpace: 'nowrap' }}>{c.source_type}</TableCell>
                                <TableCell>{c.sistema ?? '—'}</TableCell>
                                <TableCell sx={{ maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis' }} title={c.text}>
                                  {c.text || '—'}
                                </TableCell>
                                <TableCell align="center">{c.has_embedding ? '✓' : '—'}</TableCell>
                                <TableCell sx={{ whiteSpace: 'nowrap', fontSize: '0.75rem' }}>
                                  {c.created_at ? new Date(c.created_at).toLocaleDateString() : '—'}
                                </TableCell>
                              </TableRow>
                            ))
                          )}
                        </TableBody>
                      </Table>
                    </TableContainer>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        {chunksData.count === 0
                          ? '0 fragmentos'
                          : `${chunksOffset + 1}–${Math.min(chunksOffset + chunksLimit, chunksData.count)} de ${chunksData.count}`}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <Button
                          size="small"
                          disabled={chunksOffset === 0}
                          onClick={() => setChunksOffset((o) => Math.max(0, o - chunksLimit))}
                        >
                          Anterior
                        </Button>
                        <Button
                          size="small"
                          disabled={chunksOffset + chunksLimit >= chunksData.count}
                          onClick={() => setChunksOffset((o) => o + chunksLimit)}
                        >
                          Siguiente
                        </Button>
                      </Box>
                    </Box>
                  </>
                )}
                {!chunksLoading && !chunksError && chunksData == null && (
                  <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
                    No hay datos de conocimientos. Cargá desde Synap para ver fragmentos aquí.
                  </Typography>
                )}
              </AccordionDetails>
            </Accordion>
            <Button variant="contained" onClick={onClose} sx={{ mt: 2 }}>
              Cerrar
            </Button>
          </>
        )}
      </Box>
    </Drawer>
  )
}
