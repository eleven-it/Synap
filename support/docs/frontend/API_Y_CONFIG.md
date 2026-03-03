# API consumida y configuración

## Cliente HTTP

- **Base URL:** Construida con `VITE_API_BASE_URL` (sin barra final) + `/api`. Si `VITE_API_BASE_URL` está vacío, se usa `/api` (proxy en dev).
- **Credenciales:** `withCredentials: true` en Axios para enviar la cookie de sesión.
- **CSRF:** En cada petición se lee la cookie `csrftoken` y se envía en el header `X-CSRFToken`.
- **Idempotencia:** Para PATCH `/api/casos/:id/` y POST `/api/casos/:id/respuesta/enviar/` se genera un UUID con `crypto.randomUUID()` y se envía en el header `Idempotency-Key`. El backend puede devolver la misma respuesta sin repetir efectos si la clave ya fue usada.

## Endpoints consumidos (existentes en backend)

| Recurso | Método | Endpoint | Uso en frontend |
|--------|--------|----------|------------------|
| Auth | POST | `/api/auth/login/` | Login |
| Auth | GET | `/api/auth/me/` | Usuario actual y rol |
| Dashboard | GET | `/api/dashboard/` o `/api/stats/` | Dashboard |
| Casos | GET | `/api/casos/` | Listado (filtros, paginación) |
| Caso | GET | `/api/casos/:id/` | Detalle y contexto |
| Caso | PATCH | `/api/casos/:id/` | Cambio de estado / asignación (Idempotency-Key) |
| Timeline | GET | `/api/casos/:id/timeline/` | Mensajes y resúmenes |
| Adjuntos | GET | `/api/casos/:id/adjuntos/` | Lista con URLs firmadas (uso ampliable) |
| Respuesta preview | POST | `/api/casos/:id/respuesta/preview/` | Preview (stub en backend) |
| Respuesta enviar | POST | `/api/casos/:id/respuesta/enviar/` | Enviar respuesta (Idempotency-Key) |
| Copiloto mensajes | GET | `/api/casos/:id/copiloto/mensajes/` | Historial del copiloto por caso |
| Copiloto enviar | POST | `/api/casos/:id/copiloto/mensajes/` | Enviar mensaje al copiloto y opcionalmente guardar como conocimiento |
| Empresas | GET | `/api/empresas/` | Listado empresas |
| Empresa | GET | `/api/empresas/:id/` | Detalle (incl. sla_configs) |
| Usuarios soporte | GET | `/api/usuarios-soporte/`, `/:id/` | Listado y detalle |
| Agentes | GET | `/api/agentes/` | Lista para asignación |
| Métricas | GET | `/api/metricas/` | Métricas SLA |
| Knowledge | POST | `/api/knowledge/ingest/` | Ingesta (Admin) |
| Knowledge | GET | `/api/knowledge/search/?q=...` | Búsqueda (Admin) |

Referencia completa de request/response en [backend/API.md](../backend/API.md).

## Sección Configuración – Endpoints implementados

La sección **Configuración** (Admin) está implementada en la UI y el **backend ya expone** los endpoints siguientes. La configuración se persiste en PostgreSQL; los secretos se guardan cifrados (CONFIG_ENCRYPTION_KEY) y en GET se devuelven enmascarados.

### A) Canales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/config/channels/` | Listar config por canal (whatsapp, telegram, email). Incluir: estado (no_configurado \| parcial \| validando \| activo \| error), last_check_at, last_error. |
| POST | `/api/config/channels/` | Crear/actualizar borrador. |
| PATCH | `/api/config/channels/:id/` | Actualizar (token, webhook URL, etc.). |
| POST | `/api/config/channels/:id/test/` | Probar conexión. |
| POST | `/api/config/channels/:id/activate/` | Activar (tras validar). |
| POST | `/api/config/channels/:id/deactivate/` | Desactivar. |

### B) IA / Modelos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/config/ia/` | Config actual: proveedor, modelo, límites, prompt_version (por empresa o global). API key enmascarada. |
| PATCH | `/api/config/ia/` | Guardar. |
| POST | `/api/config/ia/test/` | Test LLM (ping o prompt de prueba). |

### C) RAG / Conocimiento

- Ingesta y búsqueda ya existen: POST `/api/knowledge/ingest/`, GET `/api/knowledge/search/`.
- Esperados para “config” desde UI:

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/config/rag/` | top_k, fuentes habilitadas, política global+empresa, cache TTL. |
| PATCH | `/api/config/rag/` | Guardar. |
| POST | `/api/config/rag/reindex/` | Disparar reindexación. |
| POST | `/api/config/rag/ingest/` | Ingesta bajo demanda. |

### D) SLA

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/config/sla/` | Listar por empresa (o extender GET /api/empresas/:id/ con sla_configs). |
| POST | `/api/config/sla/`, PATCH `/api/config/sla/:id/` | Crear/actualizar. |
| POST | `/api/config/sla/test/` | Opcional: simular vencimiento. |

### E) Storage / Adjuntos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/config/storage/` | Endpoint, bucket, region, path_style; políticas (tamaño máx, tipos, retención). Secret enmascarado. |
| PATCH | `/api/config/storage/` | Guardar. |
| POST | `/api/config/storage/test/` | Subir archivo de prueba o generar URL firmada. |

### F) Seguridad operativa

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/config/security/` | Rate limits por canal, anti-spam, política PII. |
| PATCH | `/api/config/security/` | Guardar. |
| POST | `/api/config/security/self-check/` | Ejecutar comprobaciones y devolver resultado. |

### G) Notificaciones y escalamiento

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/config/notifications/` | Gerencia/supervisores, mensajes estándar SLA, canal de alertas. |
| PATCH | `/api/config/notifications/` | Guardar. |

### H) Branding / Mensajes (opcional)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/config/branding/` | Nombre asistente, saludo, idioma (por empresa o global). |
| PATCH | `/api/config/branding/` | Guardar. |

---

Los GET de configuración deberían devolver al menos: **estado**, **last_check_at**, **last_error** (mensaje legible) y los campos editables. Los POST de test deben devolver éxito/error y un mensaje claro para mostrar en la UI.
