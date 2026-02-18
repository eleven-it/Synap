import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, TextField, Button, Typography, Alert } from '@mui/material'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useAuth } from './useAuth'
import { Card } from '@/components/ui'

const schema = z.object({
  username: z.string().min(1, 'Usuario requerido'),
  password: z.string().min(1, 'Contraseña requerida'),
})

type FormData = z.infer<typeof schema>

function messageForStatus(status: number | undefined): string {
  switch (status) {
    case 401:
      return 'Credenciales inválidas. Revisá usuario y contraseña.'
    case 403:
      return 'No tenés permisos para acceder. Contactá al administrador.'
    case 409:
      return 'Transición no permitida. Probá de nuevo.'
    case 500:
    case 502:
    case 503:
      return 'Error del servidor. Reintentá en unos segundos.'
    default:
      return 'Error al iniciar sesión. Reintentá más tarde.'
  }
}

export default function LoginPage() {
  const navigate = useNavigate()
  const { login, loginMutation } = useAuth()
  const [apiError, setApiError] = useState<string | null>(null)

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { username: '', password: '' },
  })

  const onSubmit = async (data: FormData) => {
    setApiError(null)
    try {
      await login({ username: data.username, password: data.password })
      navigate('/dashboard', { replace: true })
    } catch (e: unknown) {
      const err = e as { response?: { data?: { message?: string }; status?: number } }
      setApiError(
        err.response?.data?.message ||
        messageForStatus(err.response?.status)
      )
    }
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: 'background.default',
      }}
    >
      <Card sx={{ p: 3, maxWidth: 400, width: '100%' }}>
        <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
          Synap Support
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 2 }}>
          Iniciar sesión en el backoffice
        </Typography>
        {apiError && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setApiError(null)}>
            {apiError}
          </Alert>
        )}
        <form onSubmit={handleSubmit(onSubmit)}>
          <TextField
            {...register('username')}
            label="Usuario"
            fullWidth
            margin="normal"
            error={!!errors.username}
            helperText={errors.username?.message}
            autoComplete="username"
            autoFocus
            sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
          />
          <TextField
            {...register('password')}
            type="password"
            label="Contraseña"
            fullWidth
            margin="normal"
            error={!!errors.password}
            helperText={errors.password?.message}
            autoComplete="current-password"
            sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
          />
          <Button
            type="submit"
            variant="contained"
            fullWidth
            size="large"
            sx={{ mt: 2, borderRadius: 2 }}
            disabled={loginMutation.isPending}
          >
            {loginMutation.isPending ? 'Entrando…' : 'Entrar'}
          </Button>
        </form>
      </Card>
    </Box>
  )
}
