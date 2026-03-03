# Documentación del frontend – Synap Support

Documentación completa del frontend React (backoffice) desarrollado en `/support/frontend`. La UI está dirigida **solo a agentes humanos** (Admin, Agente, Supervisor); no existe interfaz para el usuario final.

## Índice

| Documento | Contenido |
|-----------|-----------|
| [ARQUITECTURA.md](ARQUITECTURA.md) | Stack, estructura de carpetas, flujo de datos, decisiones técnicas |
| [PANTALLAS.md](PANTALLAS.md) | Descripción de cada pantalla, flujos y componentes |
| [API_Y_CONFIG.md](API_Y_CONFIG.md) | Endpoints consumidos, idempotencia, sección Configuración y endpoints esperados |
| [CONFIGURACION_Y_DESPLIEGUE.md](CONFIGURACION_Y_DESPLIEGUE.md) | Variables de entorno, cómo correr, build y despliegue |

## Resumen ejecutivo

- **Ubicación:** `support/frontend`
- **Stack:** React 18, Vite, TypeScript, TanStack Query, React Router, MUI, React Hook Form + Zod, Axios, notistack
- **Propósito:** Backoffice operativo para gestionar casos, empresas, usuarios de soporte, agentes, métricas y **toda la configuración del sistema por UI** (canales, IA, RAG, SLA, storage, seguridad, notificaciones, branding)
- **Autenticación:** Sesión por cookie; CSRF desde cookie; roles desde `/api/auth/me/`
- **Pantallas:** Login, Dashboard, Casos (listado + detalle 3 columnas con Copiloto IA), Empresas, Usuarios, Agentes, Métricas, Configuración (Admin)

## Referencias

- Plan técnico: [support/docs/technical_plan.md](../technical_plan.md)
- API backend: [support/docs/backend/API.md](backend/API.md)
- README del proyecto frontend: [support/frontend/README.md](../../frontend/README.md)
