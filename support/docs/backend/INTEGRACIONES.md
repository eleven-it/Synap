# Integraciones (Backend)

El backend no importa código del ERP Synap. Toda integración con sistemas externos se hace por HTTP o mediante adaptadores con interfaces bien definidas.

---

## SynapClient (API Synap)

**Módulo:** `apps.integrations.adapters.synap_client`

- **Configuración:** `SUPPORT_SYNAP_API_URL` (base URL), `SUPPORT_SYNAP_JWT_SECRET` (firma del JWT).
- **Autenticación:** JWT firmado con el secret. El cliente genera un token con claim `sub: "support-service"` y expiración (ej. 1 hora) y lo envía en `Authorization: Bearer <token>`.
- **Comportamiento:** Timeout configurable, reintentos con backoff (max_retries). Para escrituras que la API Synap soporte, se puede enviar header `Idempotency-Key`.
- **Métodos implementados:**
  - `get_empresas()` → lista de empresas (GET al endpoint acordado, ej. `/api/empresas/`).
  - `get_empresa(synap_id)` → detalle de una empresa.
- **Excepción:** `SynapClientError` (mensaje, status_code opcional, response_body).

El contrato exacto (paths, payloads) debe documentarse en función de lo que exponga la API de Synap; Support actúa solo como consumidor HTTP.

---

## Adaptadores de canal

**Módulo:** `apps.integrations.adapters.channels`

Interfaz común (clase base `BaseChannelAdapter`):

- **validate_webhook(request)** → bool. Valida la firma del webhook. Stub: devuelve True.
- **parse_webhook(request)** → `InboundMessage | None`. Parsea el cuerpo a un mensaje normalizado (channel_type, external_id, text, attachments, timestamp, raw_payload). Stub en base; TelegramAdapter implementa parseo básico de JSON.
- **send_message(external_id, text, attachments=None)** → `SendResult(success, error)`. Envía mensaje al usuario por el canal. Stub: solo log.

Implementaciones:

- **TelegramAdapter** — channel_type "telegram"; parse_webhook con estructura típica de Telegram Bot API.
- **WhatsAppAdapter** — channel_type "whatsapp"; stub.
- **EmailAdapter** — channel_type "email"; stub.

Para producción hay que implementar validación de firma (HMAC según proveedor), parseo real del body y envío vía API del proveedor (Telegram Bot API, Meta Cloud API/Twilio, SMTP u otro).

---

## Copiloto IA (RAG-only, sin alucinaciones)

**Módulo:** `apps.integrations.services.copilot_reply`

- **Función:** `copilot_reply(text, case=None, user=None, sistema=None)` → `(respuesta_ia, sugerencia_respuesta, derivado_a_humano)`.
- **Regla:** El LLM solo responde con información del RAG (base de conocimiento). No inventa datos ni alucina.
- **Sin contexto RAG:** Si RAG no está configurado, no hay embeddings o la búsqueda no devuelve chunks relevantes, no se llama al LLM. Se devuelve un mensaje estándar indicando que se derivó el caso a un agente humano y, si hay `case`, se transiciona el estado a **Derivado a humano** (vía `apps.cases.services.derive_case_to_human`).
- **Con contexto RAG:** El prompt del sistema instruye al modelo a responder únicamente con el "Contexto de la base de conocimiento" proporcionado; si la respuesta no está en ese contexto, debe indicar que no tiene la información y que se derivará a un agente.
- Los mensajes se persisten en `CopilotMessage` (role user/assistant). Las respuestas de la API de copiloto incluyen `derivado_a_humano: true` cuando se derivó el caso.

---

## Interfaces del agente IA

**Módulo:** `apps.integrations.adapters.agent_ia`

Definiciones de contrato para futura implementación real:

- **RetrievalServiceInterface** — `search(query, company_id, top_k, include_global)` → lista de fragmentos. Stub: lista vacía.
- **ToolsServiceInterface** — `execute(tool_name, params, context)` → `ToolResult(success, message, data)`. Stub: éxito genérico.
- **AgentServiceInterface** — `process_message(case_id, user_message, context)` → (respuesta_texto, acciones_ejecutadas). Stub: texto fijo.

Permiten sustituir luego por implementaciones con LLM, pgvector (RAG) y tools reales sin cambiar la capa de orquestación que los use.
