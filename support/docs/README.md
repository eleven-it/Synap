# Documentación Synap Support

## Documentos principales

| Documento | Descripción |
|-----------|-------------|
| [plan_support.md](../plan_support.md) | Plan funcional del producto (fuente de verdad) |
| [technical_plan.md](technical_plan.md) | Plan técnico: arquitectura, modelo de datos, API, SLA, IA, despliegue |

## Documentación del backend (implementado)

El backend en `/support/backend` está documentado en la carpeta **[backend/](backend/)**:

- [**backend/README.md**](backend/README.md) — Índice de la documentación backend
- [Arquitectura](backend/ARQUITECTURA.md) — Estructura del proyecto, capas, flujo de datos
- [Modelos](backend/MODELOS.md) — Entidades, campos, relaciones, índices
- [API](backend/API.md) — Referencia de endpoints, payloads, errores, permisos
- [Servicios de dominio](backend/SERVICIOS_DOMINIO.md) — Workflow de casos, numeración, SLA
- [Integraciones](backend/INTEGRACIONES.md) — SynapClient, adaptadores de canal, IA (stubs)
- [Celery](backend/CELERY_TAREAS.md) — Tareas asíncronas y Beat
- [Configuración](backend/CONFIGURACION.md) — Variables de entorno y settings
- [Despliegue](backend/DESPLIEGUE.md) — Docker, scripts, healthchecks

## Documentación del frontend (implementado)

El frontend React en `/support/frontend` (backoffice para agentes) está documentado en la carpeta **[frontend/](frontend/)**:

- [**frontend/README.md**](frontend/README.md) — Índice de la documentación frontend
- [Arquitectura](frontend/ARQUITECTURA.md) — Stack, estructura de carpetas, flujo de datos, decisiones técnicas
- [Pantallas](frontend/PANTALLAS.md) — Rutas, login, dashboard, casos (listado y detalle 3 columnas), copiloto IA, empresas, usuarios, agentes, métricas, configuración (hub y drawers)
- [API y configuración](frontend/API_Y_CONFIG.md) — Endpoints consumidos, idempotencia, sección Configuración y endpoints esperados por área (canales, IA, RAG, SLA, storage, seguridad, notificaciones, branding)
- [Configuración y despliegue](frontend/CONFIGURACION_Y_DESPLIEGUE.md) — Variables de entorno, desarrollo local, build, despliegue
