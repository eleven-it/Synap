/** Llamadas a la API según API.md. */
import client, { setIdempotencyKey } from './client'
import type {
  User,
  Company,
  CaseListItem,
  TimelineResponse,
  AttachmentItem,
  CopilotMessage,
  DashboardStats,
  MetricsResponse,
  IAConfig,
  ChannelConfig,
  BrandingConfig,
  RAGConfigItem,
  KnowledgeChunksResponse,
} from '@/types'

const api = {
  auth: {
    login: (username: string, password: string) =>
      client.post<{ user: User }>('/auth/login/', { username, password }),
    me: () => client.get<User>('/auth/me/'),
  },
  dashboard: () => client.get<DashboardStats>('/dashboard/'),
  cases: {
    list: (params?: { status?: string; company?: number; assigned_to?: number; limit?: number; offset?: number; ordering?: string }) =>
      client.get<{ count: number; results: CaseListItem[] }>('/casos/', { params }),
    get: (id: number) => client.get<CaseListItem>(`/casos/${id}/`),
    patch: (id: number, data: { status?: string; assigned_to_id?: number | null }, idempotent = true) => {
      const headers: Record<string, string> = {}
      if (idempotent) setIdempotencyKey(headers)
      return client.patch<CaseListItem>(`/casos/${id}/`, data, { headers })
    },
    timeline: (id: number) => client.get<TimelineResponse>(`/casos/${id}/timeline/`),
    attachments: (id: number) => client.get<{ attachments: AttachmentItem[] }>(`/casos/${id}/adjuntos/`),
    responsePreview: (id: number, texto: string) =>
      client.post<{ preview: { text: string; channels: unknown[] } }>(`/casos/${id}/respuesta/preview/`, { texto }),
    responseSend: (id: number, texto: string, idempotent = true) => {
      const headers: Record<string, string> = {}
      if (idempotent) setIdempotencyKey(headers)
      return client.post<{ resultado_por_canal: { canal: string; exito: boolean }[]; result_id?: number; case_id?: number; case_updated_at?: string }>(
        `/casos/${id}/respuesta/enviar/`,
        { texto },
        { headers }
      )
    },
    copilotMessages: (id: number) =>
      client.get<{ messages: CopilotMessage[] }>(`/casos/${id}/copiloto/mensajes/`),
    copilotPost: (
      id: number,
      texto: string,
      guardar_respuesta_como_conocimiento = false,
      sistema?: 'synap' | 'administranet',
    ) =>
      client.post<{
        respuesta_ia: string
        sugerencia_respuesta: string
        mensaje_id: number
        guardado_como_conocimiento: boolean
        knowledge_chunk_id: number | null
      }>(`/casos/${id}/copiloto/mensajes/`, {
        texto,
        guardar_respuesta_como_conocimiento,
        ...(sistema ? { sistema } : {}),
      }),
  },
  companies: {
    list: () => client.get<Company[]>('/empresas/'),
    get: (id: number) => client.get<Company>(`/empresas/${id}/`),
    create: (data: { synap_id: string; prefix: string; language: string; is_active?: boolean }) =>
      client.post<Company>('/empresas/', data),
    patch: (id: number, data: Partial<Company>) => client.patch<Company>(`/empresas/${id}/`, data),
    delete: (id: number) => client.delete(`/empresas/${id}/`),
  },
  supportUsers: {
    list: (params?: { company?: number }) => client.get<unknown[]>('/usuarios-soporte/', { params }),
    get: (id: number) => client.get<unknown>(`/usuarios-soporte/${id}/`),
    create: (data: unknown) => client.post('/usuarios-soporte/', data),
    patch: (id: number, data: unknown) => client.patch(`/usuarios-soporte/${id}/`, data),
    delete: (id: number) => client.delete(`/usuarios-soporte/${id}/`),
  },
  agents: {
    list: () => client.get<{ id: number; username: string; email: string; role: string }[]>('/agentes/'),
  },
  metrics: (params?: { desde_fecha?: string; hasta_fecha?: string; empresa_id?: number }) =>
    client.get<MetricsResponse>('/metricas/', { params }),
  knowledge: {
    chunksList: (params?: { limit?: number; offset?: number; source_type?: string; company_id?: number | null }) =>
      client.get<KnowledgeChunksResponse>('/knowledge/chunks/', { params: params ?? {} }),
    ingest: (items: { text: string; source_id?: string; metadata?: Record<string, unknown> }[], company_id?: number, source_type?: string) =>
      client.post<{ created: number; updated: number; message: string }>('/knowledge/ingest/', {
        items,
        company_id: company_id ?? null,
        source_type: source_type || 'caso',
      }),
    search: (q: string, params?: { company_id?: number; top_k?: number; source_type?: string; fallback?: string }) =>
      client.get<{ results: unknown[]; mode?: string }>('/knowledge/search/', { params: { q, ...params } }),
  },
  copiloto: {
    /** Envía un mensaje al copiloto (sin caso) y devuelve la respuesta IA. sistema opcional filtra RAG. */
    mensaje: (texto: string, sistema?: 'synap' | 'administranet') =>
      client.post<{ respuesta_ia: string; sugerencia_respuesta: string | null }>('/copiloto/mensaje/', {
        texto,
        ...(sistema ? { sistema } : {}),
      }),
  },
  config: {
    channels: {
      list: (params?: { company_id?: number | null }) =>
        client.get<{ count: number; results: ChannelConfig[] }>('/config/channels/', { params: params ?? {} }),
      get: (id: number) => client.get<ChannelConfig>(`/config/channels/${id}/`),
      create: (data: { company_id?: number | null; channel_type: string; display_name?: string; status?: string; config?: Record<string, unknown> }) =>
        client.post<ChannelConfig>('/config/channels/', data),
      patch: (id: number, data: { config?: Record<string, unknown>; status?: string; display_name?: string; company_id?: number | null }) =>
        client.patch<ChannelConfig>(`/config/channels/${id}/`, data),
      activate: (id: number) =>
        client.post<{ success: boolean; message?: string }>(`/config/channels/${id}/activate/`),
      deactivate: (id: number) =>
        client.post<{ success: boolean; message?: string }>(`/config/channels/${id}/deactivate/`),
      test: (id: number) =>
        client.post<{ success: boolean; message?: string }>(`/config/channels/${id}/test/`),
    },
    ia: {
      list: (company_id?: number | null) =>
        client.get<IAConfig[]>('/config/ia/', { params: company_id != null ? { company_id } : {} }),
      patch: (data: Partial<{ company_id: number | null; provider: string; model: string; api_key: string; limits_json: Record<string, unknown>; prompt_version_id: string; status: string }>) =>
        client.patch<IAConfig>('/config/ia/', data),
      test: (company_id?: number | null) =>
        client.post<{ success: boolean; message?: string }>('/config/ia/test/', company_id != null ? { company_id } : {}),
    },
    branding: {
      list: (company_id?: number | null) =>
        client.get<BrandingConfig[]>('/config/branding/', { params: company_id != null ? { company_id } : {} }),
      patch: (data: Partial<{ company_id: number | null; assistant_name: string; welcome_message: string; default_language: string }>) =>
        client.patch<BrandingConfig>('/config/branding/', data),
    },
    rag: {
      list: (company_id?: number | null) =>
        client.get<RAGConfigItem[]>('/config/rag/', { params: company_id != null ? { company_id } : {} }),
      patch: (data: Partial<{ company_id: number | null; top_k: number; status: string; sources_enabled: string[]; cache_ttl_seconds: number }>) =>
        client.patch<RAGConfigItem>('/config/rag/', data),
    },
  },
  knowledgeSyncFromSynap: (company_id?: number | null) =>
    client.post<{ created: number; updated: number; message: string }>('/knowledge/sync-from-synap/', { company_id: company_id ?? null }),
}

export default api
