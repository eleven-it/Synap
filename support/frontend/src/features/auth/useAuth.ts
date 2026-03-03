import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/api/endpoints'
import type { User } from '@/types'

const ME_QUERY_KEY = ['auth', 'me'] as const

export function useAuth() {
  const queryClient = useQueryClient()
  const { data: user, isLoading, isError, error } = useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: async () => {
      const { data } = await api.auth.me()
      return data
    },
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  const loginMutation = useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      api.auth.login(username, password),
    onSuccess: (response) => {
      // Poblar la caché con el usuario del login para que AuthGuard no redirija al montar /dashboard
      const payload = response.data as { user: User }
      if (payload?.user) {
        queryClient.setQueryData(ME_QUERY_KEY, { user: payload.user })
      }
      queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY })
    },
  })

  const logout = () => {
    queryClient.setQueryData(ME_QUERY_KEY, null)
    queryClient.clear()
    window.location.href = '/login'
  }

  // Backend devuelve { user: { id, username, email, role } }; exponer el usuario interno
  const actualUser = (user as { user?: User } | undefined)?.user

  return {
    user: actualUser,
    isLoading,
    isError,
    error,
    isAdmin: actualUser?.role === 'admin',
    isAgentOrAdmin: actualUser?.role === 'admin' || actualUser?.role === 'agent' || actualUser?.role === 'supervisor',
    login: loginMutation.mutateAsync,
    loginMutation,
    logout,
  }
}
