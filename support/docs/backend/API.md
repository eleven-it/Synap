# Referencia API REST (Backend)

Base URL: `/api/`. Todas las respuestas en JSON. Autenticación por sesión (cookie) salvo donde se indique.

## Autenticación y salud

### GET /api/health

**Sin autenticación.** Diagnóstico completo. **Siempre 200**; el cuerpo indica estado (para UX/monitoreo que no quiera romper por un 5xx).

**Respuesta 200:**
```json
{
  "status": "ok",
  "db": "ok",
  "redis": "ok",
  "storage": "ok",
  "environment": "local"
}
```
- `status`: "ok" | "degraded" | "error"
- `db`: "ok" | "error"
- `redis`: "ok" | "error" | "skipped"
- `storage`: "ok" | "error" | "skipped"

---

### GET /api/health/live

**Sin autenticación.** **Liveness:** siempre **200** si el proceso responde. Uso típico: probe de Kubernetes/Docker para saber que el contenedor está vivo.

**Respuesta 200:** `{ "live": true }`

---

### GET /api/health/ready

**Sin autenticación.** **Readiness:** **200** si DB (y Redis si está configurado) están OK; **500** si DB o Redis fallan. Uso: readiness probe para no enviar tráfico hasta que el servicio pueda atender.

**Respuesta 200:** `{ "ready": true, "db": "ok", "redis": "ok" }`  
**Respuesta 500:** `{ "ready": false, "reason": "db"|"redis", ... }`

---

### POST /api/auth/login/

**Sin autenticación.** Login con username y password. Crea sesión.

**Body:**
```json
{
  "username": "agente1",
  "password": "..."
}
```

**Respuesta 200:**
```json
{
  "user": {
    "id": 1,
    "username": "agente1",
    "email": "",
    "role": "agent"
  }
}
```

**Errores:** 400 (falta username/password), 401 (credenciales inválidas).

---

### GET /api/auth/me/

**Autenticado.** Usuario actual y rol.

**Respuesta 200:** Mismo formato que el objeto `user` de login.

---

## Dashboard y métricas

### GET /api/dashboard/ o GET /api/stats/

**Autenticado.** Resumen para el dashboard.

**Respuesta 200:**
```json
{
  "cases_by_status": { "iniciado": 5, "en_analisis_ia": 3, ... },
  "open_count": 12,
  "sla_at_risk_count": 2
}
```

---

### GET /api/metricas/

**Autenticado.** Métricas de SLA y casos.

**Query params:** `desde_fecha`, `hasta_fecha`, `empresa_id` (opcionales). Fechas en ISO.

**Respuesta 200:**
```json
{
  "desde": "...",
  "hasta": "...",
  "sla_inicios": 100,
  "sla_vencidos": 5,
  "casos_resueltos": 80,
  "sla_cumplimiento_pct": 95.0
}
```

---

## Casos

### GET /api/casos/

**Autenticado (Agente o Admin).** Lista de casos con paginación y filtros.

**Query params:**
- `status`, `company`, `assigned_to` (filtros)
- `ordering`: ej. `-created_at`, `number_display`
- `limit`, `offset` (paginación; default limit 20, max 100)

**Respuesta 200:**
```json
{
  "count": 50,
  "results": [
    {
      "id": 1,
      "number_display": "SUP-ACME-000001",
      "status": "asignado_a_agente_humano",
      "company": { "id": 1, "synap_id": "...", "prefix": "ACME", "language": "es", "is_active": true },
      "assigned_to": { "id": 2, "username": "agente1" },
      "sla_started_at": "...",
      "sla_due_at": "...",
      "sla_paused_since": null,
      "sla_warning_sent_at": null,
      "sla_breached_at": null,
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

---

### GET /api/casos/:id/

**Autenticado.** Detalle de un caso. Mismo formato que un ítem de `results` anterior.

---

### PATCH /api/casos/:id/

**Autenticado.** Actualizar estado y/o asignación. **Idempotente** con header `Idempotency-Key` (UUID) o body `action_uuid`: si se repite la misma clave para el mismo caso y usuario, se devuelve la misma respuesta sin repetir efectos.

**Body (parcial):**
```json
{
  "status": "en_proceso_humano",
  "assigned_to_id": 2,
  "action_uuid": "550e8400-e29b-41d4-a716-446655440000"
}
```

- **status:** debe ser una transición válida desde el estado actual (ver SERVICIOS_DOMINIO.md).
- **assigned_to_id:** si se envía, se asigna el caso a ese usuario y se transiciona a `asignado_a_agente_humano` y se inicia el SLA.
- **action_uuid:** opcional; UUID para idempotencia (alternativa al header `Idempotency-Key`).

**Respuesta 200:** Objeto caso actualizado.

**Errores:** 409 con `code: "CASE_STATE_TRANSITION_INVALID"` si la transición no está permitida.

---

### GET /api/casos/:id/timeline/

**Autenticado.** Mensajes y resúmenes del caso ordenados por tiempo.

**Respuesta 200:**
```json
{
  "messages": [
    {
      "id": 1,
      "channel_type": "telegram",
      "sender_type": "user",
      "content": "...",
      "direction": "inbound",
      "created_at": "..."
    }
  ],
  "summaries": [
    {
      "id": 1,
      "summary_text": "...",
      "model_version": "...",
      "created_at": "..."
    }
  ]
}
```

---

### GET /api/casos/:id/adjuntos/

**Autenticado.** Lista de adjuntos del caso con URL firmada para descarga.

**Respuesta 200:**
```json
{
  "attachments": [
    {
      "id": 1,
      "original_name": "doc.pdf",
      "content_type": "application/pdf",
      "size_bytes": 1024,
      "url": "https://...",
      "expires_seconds": 3600
    }
  ]
}
```

---

### POST /api/casos/:id/respuesta/preview/

**Autenticado.** Vista previa de la respuesta. Stub: devuelve el texto.

**Body:** `{ "texto": "..." }` o `{ "text": "..." }`

---

### POST /api/casos/:id/respuesta/enviar/

**Autenticado.** Envía respuesta: registra un mensaje saliente (remitente agente) y evento de auditoría. **Idempotente** con `Idempotency-Key` o `action_uuid`.

**Body:** `{ "texto": "..." }` o `{ "text": "..." }`, opcional `action_uuid` (UUID).

**Respuesta 200:**
```json
{
  "resultado_por_canal": [ { "canal": "api", "exito": true } ]
}
```

---

### GET /api/casos/:id/copiloto/mensajes/

**Autenticado (Agente o Admin).** Historial de mensajes del copiloto para este caso (trazable a case_id).

**Respuesta 200:**
```json
{
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "...",
      "created_at": "...",
      "saved_to_knowledge": false,
      "knowledge_chunk_id": null
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "...",
      "created_at": "...",
      "saved_to_knowledge": true,
      "knowledge_chunk_id": 42
    }
  ]
}
```

---

### POST /api/casos/:id/copiloto/mensajes/

**Autenticado (Agente o Admin).** Envía un mensaje al copiloto en contexto del caso; devuelve respuesta IA. Opcionalmente guarda la respuesta como chunk de conocimiento (source_type=human_note).

**Body:**
```json
{
  "texto": "¿Cómo respondo a este cliente?",
  "guardar_respuesta_como_conocimiento": false
}
```

**Respuesta 200:**
```json
{
  "respuesta_ia": "...",
  "sugerencia_respuesta": "...",
  "mensaje_id": 2,
  "guardado_como_conocimiento": false,
  "knowledge_chunk_id": null
}
```
- Si `guardar_respuesta_como_conocimiento` es true, se crea un chunk en knowledge (human_note) y se devuelve `knowledge_chunk_id`.

---

## Empresas (Admin)

### GET /api/empresas/

**Admin.** Lista de empresas.

### GET /api/empresas/:id/

**Admin.** Detalle de empresa (incluye `sla_configs`).

### POST /api/empresas/

**Admin.** Crear empresa. Body: `synap_id`, `prefix`, `language`, `is_active`.

### PATCH /api/empresas/:id/ , DELETE /api/empresas/:id/

**Admin.** Actualizar o eliminar.

---

## Usuarios de soporte (Admin)

### GET /api/usuarios-soporte/

**Admin.** Lista de usuarios de soporte. Query: `company` (filtro).

### GET /api/usuarios-soporte/:id/

**Admin.** Detalle con `channel_identities`.

### POST /api/usuarios-soporte/ , PATCH /api/usuarios-soporte/:id/ , DELETE

**Admin.** CRUD usuario de soporte e identidades de canal.

---

## Agentes

### GET /api/agentes/

**Autenticado (Agente o Admin).** Lista de usuarios backoffice con perfil de agente (para asignación y filtros).

**Respuesta 200:**
```json
[
  { "id": 1, "username": "admin", "email": "", "role": "admin" },
  { "id": 2, "username": "agente1", "email": "", "role": "agent" }
]
```

---

## Copiloto IA

### POST /api/copiloto/mensaje/

**Autenticado.** Envía un mensaje al copiloto (chat agente ↔ IA). Opcionalmente en contexto de un caso.

**Body:**
```json
{
  "texto": "Ayúdame a redactar una respuesta para...",
  "case_id": 1
}
```

**Respuesta 200:**
```json
{
  "respuesta_ia": "...",
  "sugerencia_respuesta": "..."
}
```

---

### GET /api/copiloto/historial/

**Autenticado.** Historial del chat copiloto del usuario. Query: `case_id` (opcional).

**Respuesta 200:**
```json
{
  "messages": [
    { "role": "user", "content": "...", "created_at": "..." },
    { "role": "assistant", "content": "...", "created_at": "..." }
  ]
}
```

---

## Conocimiento RAG (Admin)

### POST /api/knowledge/ingest/

**Admin.** Ingesta chunks de conocimiento; dispara jobs Celery para embeddings. No re-embed si content_hash no cambia.

**Body:**
```json
{
  "items": [
    { "text": "Fragmento de texto...", "source_id": "caso-123", "metadata": {} }
  ],
  "company_id": 1,
  "source_type": "caso"
}
```
- `company_id`: opcional; null = conocimiento global.
- `source_type`: caso, codigo, human_note, resolved_case (default "caso").

**Respuesta 200:** `{ "created": 2, "updated": 0, "message": "..." }`

---

### GET /api/knowledge/search/

**Admin (debug).** Búsqueda por similitud (embed(query) → vector). Si no hay `EMBEDDING_FUNCTION` configurada: **501 Not Implemented** con mensaje `"embeddings provider not configured"`, salvo que se use **`fallback=text`** para búsqueda textual (Postgres) y así poder probar sin proveedor.

**Query:** `q` (requerido), `company_id`, `top_k` (default 10), `source_type`, `fallback=text` (opcional; búsqueda por texto si no hay embeddings).

**Respuesta 200:** `{ "results": [ ... ], "mode": "vector"|"text" }` — con `fallback=text` incluye `"message"` explicando que es búsqueda textual.

**Respuesta 501:** Sin embedder y sin `fallback=text`.

---

## Webhooks (canales)

Endpoints que aceptan mensajes entrantes. **Dedupe:** si el body incluye el ID externo del mensaje y ya existe un mensaje con ese `(channel_type, external_message_id)`, responden **200** con `{ "duplicate": true }` sin crear mensaje. Si `external_message_id` llega vacío o no se envía, **no se aplica dedupe** (se pueden crear mensajes duplicados); por eso es importante enviar siempre la fuente correcta por canal.

**Fuente de verdad por canal (external_message_id):**

| Canal     | Origen recomendado                          | Notas |
|----------|----------------------------------------------|-------|
| **Telegram** | `update.message.message_id` o `update.update_id` | Usar `message_id` por mensaje para dedupe fino. |
| **WhatsApp** | `messages[0].id` (Cloud API)                 | ID del mensaje en la API de Meta. |
| **Email**    | Header `Message-ID` del correo entrante      | Único por correo; evita reprocesar el mismo mail. |

Al implementar la lógica real del webhook, parsear el body del proveedor, extraer el ID según la tabla anterior, asignar `channel_type` y `external_message_id` al crear el `Message`; así la siguiente vez que llegue el mismo evento se detecta el duplicado.

- **POST /api/webhooks/telegram/** — channel_type `telegram`
- **POST /api/webhooks/whatsapp/** — channel_type `whatsapp`
- **POST /api/webhooks/email/** — channel_type `email`

**Sin autenticación.**

---

## Paginación

En listados (casos, empresas, etc.): parámetros `limit` (default 20, max 100) y `offset`. La respuesta incluye `count` y `results` (o lista directa según el endpoint).

---

## Errores normalizados

Cuerpo de error:

```json
{
  "code": "CODIGO_INTERNO",
  "message": "Mensaje legible",
  "details": []
}
```

Códigos HTTP: 400 (validación), 401 (no autenticado), 403 (sin permiso), 404 (no encontrado), 409 (conflicto, ej. transición de estado inválida), 429 (rate limit), 5xx (error interno).

Códigos internos ej.: `VALIDATION_ERROR`, `UNAUTHORIZED`, `CASE_STATE_TRANSITION_INVALID`, `RATE_LIMIT_EXCEEDED`.

---

## Permisos por rol

- **Admin:** Acceso completo (empresas, usuarios de soporte, agentes, casos, dashboard, métricas, copiloto).
- **Agente:** Casos (lista, detalle, PATCH, timeline, adjuntos, respuesta), dashboard, agentes, métricas, copiloto. No CRUD de empresas ni usuarios de soporte.
- **Supervisor:** Mismo que Agente (se puede ampliar visibilidad de métricas en implementación futura).

Implementación: `IsAgentOrAdmin` (casos, dashboard, agentes, métricas, copiloto) e `IsAdmin` (empresas, usuarios-soporte, **configuración**).

---

## Configuración (Admin)

Todos los endpoints bajo `/api/config/` requieren **Admin**. Los secretos (tokens, API keys, contraseñas) se guardan cifrados y en GET se devuelven **enmascarados** (ej. `****1234`). En PATCH, si un campo secreto viene vacío no se reemplaza.

### Canales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/config/channels/` | Lista config por canal (filtros: company_id, channel_type, status). |
| POST | `/api/config/channels/` | Crear borrador (body: channel_type, display_name?, config? { token, ... }). |
| GET | `/api/config/channels/{id}/` | Detalle (config_masked, last_check_at, last_error). |
| PATCH | `/api/config/channels/{id}/` | Actualizar (config parcial; secretos vacíos no se reemplazan). |
| POST | `/api/config/channels/{id}/test/` | Probar conexión (Telegram getMe, WhatsApp Graph, SMTP, etc.). |
| POST | `/api/config/channels/{id}/activate/` | Poner status active. |
| POST | `/api/config/channels/{id}/deactivate/` | Poner status disabled. |

### IA

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/config/ia/?company_id=` | Config IA (global o por empresa). api_key_masked. |
| PATCH | `/api/config/ia/` | Guardar (company_id opcional; get-or-create por ámbito). |
| POST | `/api/config/ia/test/` | Test LLM (body/query company_id opcional). |

### RAG

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/config/rag/?company_id=` | top_k, sources_enabled, cache_ttl_seconds. |
| PATCH | `/api/config/rag/` | Guardar. |
| POST | `/api/config/rag/ingest/` | Ingesta (items, company_id?, source_type?). |
| POST | `/api/config/rag/reindex/` | Reindexación (stub). |

### Storage

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/config/storage/` | Endpoint, bucket, region, access_key_masked, max_size_bytes, etc. |
| PATCH | `/api/config/storage/` | Guardar (access_key/secret opcionales; vacíos = no cambiar). |
| POST | `/api/config/storage/test/` | Probar credenciales (list bucket). |

### Seguridad

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/config/security/` | rate_limits, anti_spam_enabled, pii_warning_enabled. |
| PATCH | `/api/config/security/` | Guardar. |
| POST | `/api/config/security/self-check/` | Checklist de configuración. |

### Notificaciones

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/config/notifications/` | escalation_emails, plantillas SLA, internal_alert_channel. |
| PATCH | `/api/config/notifications/` | Guardar. |

### Branding

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/config/branding/?company_id=` | assistant_name, welcome_message, default_language. |
| PATCH | `/api/config/branding/` | Guardar (company_id opcional). |

### SLA (CRUD existente)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/config/sla/?company_id=` | Lista SLAConfig por empresa. |
| POST | `/api/config/sla/` | Crear (company_id, case_type, response_time_minutes, warning_pct). |
| GET | `/api/config/sla/{id}/` | Detalle. |
| PATCH | `/api/config/sla/{id}/` | Actualizar. |
| DELETE | `/api/config/sla/{id}/` | Eliminar. |

**Respuestas de test:** `{ "success": true|false, "message": "...", "skipped": true? }` (skipped cuando ALLOW_EXTERNAL_TESTS=false).
