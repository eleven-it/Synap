# Synap Support – Plan Técnico

**Fuente funcional de verdad:** [support/plan_support.md](../plan_support.md). Este documento no reescribe ni resume ese plan; baja al diseño técnico y constructivo para que un equipo senior pueda implementar el sistema. Todas las decisiones funcionales (propósito, canales, usuarios, casos, estados, SLA, IA, conversaciones, backoffice, seguridad, infraestructura) provienen exclusivamente de ese archivo.

---

## 1. Arquitectura técnica detallada

### 1.1 Componentes y responsabilidades

- **Backend Django (API REST):**
  - Sirve la API REST consumida por el frontend React (autenticación, CRUD, acciones).
  - Expone endpoints de webhook por canal (Telegram, WhatsApp, Email); valida firma, parsea cuerpo, normaliza a mensaje interno y delega a la capa de servicios.
  - Orquesta flujo de casos (crear/continuar, transiciones de estado), ejecución del agente IA (RAG + tool-calling), y envío de respuestas por canal.
  - Encola en Celery: ingesta/indexado RAG, generación de resúmenes, notificaciones SLA, reintentos de envío, cierre por inactividad.
  - No importa código del ERP Synap; toda integración con Synap es vía cliente HTTP (SynapClient) con JWT.

- **Frontend React SPA:**
  - Único consumidor de la API del backend para el backoffice. Solo usuarios con rol Admin, Agente o Supervisor. No hay UI para el usuario final.
  - Pantallas: Dashboard, listado de casos, detalle de caso (timeline + conversación), empresas (SLA, idioma), usuarios y canales, agentes, métricas básicas; chat copiloto (agente↔IA) y envío de respuesta multicanal con preview.
  - Renderizado en el cliente; routing SPA; estado servidor con TanStack Query; build estático servido por nginx o por el backend en producción.

- **Workers Celery:**
  - Misma base de código que el backend; comando de arranque: worker y beat.
  - Worker: ejecuta tareas de ingesta de conocimiento (chunking, embeddings, escritura en pgvector), generación de resúmenes de conversación, jobs de SLA (evaluar warning/vencimiento, notificar, escalar), reintentos de envío por canal, borrado programado de adjuntos (retención 12 meses), cierre por inactividad.
  - Beat: programa las tareas periódicas (SLA cada 1–5 min, retención, etc.) según cron/interval.

- **PostgreSQL + pgvector:**
  - Base de datos principal del servicio: empresas, usuarios de soporte, identidades de canal, casos, mensajes, resúmenes IA, adjuntos (metadata), configuración SLA, eventos de auditoría, contador de casos por empresa.
  - Extensión pgvector: tabla(s) de embeddings (vector, texto del chunk, metadata: empresa_id, tipo, source_id) para RAG. Índice HNSW o IVFFlat sobre la columna vector; filtro por empresa_id en las queries de retrieval.

- **Redis:**
  - Broker de Celery (cola de tareas).
  - Cache: sesiones de usuario (si se usan), cache de corta duración para resultados de retrieval RAG (clave por hash de query+empresa_id), y contadores/ventanas para rate limiting por canal e IP.

- **S3 compatible (MinIO en dev/staging, S3 o compatible en prod):**
  - Almacenamiento de adjuntos de mensajes. Clave de objeto por empresa/caso/mensaje (o UUID). No se exponen URLs permanentes; el backend genera URLs firmadas (presigned) con expiración para lectura/descarga.
  - En producción: versionado del bucket habilitado para DR.

- **Adaptadores de canal:**
  - Interfaz común: (1) validar webhook (firma), (2) parsear cuerpo a mensaje normalizado (canal, id_externo, texto, adjuntos, timestamp), (3) enviar respuesta (texto, adjuntos opcionales). Implementaciones: Telegram (Bot API), WhatsApp (Meta Cloud API o Twilio), Email (entrada por webhook o polling según proveedor; salida SMTP; threading por subject con [SUP-PREFIJO-NNN]).

### 1.2 Flujo de datos (resumen)

- Mensaje entrante → webhook → validación → persistencia mensaje + resolución de caso (crear/continuar) → disparo de agente IA o cola de humano.
- Frontend → API → lectura/escritura en PostgreSQL; mutaciones que requieran jobs → encolar a Celery vía Redis.
- Agente IA: contexto (historial + resúmenes + RAG) → LLM → respuesta y/o tool-calling → persistencia y/o envío por canal; en error → mensaje estándar + derivación a humano.
- SLA: transición a “Asignado a agente humano” → evento inicio SLA; transición a “Esperando respuesta del usuario” → pausa; job periódico (Beat) evalúa casos activos y dispara warning (70–80%) o vencimiento (escalado, notificación, auditoría).

### 1.3 Capas internas del backend

- **Domain:** Entidades y reglas puras (estados de caso, transiciones permitidas, numeración SUP-{PREFIJO}-000123, reglas de SLA). Sin I/O.
- **Services:** Casos de uso (crear caso, asignar, cambiar estado, ejecutar agente, calcular SLA, enviar mensaje). Orquestan domain y adapters.
- **Adapters:** SynapClient (HTTP + JWT), cada canal (Telegram, WhatsApp, Email), vector store (pgvector), almacenamiento de archivos (S3). Interfaz estable para sustituir o ampliar sin tocar el núcleo.

---

## 2. Layout del repositorio /support

- **`/support/backend`:** Proyecto Django. Incluye: configuración (settings por entorno: local, dev, staging, prod), apps de dominio (empresas, usuarios, canales, casos, mensajes, ia, sla, auditoría, adjuntos), SynapClient en capa de adapters, tareas Celery. No hay imports desde fuera de `support`.

- **`/support/frontend`:** Aplicación React: código fuente (componentes, rutas, estado, llamadas a API), build de producción. Variable de entorno para la URL base de la API del backend.

- **`/support/docker`:** `docker-compose.yml` (y opcionalmente `Dockerfile` por servicio o multi-stage). Incluye servicios: backend, worker, beat, postgres (con pgvector), redis, minio (dev/staging), frontend (build estático) y opcional nginx como reverso. Archivo `.env.example` con todas las variables necesarias documentadas.

- **`/support/docs`:** `plan_support.md` (plan funcional, fuente de verdad) y `technical_plan.md` (este documento). Opcional: README con instrucciones de arranque con Docker.

Regla estricta: en todo el árbol `/support` está prohibido importar desde el resto del repositorio (ERP Synap). Dependencias solo a librerías públicas y al propio código bajo `/support`.

---

## 3. Modelo de datos completo

### 3.1 Entidades, campos y relaciones

- **Empresa**
  - id (PK), synap_id (referencia al ERP, único), prefijo (string, para numeración ej. "ACME"), idioma (código), activo (boolean), created_at, updated_at.
  - Relaciones: 1:N con Caso, UsuarioSoporte, ConfigSLA; 1:1 o N:1 con contador de casos (tabla o fila de contador por empresa).

- **UsuarioSoporte** (usuario final que recibe soporte)
  - id (PK), empresa_id (FK Empresa), nombre (string), idioma (código), autorizado (boolean), created_at, updated_at.
  - Relación: 1:N con IdentidadCanal. Alta y autorización solo desde backoffice.

- **IdentidadCanal**
  - id (PK), usuario_soporte_id (FK UsuarioSoporte), tipo_canal (enum: telegram, whatsapp, email), id_externo (string: telegram_user_id, E.164 o email). Constraint único (tipo_canal, id_externo) para resolver mensaje entrante → usuario.

- **Caso**
  - id (PK), empresa_id (FK Empresa), numero_secuencial (entero, por empresa), numero_display (string generado: "SUP-{prefijo}-{numero_secuencial:06d}"), estado (enum: Iniciado, En_analisis_IA, Esperando_respuesta_usuario, Derivado_a_humano, Asignado_a_agente_humano, En_proceso_humano, Resuelto, Cerrado, Reabierto), asignado_a_id (FK a usuario backoffice, nullable), sla_inicio_at (nullable), sla_limite_at (nullable), sla_pausado_desde (nullable), created_at, updated_at.
  - Relaciones: 1:N Mensaje, ResumenIA, EventoAuditoria; N:1 Empresa, asignado_a (agente).

- **Mensaje**
  - id (PK), caso_id (FK Caso), tipo_canal, id_externo_canal (o FK IdentidadCanal), remitente (enum: usuario, sistema, agente, ia; o FK si agente), contenido (texto), direccion (entrante | saliente), created_at (timestamp, inmutable). Sin campos updated_at; no se editan ni borran.

- **ResumenIA**
  - id (PK), caso_id (FK Caso), desde_mensaje_id (FK Mensaje, nullable), hasta_mensaje_id (FK Mensaje, nullable), resumen_texto (texto), modelo_versión (string), created_at.

- **Adjunto**
  - id (PK), mensaje_id (FK Mensaje), bucket (string), key (string), content_type, size_bytes, nombre_original. URLs generadas bajo demanda (presigned) con expiración.

- **EventoAuditoria**
  - id (PK), case_id (FK Caso, nullable), empresa_id (FK Empresa), tipo_evento (string: creacion_caso, cambio_estado, asignacion, mensaje_recibido, mensaje_enviado, accion_ia, sla_inicio, sla_pausa, sla_reanudacion, sla_warning, sla_vencido, reapertura, etc.), payload (JSONB), actor_id (nullable), created_at. Solo inserciones; append-only.

- **ConfigSLA**
  - id (PK), empresa_id (FK Empresa), tipo_caso (string, ej. "default"), tiempo_respuesta_minutos (entero), warning_pct (entero, 70 u 80).

- **ContadorCasosEmpresa** (o equivalente)
  - empresa_id (FK, único), ultimo_numero (entero). Se incrementa en transacción (o select_for_update) al crear un caso; con ese valor se forma numero_secuencial y numero_display.

### 3.2 Índices

- Empresa: (synap_id) UNIQUE.
- IdentidadCanal: UNIQUE (tipo_canal, id_externo); índice por usuario_soporte_id.
- Caso: (empresa_id, estado), (asignado_a_id, estado), (created_at), (sla_limite_at) donde estado permita SLA activo.
- Mensaje: (caso_id, created_at) para timeline ordenado.
- ResumenIA: (caso_id).
- Adjunto: (mensaje_id).
- EventoAuditoria: (case_id, created_at), (empresa_id, tipo_evento, created_at). Si el volumen crece, considerar particionado por created_at (mensual/anual).
- Tabla de embeddings (RAG): índice HNSW o IVFFlat sobre la columna vector; índice (empresa_id, tipo) para filtros; dimensiones según modelo de embeddings.

### 3.3 Numeración de casos

- Formato: SUP-{PREFIJO_EMPRESA}-000123. Prefijo viene de Empresa.prefijo; el número de 6 dígitos viene del contador por empresa. Generación en la misma transacción que la inserción del Caso: lock/update del contador, luego insert del caso con ese numero_secuencial y numero_display calculado.

---

## 4. Diseño técnico del workflow de casos y SLA (runtime + scheduler)

### 4.1 Estados y transiciones (runtime)

- Estados según plan_support.md: Iniciado, En análisis IA, Esperando respuesta del usuario, Derivado a humano, Asignado a agente humano, En proceso (humano), Resuelto, Cerrado, Reabierto.
- Transiciones válidas: definidas en dominio (máquina de estados). Ejemplos: Iniciado → En_analisis_IA; En_analisis_IA → Esperando_respuesta_usuario | Derivado_a_humano; Esperando_respuesta_usuario → En_analisis_IA | Derivado_a_humano; Derivado_a_humano → Asignado_a_agente_humano; Asignado_a_agente_humano → En_proceso_humano; En_proceso_humano → Esperando_respuesta_usuario | Resuelto; Resuelto → Cerrado | Reabierto; Cerrado → Reabierto; Reabierto → En_analisis_IA | Derivado_a_humano.
- En cada transición: actualizar Caso.estado (y campos de SLA si aplica), insertar EventoAuditoria (tipo cambio_estado, payload con estado_anterior, estado_nuevo, actor).

### 4.2 Eventos que disparan lógica (runtime)

- **Mensaje entrante:** Resolver IdentidadCanal → UsuarioSoporte; si no existe o no autorizado, rechazar o dar de alta según backoffice. Resolver caso abierto del usuario o crear uno nuevo (numeración); insertar Mensaje; según estado y configuración, invocar agente IA (o poner en cola de humano). Posible reapertura si el mensaje referencia un caso Cerrado/Resuelto (por subject email o por regla de negocio).
- **Asignación a agente:** Transición a Asignado_a_agente_humano. Disparar inicio SLA: leer ConfigSLA (empresa, tipo_caso), setear sla_inicio_at y sla_limite_at, insertar EventoAuditoria sla_inicio.
- **Cambio a Esperando_respuesta_usuario:** Setear sla_pausado_desde (timestamp actual); el tiempo hasta que salga de este estado no cuenta para el límite. Insertar evento sla_pausa. Al salir de este estado, clear sla_pausado_desde y recalcular sla_limite_at si la política es “solo tiempo activo” (opcional); insertar evento sla_reanudacion.

### 4.3 Scheduler (Celery Beat)

- **Job SLA (cada 1–5 minutos):** Seleccionar casos con estado Asignado_a_agente_humano o En_proceso_humano, con SLA activo (sla_inicio_at no nulo y no en pausa, o pausa descontada). Para cada caso: calcular tiempo consumido vs tiempo_respuesta; si porcentaje >= warning_pct y aún no se envió warning → enviar notificación interna (y al agente), insertar evento sla_warning; si tiempo consumido >= tiempo_respuesta → marcar vencido: notificar usuario, escalar a gerencia (evento y notificación), insertar evento sla_vencido.
- **Job cierre por inactividad:** Periódico (ej. diario). Casos en estados “esperando respuesta” o “en proceso” con último mensaje más antiguo que umbral (configurable) → transición a Cerrado (o Resuelto luego Cerrado) e insertar evento.
- **Job retención adjuntos:** Periódico. Borrar de S3 y de tabla Adjunto los registros cuya fecha del mensaje (o created_at) supere 12 meses.

### 4.4 Métricas SLA

- Calcular desde EventoAuditoria: sla_inicio, sla_vencido, cambio_estado a Resuelto/Cerrado. Por empresa y por agente: porcentaje cumplido vs vencido, tiempo medio hasta primera respuesta y hasta cierre. Se pueden exponer en endpoint de métricas y en Dashboard.

---

## 5. Diseño técnico del agente IA + RAG

### 5.1 Servicios internos

- **AgentService (orquestador):** Recibe mensaje de usuario y case_id. Obtiene historial (ConversationService) y contexto RAG (RetrievalService con empresa_id y opción global+empresa). Construye prompt (versión por empresa si hay versionado). Invoca LLM; si el LLM devuelve tool calls, invoca ToolsService por cada una y vuelve a llamar al LLM con resultados hasta respuesta final. Persiste respuesta y/o efectos (cambio estado, asignación, nota, notificación). En cualquier excepción o error de LLM/tool: responde mensaje estándar al usuario y transiciona caso a Derivado_a_humano; registra en auditoría.
- **RetrievalService:** Dado query (texto) y empresa_id: opcionalmente cache Redis (clave hash(query, empresa_id), TTL corto). Si no cache hit: generar embedding del query, buscar en pgvector top-k vectores más cercanos con filtro (empresa_id o global). Devolver lista de fragmentos (texto + metadata). Interfaz tal que el vector store pueda sustituirse (post-MVP) por otro proveedor sin cambiar el resto.
- **ToolsService:** Registro de herramientas con nombre, parámetros (schema) y función de ejecución. Herramientas: cambiar_estado (case_id, nuevo_estado), asignar_agente (case_id, agente_id), crear_nota (case_id, texto), notificar_usuario (case_id, texto, canal_opcional), y las que llamen a SynapClient (según contrato API). Validación de parámetros y permisos; retorno estructurado (éxito/error, mensaje) para inyectar en el siguiente turno del LLM.
- **ConversationService:** Devuelve para un caso la lista de mensajes (y resúmenes) ordenados por tiempo; opcionalmente truncada a últimos N mensajes + resúmenes de bloques anteriores para no superar límite de contexto del LLM.
- **KnowledgeIngestionService:** Lee fuentes (casos resueltos con conversación/resumen; opcionalmente código Synap si se expone). Chunking (por ventana de tokens o por unidad lógica); genera embeddings; escribe en tabla pgvector con metadata (empresa_id, tipo, source_id). Se ejecuta vía tarea Celery (programada o bajo demanda).

### 5.2 RAG: ingesta

- Fuentes: casos resueltos (texto de mensajes + resúmenes existentes); código Synap solo si está disponible vía API o export. Chunking: para conversaciones por turnos o por ventana; para código por función/archivo o ventana con overlap. Embedding: mismo modelo que se use en retrieval (dimensión fija). Metadata obligatoria: empresa_id (o null para global), tipo (caso | codigo), source_id (id del caso o del artefacto).

### 5.3 RAG: retrieval

- Top-k configurable (ej. 5–10). Filtro: empresa_id = X o (empresa_id = X OR empresa_id IS NULL) para “global+empresa”. Cache Redis con TTL corto (ej. 60–300 s). Criterios de salida para migrar a vector DB dedicada (post-MVP): por ejemplo latencia p95 o volumen de vectores por encima de umbral; la interfaz RetrievalService debe permitir cambiar el backend sin tocar AgentService.

### 5.4 Tool-calling

- Contratos (nombre, parámetros): cambiar_estado, asignar_agente, crear_nota, notificar_usuario, más las acciones Synap que se documenten en el contrato API. Fallback: cualquier error no recuperable → mensaje estándar al usuario + transición a Derivado_a_humano + log y auditoría.

**Política de idempotencia de tools (evitar efectos dobles si el LLM repite una tool):**

- **cambiar_estado(case_id, nuevo_estado):** Idempotente. Antes de aplicar la transición, comprobar el estado actual del caso; si el caso ya está en `nuevo_estado`, devolver éxito sin volver a escribir ni generar nuevo evento de auditoría. Así, si el LLM invoca dos veces “cambiar a Resuelto”, solo la primera tiene efecto.
- **asignar_agente(case_id, agente_id):** Idempotente. Si el caso ya está asignado a ese mismo `agente_id`, devolver éxito sin actualizar ni disparar de nuevo inicio de SLA. Si está asignado a otro agente, se puede considerar actualización (reasignación) y devolver éxito; documentar el comportamiento deseado (¿reasignar siempre o solo si es la misma invocación duplicada?).
- **Acciones contra Synap (vía SynapClient):** Todas las escrituras deben usar **idempotency key** si la API de Synap lo soporta (header o cuerpo). La key puede derivarse de (case_id, tool_name, idempotency_salt o timestamp de turno del agente) para que la misma decisión del LLM en un mismo turno no cree registros duplicados en Synap. En lecturas no aplica idempotencia; en escrituras sin soporte de key en Synap, documentar el riesgo de duplicados y mitigar en la medida posible (ej. comprobar si el recurso ya existe antes de crear).
- **crear_nota(case_id, texto):** No es estrictamente idempotente (cada invocación puede ser una nota nueva). Si se quiere evitar notas duplicadas por repetición del LLM, se puede usar una key por (case_id, hash(texto), ventana de tiempo) y devolver éxito sin insertar si ya existe nota idéntica reciente; opcional según criterio de producto.
- **notificar_usuario(case_id, texto, canal_opcional):** No idempotente por naturaleza (cada envío es un mensaje). El rate limiting y la deduplicación por canal ya mitigan abusos; no es necesario bloquear una segunda invocación idéntica en el mismo turno si el producto acepta “doble notificación” en casos raros.

### 5.5 Versionado de prompts

- Prompts (sistema y usuario) versionados en DB o en config (versión por id). Empresa puede tener asociada una versión de prompt (o “default”). AgentService carga el prompt según empresa_id para rollout por empresa sin desplegar código.

---

## 6. Contrato API backend ↔ frontend

### 6.1 Autenticación

- **MVP:** El backend emite credencial para usuarios del backoffice (Admin, Agente, Supervisor). Opciones válidas: (1) **Sesión:** cookie de sesión (sessionid); el frontend envía cookies en cada petición; el backend valida sesión y asocia usuario y rol. (2) **JWT:** token en header `Authorization: Bearer <token>`; el backend valida firma y claims (user_id, rol, exp) y autoriza. Elegir una de las dos para MVP; no es necesario soportar ambas a la vez.
- **Post-MVP:** SSO (SAML, OIDC o login delegado en Synap) puede añadirse como otro mecanismo de autenticación para agentes; el backend seguiría emitiendo sesión o JWT interno tras validar la identidad con el IdP. No es requisito para arrancar.

### 6.2 Health endpoint

- **GET /api/health** — Sin autenticación. Respuesta **200** y cuerpo JSON con estado básico del servicio para Docker healthchecks y monitoreo.
  - Campos mínimos: `status` ("ok" | "degraded" | "error"), `db` ("ok" | "error"), `redis` ("ok" | "error"). Opcional: `version` o `environment`.
  - Comportamiento: el backend ejecuta una comprobación ligera a PostgreSQL (ej. `SELECT 1` o conexión viva) y a Redis (ej. PING). Si ambos responden, `status: "ok"` y `db`, `redis: "ok"`. Si uno falla, `status: "degraded"` o `"error"` y el componente correspondiente en `"error"`. No debe depender de servicios opcionales (Synap, S3) para marcar 200 cuando DB y Redis están bien.
  - Uso: healthcheck del contenedor backend (`curl -f http://localhost:8000/api/health` hasta 200) y comprobaciones de disponibilidad desde un load balancer o orquestador.

### 6.3 Endpoints mínimos por pantalla

- **Dashboard:** GET /api/dashboard o /api/stats. Response: resumen de casos (totales por estado, abiertos, en riesgo SLA, métricas básicas). JSON con contadores y listas acotadas.
- **Listado de casos:** GET /api/casos. Query params: estado, empresa_id, asignado_a_id, desde_fecha, hasta_fecha, ordering (ej. -created_at), limit, offset (o cursor). Response: { count, results: [ { id, numero_display, estado, empresa, asignado_a, sla_*, updated_at, ... } ] }.
- **Detalle de caso:** GET /api/casos/{id}. Response: caso completo + timeline (mensajes + resúmenes ordenados por tiempo). GET /api/casos/{id}/adjuntos: lista de adjuntos con URL firmada (expiración corta) por ítem.
- **Empresas:** GET /api/empresas, GET /api/empresas/{id}, POST /api/empresas, PATCH /api/empresas/{id}, DELETE si aplica. Incluir en el recurso empresa: prefijo, idioma, config SLA (o subrecurso).
- **Usuarios y canales:** GET /api/usuarios-soporte (query empresa_id opcional), GET /api/usuarios-soporte/{id} con identidades de canal. POST/PATCH para crear/editar usuario e identidades (backoffice).
- **Agentes:** GET /api/agentes. Lista de usuarios backoffice con rol Agente/Supervisor/Admin para asignación y filtros.
- **Métricas:** GET /api/metricas. Query params: desde_fecha, hasta_fecha, empresa_id. Response: métricas de SLA (cumplido/vencido), latencia, uso por empresa, costos IA si se exponen.
- **Copiloto IA:** POST /api/copiloto/mensaje. Body: { case_id (opcional), texto }. Response: { respuesta_ia, sugerencia_respuesta (opcional) }. GET /api/copiloto/historial o por case_id: historial del chat agente↔IA.
- **Respuesta multicanal:** POST /api/casos/{id}/respuesta/preview. Body: { texto, adjuntos (ids o archivos) }. Response: preview por canal. POST /api/casos/{id}/respuesta/enviar. Body: { texto, adjuntos }. Response: { resultado_por_canal: { canal, exito, error? } }.
- **Acciones sobre caso:** PATCH /api/casos/{id}: cambiar estado, asignado_a_id (asignar). Validación de transiciones en backend; 409 si transición no permitida.

### 6.4 Payloads y paginación

- Request/response en JSON. Paginación: limit (default 20, max 100), offset o cursor. Filtros como query params. Respuestas de lista: results, count, next/previous (URL o cursor).

### 6.5 Realtime (MVP)

- Polling: el frontend puede hacer GET /api/casos/{id} o GET /api/casos/{id}/timeline cada N segundos cuando la pantalla de detalle está abierta, para actualizar timeline y estado SLA. Incluir en el recurso caso campos derivados de SLA (ej. porcentaje consumido, segundos restantes) para mostrar en UI sin lógica pesada en cliente.

### 6.6 Errores normalizados

- HTTP: 400 (validación), 401 (no autenticado), 403 (permiso denegado), 404 (recurso no encontrado), 409 (conflicto, ej. transición de estado inválida), 429 (rate limit), 5xx (error interno).
- Cuerpo: { "code": "CODIGO_INTERNO", "message": "Mensaje legible", "details": [] }. Códigos internos ej.: CASE_STATE_TRANSITION_INVALID, UNAUTHORIZED_CHANNEL, RATE_LIMIT_EXCEEDED. El frontend usa code para mensajes o comportamientos específicos.

---

## 7. Diseño técnico del frontend React

### 7.1 Stack y enrutado

- React con router (React Router). Rutas: / (redirect), /login, /dashboard, /casos, /casos/:id, /empresas, /usuarios, /agentes, /metricas. Rutas protegidas según autenticación; visibilidad y acciones según rol (Admin, Agente, Supervisor).

### 7.2 Estado

- TanStack Query para todos los datos que vienen del backend (casos, detalle, empresas, usuarios, agentes, métricas, historial copiloto). Mutations para crear/actualizar; invalidación de queries relacionadas tras mutación. Estado local mínimo para formularios y UI transitoria.

### 7.3 Layout y componentes clave

- **Dashboard:** Página con widgets: resumen de casos (abiertos, por estado), SLA (en riesgo, vencidos), métricas básicas. Layout en grid o columnas; datos vía GET /api/dashboard o /api/stats.
- **Lista de casos:** Tabla o cards con filtros (estado, empresa, asignado), ordenación y paginación. Virtualización (ej. react-window) si la lista puede ser muy larga. Datos: GET /api/casos con query params.
- **Detalle de caso (3 columnas):** (1) Columna izquierda: datos del caso (numero_display, estado, empresa, asignado_a, fechas SLA, botones asignar/cambiar estado). (2) Columna central: timeline de mensajes y resúmenes (scroll, ordenado por tiempo; carga incremental si se implementa). (3) Columna derecha: panel de redacción de respuesta (texto, adjuntos, preview por canal, enviar) y bloque Copiloto IA (chat agente↔IA, historial, input para nuevo mensaje; mostrar sugerencia de respuesta para copiar/pegar o “usar y editar”).
- **Copiloto IA:** Componente de chat: lista de mensajes (agente, IA), input, envío POST /api/copiloto/mensaje; opcionalmente GET /api/copiloto/historial. Respuesta del backend puede incluir sugerencia_respuesta para el mensaje al usuario.
- **Respuesta multicanal:** Formulario (texto, adjuntos) + preview (POST preview) + botón enviar (POST enviar). Mostrar resultado por canal (éxito/error).
- **Empresas, Usuarios, Agentes, Métricas:** Páginas CRUD o listado/detalle según endpoints anteriores; control por rol (solo Admin para empresas/usuarios si se define así).

### 7.4 Accesibilidad y performance

- Lazy-loading de rutas (React.lazy + Suspense). Virtualización de listas largas. Skeletons o placeholders en carga. Atributos ARIA y estructura semántica donde aplique. Evitar re-renders innecesarios (memo, estructura de queries).

### 7.5 Roles

- Admin: acceso completo. Agente: sus casos, asignación, respuesta, copiloto. Supervisor: visibilidad ampliada y métricas. El backend aplica los mismos permisos; el frontend oculta o deshabilita acciones no permitidas según el rol obtenido tras login.

### 7.6 Microinteracciones

- Estados de carga (spinner/skeleton) en datos y en botones durante mutations. Optimistic UI donde sea seguro (ej. cambio de estado local). Toasts o mensajes inline para éxito/error en envío de mensajes y asignaciones.

---

## 8. Docker Compose detallado

### 8.1 Servicios

- **backend:** Imagen Django (o multi-stage build). Comando: gunicorn o runserver en dev. Puertos: 8000. Dependencias: postgres, redis. Variables de entorno inyectadas (ver lista). Volumen opcional para código en dev (mount del código). Healthcheck: GET /api/health o similar (200).

- **worker:** Misma imagen que backend. Comando: celery -A config worker. Dependencias: redis, postgres. Mismas env vars que backend. Sin puertos. Healthcheck opcional: celery inspect ping.

- **beat:** Misma imagen que backend. Comando: celery -A config beat. Dependencias: redis. Env vars como backend. Sin puertos.

- **postgres:** Imagen oficial PostgreSQL con extensión pgvector (imagen que incluya pgvector o init script que ejecute CREATE EXTENSION vector). Puerto: 5432. Variables: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD. Volumen nombrado para persistencia de datos. Healthcheck: pg_isready.

- **redis:** Imagen oficial Redis. Puerto: 6379. Volumen opcional para persistencia. Healthcheck: redis-cli ping.

- **minio:** Solo en dev/staging. Imagen MinIO. Puertos: 9000 (API), 9001 (consola). Volumen para datos. Variables: MINIO_ROOT_USER, MINIO_ROOT_PASSWORD. En prod se usa S3 externo (no servicio en compose).

- **frontend:** En producción: build estático (npm run build); servir con nginx o con el mismo backend (whitenoise/django). Si se usa servicio aparte: imagen nginx con el build copiado; puerto 80. En dev: servicio de desarrollo (npm run dev) con proxy al backend; no necesario en mismo compose si se corre en host.

- **nginx (opcional):** Reverso proxy. Puerto 80/443. Upstream: backend (y opcionalmente frontend estático). SSL según entorno. Depende de backend (y frontend si aplica).

### 8.2 Variables de entorno (lista)

- Base de datos: DATABASE_URL o POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD.
- Redis: REDIS_URL o REDIS_HOST, REDIS_PORT.
- S3/MinIO: S3_ENDPOINT_URL (MinIO en dev), S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET_NAME, S3_REGION (opcional).
- Synap: SUPPORT_SYNAP_API_URL, SUPPORT_SYNAP_JWT_SECRET (o mecanismo de token).
- Canales: TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET; WHATSAPP_* según proveedor; EMAIL_* (SMTP, etc.).
- IA: LLM_API_KEY, LLM_MODEL; EMBEDDINGS_API_KEY si es distinto.
- App: SECRET_KEY, DEBUG, ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS, ENVIRONMENT (local|dev|staging|prod).

### 8.3 Volúmenes

- postgres_data: persistencia de PostgreSQL.
- redis_data (opcional): persistencia de Redis.
- minio_data: datos de MinIO en dev.
- Ningún volumen de código en prod (código dentro de la imagen).

### 8.4 Healthchecks

- **Backend:** GET /api/health (sin auth). Se considera healthy si responde 200 con cuerpo que indique `db: "ok"` y `redis: "ok"` (véase sección 6.2). Comando típico: `curl -f http://localhost:8000/api/health` o equivalente en el healthcheck del contenedor.
- Postgres: pg_isready.
- Redis: redis-cli ping.
- Worker/Beat: opcional celery inspect ping o comprobar que las tareas se encolan.

---

## 9. Estrategia de independencia (mover /support a repo separado)

- **Objetivo:** Poder mover la carpeta `/support` a un repositorio nuevo y desplegar Support sin el ERP Synap en el mismo repo.

- **Reglas ya aplicadas:** (1) Cero imports desde el resto del repo; (2) integración con Synap solo vía HTTP (SynapClient); (3) configuración por variables de entorno (URL Synap, JWT, etc.); (4) documentación del contrato API Synap en support/docs (endpoints que Support espera, autenticación, ejemplos de request/response).

- **Pasos al independizar:** (1) Copiar o mover todo el árbol `/support` al nuevo repo. (2) Ajustar .env y documentación: SUPPORT_SYNAP_API_URL y SUPPORT_SYNAP_JWT_SECRET (o equivalente) para apuntar al Synap desplegado en otro lugar. (3) CI/CD del nuevo repo: build de imágenes desde /support/docker (o /support/backend y /support/frontend), tests, lint, deploy. No se requieren cambios de diseño interno en backend/frontend; la capa SynapClient ya aísla la integración.

- **Contrato Synap:** Documentar en support/docs (ej. CONTRATO_API_SYNAP.md) los endpoints que Support consume (listar empresas, validar usuario, y los que usen las tools), método de JWT (firmado, claims, renovación), idempotencia en escrituras y códigos de error. Así, quien despliegue Support puede implementar o exponer ese contrato en el lado Synap.

---

## 10. Checklist técnico de implementación

- **Layout repo:** Crear /support/backend, /support/frontend, /support/docker, /support/docs; plan_support.md y technical_plan.md en docs. Sin imports desde fuera de support.

- **Backend – Modelo de datos:** Modelos Django para Empresa, UsuarioSoporte, IdentidadCanal, Caso, Mensaje, ResumenIA, Adjunto, EventoAuditoria, ConfigSLA, contador por empresa. Migraciones; extensión pgvector y tabla de embeddings. Índices según sección 3.

- **Backend – API casos:** CRUD casos con numeración SUP-{PREFIJO}-000123 en transacción; listado con filtros y paginación; transiciones de estado con validación y registro en EventoAuditoria.

- **Backend – API mensajes y timeline:** Persistencia inmutable de mensajes; endpoint de timeline por caso (mensajes + resúmenes ordenados). Adjuntos: metadata en BD; generación de URLs firmadas bajo demanda.

- **Backend – SynapClient:** Cliente HTTP con JWT (obtención o generación según contrato); al menos un endpoint (ej. empresas) integrado; retry y backoff; tests con mock de Synap.

- **Canales:** Al menos un canal (ej. Telegram) end-to-end: webhook con validación de firma, parseo a mensaje normalizado, resolución de usuario/caso, persistencia de mensaje, envío de respuesta. Deduplicación por id externo del mensaje.

- **SLA – Runtime:** Al asignar agente → setear sla_inicio_at y sla_limite_at desde ConfigSLA; al pasar a Esperando_respuesta_usuario → sla_pausado_desde; al salir → clear pausa y opcionalmente recalcular límite. Eventos sla_inicio, sla_pausa, sla_reanudacion en EventoAuditoria.

- **SLA – Scheduler:** Tarea Celery Beat cada 1–5 min: casos con SLA activo; si porcentaje >= warning_pct → notificación + evento sla_warning; si vencido → notificar usuario, escalar gerencia, evento sla_vencido.

- **IA – RAG:** Pipeline de ingesta (casos resueltos; opcional código): chunking, embeddings, escritura en pgvector con metadata. RetrievalService: top-k, filtro empresa/global, cache Redis opcional. Interfaz desacoplada del vector store.

- **IA – Agente:** AgentService que orquesta ConversationService, RetrievalService, LLM y ToolsService. Tools: cambiar_estado, asignar_agente, crear_nota, notificar_usuario, y las que llamen a Synap. Fallback a mensaje estándar + Derivado_a_humano en error. Versionado de prompts por empresa (config o DB).

- **Frontend – Pantallas:** Dashboard, lista de casos (filtros, paginación), detalle de caso (3 columnas: datos, timeline, acciones + copiloto). Empresas, usuarios/canales, agentes, métricas según permisos. Login y rutas protegidas por rol.

- **Frontend – Copiloto y respuesta:** Chat con POST/GET copiloto; envío de respuesta con preview y enviar. Mostrar sugerencia de respuesta del IA cuando venga en la respuesta.

- **Docker Compose:** Servicios backend, worker, beat, postgres (pgvector), redis, minio (dev), frontend (build estático) y opcional nginx. .env.example con todas las variables. Healthchecks. Criterio: docker-compose up deja el sistema operativo para desarrollo.

- **Docs y CI:** README en /support con instrucciones de arranque. Contrato API Synap documentado en support/docs. CI: build de imágenes, tests backend y frontend, lint; deploy manual aprobado.

- **Definition of done por ítem:** Tests pasan; lint sin errores; documentación actualizada. Revisión de código antes de cerrar cada ítem.
