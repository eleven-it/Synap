# Synap Support – Backend

Backend del servicio de soporte (Django 4+ y Django REST Framework). Independiente del ERP Synap; la integración con Synap es solo vía API HTTP (SynapClient) con JWT.

## Requisitos

- Python 3.10+
- PostgreSQL con extensión **pgvector** (habilitada en migración `knowledge.0002` para RAG)
- Redis
- Opcional: MinIO/S3 para adjuntos

## Instalación

```bash
cd support
cp .env.example .env
# Editar support/.env (DATABASE_URL, REDIS_URL, CONFIG_ENCRYPTION_KEY, etc.)
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
*(Support usa un solo .env en `support/.env`; el backend lo lee desde ahí.)*

## Base de datos

Crear la base PostgreSQL (con extensión pgvector disponible) y ejecutar migraciones:

```bash
export DJANGO_SETTINGS_MODULE=config.settings.local
python manage.py migrate
```

La migración `knowledge.0002_rag_embedding_and_metadata` ejecuta `CREATE EXTENSION IF NOT EXISTS vector` y añade la columna `embedding` y un índice de similitud (HNSW si pgvector lo soporta, sino IVFFlat).

**pgvector:** Se recomienda **pgvector ≥ 0.5** (HNSW). En Docker, usar una imagen con pgvector preinstalado, por ejemplo `pgvector/pgvector:pg16` o `ankane/pgvector`. Versión mínima sugerida: Postgres 14+ con extensión vector.

```bash
python manage.py createsuperuser   # para acceder al admin y como agente
```

Después de crear un usuario, asignarle un perfil de agente en Admin → Perfiles de agente (rol: admin, agent o supervisor).

## Arranque desarrollo

```bash
# Terminal 1: Django
./scripts/run.sh
# o: python manage.py runserver 0.0.0.0:8000

# Terminal 2: Celery worker
celery -A config worker -l info

# Terminal 3: Celery beat (SLA periódico)
celery -A config beat -l info
```

## API

- **GET /api/health** — Estado del servicio (db, redis, storage opcional). Sin autenticación.
- **POST /api/auth/login/** — Login (username, password). Crea sesión.
- **GET /api/auth/me/** — Usuario actual y rol.
- **GET /api/dashboard/** — KPIs (casos por estado, abiertos, SLA en riesgo).
- **GET /api/casos/** — Lista de casos (filtros: status, company, assigned_to).
- **GET /api/casos/:id/** — Detalle de caso.
- **PATCH /api/casos/:id/** — Cambiar estado y/o asignar agente.
- **GET /api/casos/:id/timeline/** — Mensajes y resúmenes.
- **GET /api/casos/:id/adjuntos/** — Adjuntos con URL firmada.
- **POST /api/casos/:id/respuesta/enviar/** — Enviar respuesta (registra mensaje).
- **GET /api/empresas/**, **POST /api/empresas/**, etc. — CRUD empresas (Admin).
- **GET /api/usuarios-soporte/** — Usuarios de soporte y canales (Admin).
- **GET /api/agentes/** — Lista de agentes (backoffice).
- **GET /api/metricas/** — Métricas (SLA, desde_fecha, hasta_fecha, empresa_id).
- **POST /api/copiloto/mensaje/** — Chat copiloto (texto, case_id opcional).
- **GET /api/copiloto/historial/** — Historial del copiloto.
- **GET/POST /api/casos/:id/copiloto/mensajes/** — Copiloto por caso (guardar respuesta como conocimiento).
- **POST /api/knowledge/ingest/** — Ingesta chunks (Admin). **GET /api/knowledge/search/?q=...** — Búsqueda vectorial (Admin).
- **Configuración (Admin):** `/api/config/channels/`, `/api/config/ia/`, `/api/config/rag/`, `/api/config/storage/`, `/api/config/security/`, `/api/config/notifications/`, `/api/config/branding/`, `/api/config/sla/`. Los secretos se guardan cifrados (variable `CONFIG_ENCRYPTION_KEY` en `.env`); en GET se devuelven enmascarados. Ver [API.md](docs/backend/API.md#configuración-admin).
- Acciones sensibles (PATCH caso, enviar respuesta) aceptan **Idempotency-Key** (UUID) para no duplicar efectos.
- Webhooks (telegram, whatsapp, email) hacen **dedupe** por `(channel_type, external_message_id)` y responden 200 si duplicado.

## Estructura

- `config/` — Configuración Django (settings por entorno, urls, celery, wsgi).
- `apps/` — Apps de dominio:
  - `companies` — Empresa (synap_id, prefijo, idioma).
  - `support_users` — Usuario de soporte e identidades de canal.
  - `agents` — Perfil de agente (rol) vinculado a User.
  - `cases` — Caso, Mensaje, ResumenIA, contador; dominio y servicios.
  - `attachments` — Adjuntos (metadata + S3).
  - `sla` — ConfigSLA y motor (inicio, pausa, warning, vencimiento; tareas Celery).
  - `audit` — EventoAuditoria append-only.
  - `knowledge` — RAG con LangChain PGVector (langchain_rag: store, ingesta add_documents, retriever, cadena LCEL); sin tabla Django propia.
  - `integrations` — SynapClient, adapters de canal, copiloto; modelos CopilotMessage.
  - `system_config` — Configuración producto (canales, IA, RAG, storage, seguridad, notificaciones, branding, SLA CRUD); cifrado de secretos, ConfigService con cache, auditoría.
  - `api` — Vistas y serializers DRF.
- `apps/core` — Excepciones y logging (no es app instalada).

## Docker

Ver `/support/docker` para docker-compose. El backend se construye con:

```bash
docker build -t support-backend .
```

Variables de entorno: ver `support/.env.example` (único .env del proyecto Support).

## Documentación

- **Plan funcional:** [support/plan_support.md](../plan_support.md)
- **Plan técnico:** [support/docs/technical_plan.md](../docs/technical_plan.md)
- **Documentación backend (implementado):** [support/docs/backend/](../docs/backend/)
  - [Índice](../docs/backend/README.md) · [Arquitectura](../docs/backend/ARQUITECTURA.md) · [Modelos](../docs/backend/MODELOS.md) · [API](../docs/backend/API.md) · [Servicios y SLA](../docs/backend/SERVICIOS_DOMINIO.md) · [Integraciones](../docs/backend/INTEGRACIONES.md) · [Celery](../docs/backend/CELERY_TAREAS.md) · [Configuración](../docs/backend/CONFIGURACION.md) · [Despliegue](../docs/backend/DESPLIEGUE.md)
