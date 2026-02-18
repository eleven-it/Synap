# Modelo de datos (Backend)

## Tablas y entidades

### companies (Empresa)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | PK | |
| synap_id | VARCHAR(64) UNIQUE | Referencia al ERP (solo integración vía API) |
| prefix | VARCHAR(32) | Prefijo para numeración de casos (ej. ACME) |
| language | VARCHAR(10) | Idioma por defecto |
| is_active | BOOLEAN | |
| created_at, updated_at | TIMESTAMP | |

**Tabla:** `support_company`

---

### support_users (Usuario de soporte)

Usuario final que recibe soporte. Asociado a una empresa. Alta y autorización solo desde backoffice.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | PK | |
| company_id | FK → companies | |
| name | VARCHAR(255) | |
| language | VARCHAR(10) | |
| is_authorized | BOOLEAN | |
| created_at, updated_at | TIMESTAMP | |

**Tabla:** `support_support_user`

---

### support_users (Identidad de canal)

Una entrada por canal (telegram, whatsapp, email). Constraint único `(channel_type, external_id)`.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | PK | |
| support_user_id | FK → support_support_user | |
| channel_type | VARCHAR(20) | telegram, whatsapp, email |
| external_id | VARCHAR(255) | telegram_user_id, E.164 o email |
| metadata | JSONB | |
| created_at | TIMESTAMP | |

**Tabla:** `support_channel_identity`

---

### agents (Perfil de agente)

Rol del usuario backoffice (Django User). OneToOne con `auth_user`.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | PK | |
| user_id | FK → auth_user (UNIQUE) | |
| role | VARCHAR(20) | admin, agent, supervisor |
| created_at, updated_at | TIMESTAMP | |

**Tabla:** `support_agent_profile`

---

### cases (Contador de casos)

Un registro por empresa para la numeración SUP-{PREFIJO}-000123.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | PK | |
| company_id | FK → companies (UNIQUE) | |
| last_number | INTEGER | Último número asignado |

**Tabla:** `support_case_counter`

---

### cases (Caso)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | PK | |
| company_id | FK → companies | |
| number_sequential | INTEGER | Número secuencial por empresa |
| number_display | VARCHAR(64) UNIQUE | Formato SUP-{prefijo}-000123 |
| status | VARCHAR(32) | Ver estados más abajo |
| assigned_to_id | FK → auth_user, NULL | Agente asignado |
| sla_started_at | TIMESTAMP, NULL | Inicio del SLA |
| sla_due_at | TIMESTAMP, NULL | Límite del SLA |
| sla_paused_since | TIMESTAMP, NULL | Pausa (esperando respuesta usuario) |
| sla_warning_sent_at | TIMESTAMP, NULL | Momento en que se envió el warning |
| sla_breached_at | TIMESTAMP, NULL | Momento de vencimiento |
| created_at, updated_at | TIMESTAMP | |

**Estados (CaseStatus):** iniciado, en_analisis_ia, esperando_respuesta_usuario, derivado_a_humano, asignado_a_agente_humano, en_proceso_humano, resuelto, cerrado, reabierto.

**Tabla:** `support_case`  
**Índices:** (company_id, status), (assigned_to_id, status), created_at, sla_due_at.

---

### cases (Mensaje)

Inmutable (sin updated_at). Cada ítem del timeline. Dedupe por canal: UNIQUE (channel_type, external_message_id) cuando external_message_id no vacío.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | PK | |
| case_id | FK → support_case | |
| channel_type | VARCHAR(20) | telegram, whatsapp, email, ... |
| external_channel_id | VARCHAR(255) | |
| external_message_id | VARCHAR(255) | ID del mensaje en el canal (evita duplicados por webhook) |
| sender_type | VARCHAR(20) | user, system, agent, ai, sla |
| sender_user_id | INTEGER, NULL | Si remitente es agente |
| content | TEXT | |
| direction | VARCHAR(10) | inbound, outbound |
| created_at | TIMESTAMP | |

**Tabla:** `support_message`  
**Índice:** (case_id, created_at). **Constraint:** UNIQUE (channel_type, external_message_id) donde external_message_id <> ''.

---

### cases (Resumen IA)

Resumen de un rango de mensajes del caso (versionado).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | PK | |
| case_id | FK → support_case | |
| from_message_id | FK → support_message, NULL | |
| to_message_id | FK → support_message, NULL | |
| summary_text | TEXT | |
| model_version | VARCHAR(64) | |
| created_at | TIMESTAMP | |

**Tabla:** `support_case_summary`

---

### attachments (Adjunto)

Metadata del archivo; el objeto se almacena en S3. Las URLs se generan firmadas bajo demanda.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | PK | |
| message_id | FK → support_message | |
| bucket | VARCHAR(255) | |
| storage_key | VARCHAR(512) | |
| content_type | VARCHAR(128) | |
| size_bytes | INTEGER | |
| original_name | VARCHAR(255) | |
| content_hash | VARCHAR(64) | Opcional |
| is_sensitive | BOOLEAN | |
| created_at | TIMESTAMP | |

**Tabla:** `support_attachment`

---

### sla (Configuración SLA)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | PK | |
| company_id | FK → companies | |
| case_type | VARCHAR(64) | Ej. default |
| response_time_minutes | INTEGER | |
| warning_pct | SMALLINT | 70 u 80 |
| created_at, updated_at | TIMESTAMP | |

**Tabla:** `support_sla_config`  
**Constraint:** UNIQUE (company_id, case_type).

---

### audit (Registro de idempotencia)

Para acciones sensibles (cambio estado, asignar, enviar respuesta). Misma clave → mismo resultado sin repetir efectos.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | PK | |
| case_id | FK → support_case | |
| action_key | VARCHAR(64) | UUID (header Idempotency-Key o body action_uuid) |
| actor_id | FK → auth_user | |
| status_code | SMALLINT | Código HTTP de la respuesta guardada |
| response_payload | JSONB | Payload resumido de la respuesta |
| created_at | TIMESTAMP | |

**Tabla:** `support_idempotency_record`  
**Constraint:** UNIQUE (case_id, action_key, actor_id).

---

### audit (Evento de auditoría)

Append-only. Solo inserciones.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | PK | |
| case_id | FK → support_case, NULL | |
| company_id | FK → companies | |
| event_type | VARCHAR(32) | Ver tipos más abajo |
| payload | JSONB | |
| actor_id | FK → auth_user, NULL | |
| created_at | TIMESTAMP | |

**Tipos (AuditEventType):** creacion_caso, cambio_estado, asignacion, mensaje_recibido, mensaje_enviado, accion_ia, sla_inicio, sla_pausa, sla_reanudacion, sla_warning, sla_vencido, reapertura, adjunto_descarga, acceso_caso.

**Tabla:** `support_audit_event`  
**Índices:** (case_id, created_at), (company_id, event_type, created_at).

---

### knowledge (Chunk de conocimiento)

Para RAG con búsqueda vectorial (pgvector). company_id NULL = conocimiento global.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | PK | |
| company_id | FK → companies, NULL | Global si NULL |
| source_type | VARCHAR(32) | caso, codigo, human_note, resolved_case |
| source_id | VARCHAR(64) | ID fuente (caso, artefacto, etc.) |
| text | TEXT | |
| content_hash | VARCHAR(64) | Hash del contenido (evita re-embed si no cambia) |
| metadata | JSONB | |
| embedding | VECTOR(dim) | pgvector; dimensión por EMBEDDING_DIMENSION (default 1536) |
| created_at | TIMESTAMP | |

**Tabla:** `support_knowledge_chunk`  
**Índices:** (company_id, source_type), content_hash, HNSW sobre embedding (similitud coseno).

---

### integrations (Mensaje copiloto)

Chat agente ↔ IA en contexto opcional de caso. Trazabilidad a conocimiento con saved_to_knowledge.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | PK | |
| case_id | FK → support_case, NULL | |
| user_id | FK → auth_user | |
| role | VARCHAR(10) | user, assistant |
| content | TEXT | |
| saved_to_knowledge | BOOLEAN | Si se guardó como chunk (human_note) |
| knowledge_chunk_id | INTEGER, NULL | ID del chunk creado |
| created_at | TIMESTAMP | |

**Tabla:** `support_copilot_message`

---

## Relaciones resumidas

- **Company** 1:N Case, SupportUser, SLAConfig; 1:1 CaseCounter.
- **SupportUser** 1:N ChannelIdentity.
- **Case** N:1 Company, assigned_to (User); 1:N Message, CaseSummary, AuditEvent; SLA runtime en los campos sla_*.
- **Message** N:1 Case; 1:N Attachment.
- **AuditEvent** N:1 Case, Company, actor (User).

## Numeración de casos

Formato: `SUP-{PREFIJO_EMPRESA}-000123`. El prefijo viene de `Company.prefix`. El número de 6 dígitos se obtiene incrementando `CaseCounter.last_number` por empresa dentro de una transacción (con `select_for_update`) al crear el caso.
