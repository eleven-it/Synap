# Celery y tareas asíncronas

## Configuración

- **Módulo:** `config.celery`. La app se carga en `config/__init__.py` (`celery_app`).
- **Broker y backend:** Se usan `CELERY_BROKER_URL` y `REDIS_URL` (por defecto Redis).
- **Autodiscover:** Tareas en `apps.cases`, `apps.sla`, `apps.audit`, `apps.knowledge`, `apps.integrations`.

## Tareas implementadas

### SLA (`apps.sla.tasks`)

| Tarea | Nombre | Descripción |
|-------|--------|-------------|
| run_sla_checks | sla.run_sla_checks | Job periódico: casos con SLA activo no pausado; si % >= warning_pct envía warning y registra evento; si tiempo >= límite marca vencido, notifica usuario y escala a gerencia (stubs). |
| notify_user_sla_breached | sla.notify_user_sla_breached | Stub: notificar al usuario que el SLA venció. |
| escalate_sla_to_management | sla.escalate_sla_to_management | Stub: escalar a gerencia. |
| notify_agent_sla_warning | sla.notify_agent_sla_warning | Stub: notificar al agente el warning de SLA. |

### Conocimiento (`apps.knowledge.tasks`)

| Tarea | Nombre | Descripción |
|-------|--------|-------------|
| ingest_resolved_cases | knowledge.ingest_resolved_cases | Stub: ingesta de casos resueltos para RAG (parámetro opcional company_id). |

## Celery Beat (programación)

Definido en `config.celery.app.conf.beat_schedule`:

- **sla-checks-every-2min:** tarea `sla.run_sla_checks`, cada 120 segundos.

Para cambiar la frecuencia se edita el valor de `schedule` en `config/celery.py` (por ejemplo `crontab(minute='*/5')` para cada 5 minutos).

## Arranque

- **Worker:** `celery -A config worker -l info`
- **Beat:** `celery -A config beat -l info`

En Docker se suelen definir servicios separados para worker y beat usando la misma imagen del backend.
