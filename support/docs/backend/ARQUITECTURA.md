# Arquitectura del Backend

## Estructura del proyecto

```
support/backend/
├── config/                 # Proyecto Django "support_service"
│   ├── __init__.py         # Carga celery_app
│   ├── settings/           # Configuración por entorno
│   │   ├── base.py
│   │   ├── local.py
│   │   ├── dev.py
│   │   ├── staging.py
│   │   └── prod.py
│   ├── urls.py             # Raíz: admin + api/
│   ├── wsgi.py
│   └── celery.py           # Celery + Beat schedule
├── apps/
│   ├── core/               # Utilidades (no app instalada)
│   │   ├── exceptions.py   # APIError, CaseStateTransitionError, custom_exception_handler
│   │   └── logging_utils.py
│   ├── companies/          # Empresa (synap_id, prefijo, idioma)
│   ├── support_users/      # Usuario de soporte + IdentidadCanal
│   ├── agents/             # AgentProfile (rol: admin, agent, supervisor)
│   ├── cases/              # Caso, Mensaje, CaseSummary, CaseCounter + domain + services
│   ├── attachments/        # Adjunto (metadata + S3)
│   ├── sla/                # SLAConfig + servicios SLA + tasks Celery
│   ├── audit/              # AuditEvent (append-only)
│   ├── knowledge/          # KnowledgeChunk (RAG stub) + tasks
│   ├── integrations/       # SynapClient, adapters, CopilotMessage, copilot_reply
│   └── api/                # Vistas y serializers DRF, permisos
├── scripts/
│   └── run.sh              # migrate + runserver
├── manage.py
├── requirements.txt
├── .env.example
├── Dockerfile
└── README.md
```

## Capas internas

- **Domain:** Lógica pura de negocio sin I/O. En `apps/cases/domain.py`: estados, transiciones válidas (`VALID_TRANSITIONS`), `can_transition()`, `open_status_values()`, `is_sla_paused_status()`, etc.
- **Services:** Orquestación y casos de uso. Ejemplos: `apps/cases/services.py` (crear caso, numeración, transiciones, asignación), `apps/sla/services.py` (inicio/pausa/reanudación SLA, warning, vencimiento), `apps/attachments/services.py` (URLs firmadas S3).
- **Adapters:** I/O hacia sistemas externos. En `apps/integrations/adapters/`: `SynapClient` (HTTP + JWT), `BaseChannelAdapter` y implementaciones (Telegram, WhatsApp, Email), interfaces de agente IA (RetrievalService, ToolsService, AgentService).

## Flujo de datos

- **Mensaje entrante:** Webhook → validación de firma (adapter) → parseo a mensaje normalizado → resolución usuario/caso → persistencia mensaje → disparo de agente IA o cola humano (en implementación completa).
- **Frontend:** Peticiones a `/api/*` → autenticación sesión → vistas DRF → servicios de dominio y modelos → respuesta JSON.
- **SLA:** Al asignar agente → `start_sla_for_case`. Al pasar a "Esperando respuesta del usuario" → `pause_sla_for_case`. Al salir → `resume_sla_for_case`. Job Beat periódico ejecuta `run_sla_checks` (warning y vencimiento).
- **Auditoría:** Toda acción relevante (creación de caso, cambio de estado, asignación, mensajes, eventos SLA) persiste un registro en `AuditEvent` (append-only).

## Dependencias

- Django 4+, DRF, django-filter, django-cors-headers, django-environ.
- PostgreSQL (psycopg), Redis, Celery, boto3 (S3), PyJWT, requests, structlog.
- No se importa código del ERP Synap; solo se consume su API HTTP mediante `SynapClient`.
