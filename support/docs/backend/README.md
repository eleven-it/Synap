# Documentación Backend – Synap Support

Documentación técnica del backend implementado en `/support/backend` (Django 4+ y Django REST Framework). El servicio es independiente del ERP Synap; la integración con Synap es exclusivamente vía API HTTP (SynapClient) con JWT.

## Índice

| Documento | Contenido |
|-----------|-----------|
| [ARQUITECTURA.md](ARQUITECTURA.md) | Estructura del proyecto, capas (domain/services/adapters), componentes y flujo de datos |
| [MODELOS.md](MODELOS.md) | Modelo de datos: entidades, campos, relaciones, índices y tablas |
| [API.md](API.md) | Referencia de la API REST: endpoints, métodos, payloads, paginación, errores y permisos |
| [SERVICIOS_DOMINIO.md](SERVICIOS_DOMINIO.md) | Reglas de negocio, workflow de casos, numeración, asignación y motor SLA |
| [INTEGRACIONES.md](INTEGRACIONES.md) | SynapClient, adaptadores de canal (Telegram, WhatsApp, Email) e interfaces IA (stubs) |
| [CELERY_TAREAS.md](CELERY_TAREAS.md) | Tareas asíncronas, Celery Beat y jobs programados |
| [CONFIGURACION.md](CONFIGURACION.md) | Variables de entorno y settings por entorno (local, dev, staging, prod) |
| [DESPLIEGUE.md](DESPLIEGUE.md) | Docker, scripts de arranque, healthchecks y despliegue |

## Referencias

- **Plan funcional:** [../plan_support.md](../plan_support.md)
- **Plan técnico:** [../technical_plan.md](../technical_plan.md)
- **README rápido del backend:** [../../backend/README.md](../../backend/README.md)
