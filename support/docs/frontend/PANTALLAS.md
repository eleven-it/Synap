# Pantallas y flujos

## Rutas

| Ruta | Acceso | Descripción |
|------|--------|-------------|
| `/login` | Público | Inicio de sesión (usuario y contraseña) |
| `/dashboard` | Autenticado | Resumen: casos abiertos, SLA en riesgo, casos por estado |
| `/casos` | Agente/Admin | Listado de casos con filtros y paginación |
| `/casos/:id` | Agente/Admin | Detalle de caso (3 columnas) |
| `/empresas` | Admin | Listado de empresas |
| `/usuarios` | Admin | Usuarios de soporte |
| `/agentes` | Agente/Admin | Lista de agentes (para asignación) |
| `/metricas` | Agente/Admin | Métricas SLA (período, empresa opcional) |
| `/configuracion` | Admin | Hub de configuración del sistema |

## Login

- Formulario: usuario y contraseña (validación con Zod).
- POST `/api/auth/login/`; en éxito se guarda la sesión (cookie) y se redirige a `/dashboard`.
- En error (401 o 400) se muestra mensaje en pantalla (sin toasts).
- No hay UI para “recordar sesión” ni recuperación de contraseña en esta versión.

## Dashboard

- GET `/api/dashboard/` (o `/api/stats/`).
- Muestra: **Casos abiertos**, **SLA en riesgo**, y resumen **Por estado** (conteos por estado).
- Tarjetas en grid; skeletons durante la carga.

## Casos – Listado

- GET `/api/casos/` con query params: `status`, `limit`, `offset`, `ordering` (p. ej. `-created_at`).
- Tabla: número de caso, estado (chip), empresa, asignado, indicador SLA, fecha de actualización.
- Filtro por estado (dropdown). Paginación (10, 20, 50).
- Clic en fila navega a `/casos/:id`.

## Casos – Detalle (3 columnas)

Vista principal del backoffice: contexto del caso, timeline y respuesta, y copiloto IA.

### Columna 1 – Contexto

- GET `/api/casos/:id/`.
- Muestra: número de caso, estado (chip), empresa, asignado, fechas SLA.
- **Selector de estado:** PATCH `/api/casos/:id/` con `status`; se envía **Idempotency-Key** (UUID).
- Sin lógica de transiciones en el front; el backend valida y puede devolver 409 si la transición no está permitida.

### Columna 2 – Timeline y respuesta

- **Timeline:** GET `/api/casos/:id/timeline/`. Lista de mensajes y resúmenes IA ordenados por tiempo. Mensajes entrantes/salientes con estilo distinto (burbujas).
- **Caja de respuesta:** Campo de texto multilínea y botón “Enviar”. POST `/api/casos/:id/respuesta/enviar/` con `texto`; header **Idempotency-Key**. Tras éxito se invalida la query del timeline y se muestra toast.
- Los adjuntos del caso (GET `/api/casos/:id/adjuntos/`) están previstos en la API; la UI puede ampliarse para listar y descargar con las URLs firmadas.

### Columna 3 – Copiloto IA

- **Historial:** GET `/api/casos/:id/copiloto/mensajes/`. Lista de mensajes usuario/IA con indicador de “guardado como conocimiento” cuando aplique.
- **Nuevo mensaje:** Campo de texto + checkbox **“Guardar respuesta como conocimiento”** + botón Enviar. POST `/api/casos/:id/copiloto/mensajes/` con `texto` y `guardar_respuesta_como_conocimiento`. La respuesta del backend incluye `respuesta_ia`, `sugerencia_respuesta` y, si se guardó, `knowledge_chunk_id`.
- El panel está siempre asociado al caso actual; no hay copiloto “global” en esta vista (el plan contempla también endpoints globales con `case_id` opcional).

## Empresas

- GET `/api/empresas/`. Tabla: prefijo, synap_id, idioma, activa.
- Solo lectura en la implementación actual; la API permite POST/PATCH/DELETE (Admin) para ampliar CRUD desde la UI.

## Usuarios de soporte

- GET `/api/usuarios-soporte/` (opcionalmente con filtro `company`). Tabla: id, nombre, empresa.
- Pensado para Admin; la API permite CRUD completo.

## Agentes

- GET `/api/agentes/`. Tabla: usuario, email, rol (chip).
- Sirve como referencia para asignación de casos; en el detalle de caso el selector de “asignado” podría reutilizar esta lista (actualmente el cambio de estado y asignación se hace por PATCH con `assigned_to_id`).

## Métricas

- GET `/api/metricas/` con params opcionales: `desde_fecha`, `hasta_fecha`, `empresa_id`.
- Tarjetas: SLA inicios, SLA vencidos, casos resueltos, cumplimiento SLA (%).
- Selector de empresa (opcional) para filtrar.

## Configuración (Admin)

Hub con **8 áreas**, cada una en una tarjeta con:

- **Estado:** No configurado, Parcial, Validando, Activo, Error (previsto para cuando el backend exponga estado).
- **Acciones:** “Configurar” / “Editar”, “Probar” (cuando aplique), toggle “Activo” (cuando aplique).

Al pulsar “Configurar” o “Editar” se abre un **Drawer** por la derecha con el formulario o wizard correspondiente.

### A) Canales

- Drawer con **Stepper:** WhatsApp Meta, Telegram, Email SMTP/IMAP.
- Por canal: campos de token/credenciales y texto de ayuda (webhook, verify token, etc.). Los valores no se persisten hasta que el backend exponga los endpoints de config (ver API_Y_CONFIG.md).
- Botones: Atrás, Siguiente, Guardar borrador.

### B) IA / Modelos

- Campos: proveedor, API Key (password), modelo, límite de tokens.
- Botones: “Probar LLM”, “Guardar y activar”. Endpoints esperados: GET/PATCH `/api/config/ia/`, POST `/api/config/ia/test/`.

### C) RAG / Conocimiento

- top_k y descripción de fuentes (casos resueltos, human_note). Botones: Reindexar, Ingestar ahora, Cerrar.
- La ingesta y búsqueda ya existen en la API (`/api/knowledge/ingest/`, `/api/knowledge/search/`); la “config” (top_k, fuentes, cache) se documenta como endpoints esperados.

### D) SLA

- Campos: tiempo de respuesta (min), warning %, “Escalar a (gerencia)”.
- Botón “Simular vencimiento” (opcional en backend). Endpoints esperados para CRUD de config SLA desde la UI.

### E) Storage / Adjuntos

- Endpoint S3/MinIO, bucket, access key, secret key, tamaño máximo. Botones: Probar conexión, Guardar.

### F) Seguridad operativa

- Switches: rate limit por canal, anti-spam, advertencia PII. Botón “Ejecutar self-check”.

### G) Notificaciones y escalamiento

- Email de alertas, mensajes estándar para SLA por vencer y SLA vencido.

### H) Branding / Mensajes

- Nombre del asistente, mensaje de saludo, idioma por defecto.

En todas las áreas, la UI está preparada para conectar con los endpoints documentados en API_Y_CONFIG.md; no se implementa lógica de negocio en el frontend.
