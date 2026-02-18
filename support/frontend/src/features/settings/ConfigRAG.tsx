import { Drawer, Typography, Box, IconButton, TextField, Button } from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'

interface ConfigRAGProps {
  open: boolean
  onClose: () => void
}

export default function ConfigRAG({ open, onClose }: ConfigRAGProps) {
  return (
    <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: '100%', sm: 420 } } }}>
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">RAG / Conocimiento</Typography>
          <IconButton onClick={onClose} aria-label="Cerrar">
            <CloseIcon />
          </IconButton>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Ingesta y búsqueda ya expuestos en API: POST /api/knowledge/ingest/, GET /api/knowledge/search/. Config de fuentes y top_k: endpoints esperados en README.
        </Typography>
        <TextField label="Top K" type="number" fullWidth size="small" sx={{ mb: 1 }} defaultValue={10} />
        <Typography variant="caption" display="block" sx={{ mb: 2 }}>
          Fuentes: casos resueltos, human_note. Política: global + empresa.
        </Typography>
        <Button variant="outlined" sx={{ mr: 1 }}>Reindexar</Button>
        <Button variant="outlined" sx={{ mr: 1 }}>Ingestar ahora</Button>
        <Button variant="contained" onClick={onClose}>Cerrar</Button>
      </Box>
    </Drawer>
  )
}
