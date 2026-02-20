/** Tipos alineados con API backend (API.md). */

export type Role = 'admin' | 'agent' | 'supervisor'

export interface User {
  id: number
  username: string
  email: string
  role: Role
}

export interface Company {
  id: number
  synap_id: string
  prefix: string
  language: string
  is_active: boolean
  created_at?: string
  updated_at?: string
}

export type CaseStatus =
  | 'iniciado'
  | 'en_analisis_ia'
  | 'esperando_respuesta_usuario'
  | 'derivado_a_humano'
  | 'asignado_a_agente_humano'
  | 'en_proceso_humano'
  | 'resuelto'
  | 'cerrado'
  | 'reabierto'

export interface CaseListItem {
  id: number
  number_display: string
  status: CaseStatus
  company: Company
  assigned_to: { id: number; username: string } | null
  sla_started_at: string | null
  sla_due_at: string | null
  sla_paused_since: string | null
  sla_warning_sent_at: string | null
  sla_breached_at: string | null
  created_at: string
  updated_at: string
}

export interface Message {
  id: number
  channel_type: string
  sender_type: string
  content: string
  direction: 'inbound' | 'outbound'
  created_at: string
}

export interface CaseSummary {
  id: number
  summary_text: string
  model_version: string
  created_at: string
}

export interface TimelineResponse {
  messages: Message[]
  summaries: CaseSummary[]
}

export interface AttachmentItem {
  id: number
  original_name: string
  content_type: string
  size_bytes: number
  url: string
  expires_seconds: number
}

export interface CopilotMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
  saved_to_knowledge?: boolean
  knowledge_chunk_id?: number | null
}

export interface DashboardStats {
  cases_by_status: Record<string, number>
  open_count: number
  sla_at_risk_count: number
}

export interface MetricsResponse {
  desde: string
  hasta: string
  sla_inicios: number
  sla_vencidos: number
  casos_resueltos: number
  sla_cumplimiento_pct: number
}

export interface ApiError {
  code?: string
  message: string
  details?: unknown[]
}

/** Configuración de canal (Telegram, WhatsApp, Email). Solo canales con status "active" se usan para recibir/enviar. */
export interface ChannelConfig {
  id: number
  company_id: number | null
  channel_type: string
  display_name: string
  status: string
  config_masked: Record<string, unknown>
  last_check_at: string | null
  last_error: string
  created_at: string
  updated_at: string
}

/** Configuración de branding (nombre del asistente, mensaje de bienvenida). */
export interface BrandingConfig {
  id: number
  company_id: number | null
  assistant_name: string
  welcome_message: string
  default_language: string
  created_at?: string
  updated_at?: string
}

/** Configuración RAG (top_k, fuentes, estado). */
export interface RAGConfigItem {
  id: number
  company_id: number | null
  top_k: number
  sources_enabled: string[]
  cache_ttl_seconds: number
  status: string
  last_ingest_at: string | null
  last_error: string
  created_at?: string
  updated_at?: string
}

/** Chunk de conocimiento RAG (listado para UI). */
export interface KnowledgeChunkItem {
  id: number
  source_type: string
  source_id: string
  company_id: number | null
  text: string
  text_length: number
  metadata: Record<string, unknown>
  sistema?: string
  file?: string
  has_embedding: boolean
  created_at: string | null
}

export interface KnowledgeChunksResponse {
  count: number
  limit: number
  offset: number
  results: KnowledgeChunkItem[]
}

/** Configuración IA (GET devuelve api_key_masked; PATCH acepta api_key en texto para guardar cifrado). */
export interface IAConfig {
  id: number
  company_id: number | null
  provider: string
  model: string
  api_key_masked: string
  limits_json: Record<string, unknown>
  prompt_version_id: string
  status: string
  last_check_at: string | null
  last_error: string
  created_at: string
  updated_at: string
}
