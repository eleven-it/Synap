# Servicios de dominio y reglas de negocio

## Workflow de casos (estados y transiciones)

Estados definidos en `apps.cases.models.CaseStatus`:

- **iniciado** — Caso recién creado.
- **en_analisis_ia** — El agente IA está procesando.
- **esperando_respuesta_usuario** — Se espera respuesta del usuario; el SLA se considera en pausa.
- **derivado_a_humano** — Derivado a humano, aún sin asignar.
- **asignado_a_agente_humano** — Asignado a un agente; aquí arranca el SLA.
- **en_proceso_humano** — El agente está trabajando en el caso.
- **resuelto** — Marcado como resuelto.
- **cerrado** — Cerrado.
- **reabierto** — Reabierto desde cerrado/resuelto.

### Matriz de transiciones válidas

Definida en `apps.cases.domain.VALID_TRANSITIONS`:

| Desde | Hacia permitido |
|-------|------------------|
| iniciado | en_analisis_ia |
| en_analisis_ia | esperando_respuesta_usuario, derivado_a_humano |
| esperando_respuesta_usuario | en_analisis_ia, derivado_a_humano |
| derivado_a_humano | asignado_a_agente_humano |
| asignado_a_agente_humano | en_proceso_humano |
| en_proceso_humano | esperando_respuesta_usuario, resuelto |
| resuelto | cerrado, reabierto |
| cerrado | reabierto |
| reabierto | en_analisis_ia, derivado_a_humano |

La función `can_transition(estado_actual, estado_nuevo)` valida antes de aplicar. Si la transición no está permitida, se lanza `CaseStateTransitionError` (409).

---

## Numeración de casos

- Formato: **SUP-{PREFIJO_EMPRESA}-000123**.
- El prefijo viene de `Company.prefix`.
- El número de 6 dígitos es secuencial por empresa y se obtiene de la tabla `CaseCounter` (campo `last_number`).
- Al crear un caso:
  1. Se obtiene o crea el `CaseCounter` de la empresa con `select_for_update`.
  2. Se incrementa `last_number` y se guarda.
  3. Se crea el `Case` con ese `number_sequential` y `number_display = f"SUP-{company.prefix}-{number:06d}"`.

Servicio: `apps.cases.services.get_next_case_number(company)` → `(int, str)`.  
Creación de caso: `apps.cases.services.create_case(company)` → crea caso, registra evento `creacion_caso` en auditoría.

---

## Creación y continuación de caso

- **Listado de casos abiertos para un usuario de soporte:** `get_open_cases_for_support_user(support_user)`. Considera “abiertos” todos los estados salvo `cerrado` y `resuelto` (función `open_status_values()` en domain).
- **Resolver o crear caso por canal:** `get_or_create_case_for_channel(company, channel_type, external_id, support_user, prefer_new)`. Si hay casos abiertos del usuario (por ese `external_id`) y no se pide uno nuevo, devuelve el primero; si no, crea uno nuevo. Devuelve `(case, created)`.

---

## Asignación y transiciones

- **Transición de estado:** `transition_case_status(case, new_status, actor_id=None, payload_extra=None)`. Valida con `can_transition`, actualiza el caso, registra evento `cambio_estado` y, si aplica, llama a `pause_sla_for_case` o `resume_sla_for_case` (al entrar o salir de `esperando_respuesta_usuario`).
- **Asignar caso:** `assign_case(case, assigned_to_id, actor_id=None)`. Pone `assigned_to_id`, transiciona a `asignado_a_agente_humano`, registra evento `asignacion` y llama a `start_sla_for_case(case, actor)`.

---

## Motor de SLA

Implementado en `apps.sla.services` y disparado desde casos (asignación y transiciones) y desde Celery Beat.

### Inicio del SLA

- **Cuándo:** Al transicionar a **asignado_a_agente_humano** (desde `assign_case`).
- **Qué hace:** Obtiene `SLAConfig` para la empresa (y tipo_caso "default"), setea `sla_started_at` y `sla_due_at` (now + response_time_minutes), limpia `sla_paused_since`, y registra evento `sla_inicio`.

### Pausa del SLA

- **Cuándo:** Al transicionar a **esperando_respuesta_usuario** (desde `transition_case_status`).
- **Qué hace:** Setea `sla_paused_since = now` y registra evento `sla_pausa`. El tiempo en este estado no cuenta para el límite.

### Reanudación del SLA

- **Cuándo:** Al salir de **esperando_respuesta_usuario** (desde `transition_case_status`).
- **Qué hace:** Limpia `sla_paused_since`, recalcula `sla_due_at` (now + response_time_minutes) y registra evento `sla_reanudacion`.

### Warning (70–80%)

- **Cuándo:** Job periódico Celery (`run_sla_checks`). Para cada caso con SLA activo (no pausado, no vencido), si el porcentaje de tiempo consumido >= `warning_pct` y aún no se envió warning.
- **Qué hace:** Setea `sla_warning_sent_at`, registra evento `sla_warning` y encola tarea `notify_agent_sla_warning` (stub).

### Vencimiento del SLA

- **Cuándo:** Mismo job; si tiempo consumido >= tiempo de respuesta.
- **Qué hace:** Setea `sla_breached_at`, registra evento `sla_vencido`, encola `notify_user_sla_breached` y `escalate_sla_to_management` (stubs).

### Cálculo de tiempo consumido

- `effective_sla_seconds_consumed(case, until=None)`: tiempo desde `sla_started_at` hasta `until` (o now), restando el intervalo en que `sla_paused_since` estuvo activo.
- `sla_percentage_consumed(case, until=None)`: porcentaje respecto de `SLAConfig.response_time_minutes`.

---

## Auditoría

- **Append-only:** Solo inserciones en `AuditEvent`. No se actualizan ni borran registros.
- **Eventos registrados:** creacion_caso, cambio_estado, asignacion, mensaje_recibido, mensaje_enviado, accion_ia, sla_inicio, sla_pausa, sla_reanudacion, sla_warning, sla_vencido, reapertura, adjunto_descarga, acceso_caso.
- Los servicios de casos y SLA crean los eventos correspondientes con `case_id`, `company_id`, `event_type`, `payload` (JSON) y opcionalmente `actor`.
