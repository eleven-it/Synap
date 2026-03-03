# Synap Support – Frontend

SPA React para el backoffice de Synap Support. Solo usuarios con rol **Admin**, **Agente** o **Supervisor**. No hay UI para usuarios finales.

## Stack

- **React 18** + **Vite** + **TypeScript**
- **TanStack Query** (datos servidor, cache, mutaciones)
- **React Router** (rutas protegidas, guards por rol)
- **MUI (Material UI)** – Kit de componentes: backoffice estándar, accesibilidad, theming y datos en tabla/cards. Alternativas (Chakra, Ant) son válidas; MUI encaja con productos operativos y documentación amplia.
- **React Hook Form** + **Zod** (formularios y validación)
- **Axios** con `withCredentials` (cookie-session) y header CSRF desde cookie
- **notistack** (toasts/snackbars)

## Cómo correr

```bash
cd support/frontend
npm install
# Las variables (VITE_API_BASE_URL, etc.) se leen de support/.env
npm run dev
```
*(Crear `support/.env` desde `support/.env.example` si aún no existe; Vite está configurado con `envDir: ..`.)*

En desarrollo, Vite puede hacer proxy de `/api` al backend (ver `vite.config.ts`). En ese caso `VITE_API_BASE_URL` puede omitirse o dejarse vacío para usar rutas relativas.

Build de producción:

```bash
npm run build
```

Salida en `dist/`. Servir con nginx o con el backend (Whitenoise, etc.).

## Estructura del proyecto

```
src/
  app/           # Routing, layout, providers (App, Layout, routes)
  features/     # Por dominio
    auth/       # Login, useAuth, AuthGuard
    cases/      # Listado, detalle (3 columnas: contexto, timeline, copiloto + respuesta)
    copilot/    # CopilotPanel (chat agente↔IA por caso, guardar como conocimiento)
    companies/  # Empresas (Admin)
    users/      # Usuarios de soporte (Admin)
    agents/     # Agentes (lista para asignación)
    metrics/    # Métricas SLA
    settings/   # Configuración (Admin): hub + drawers por área
  api/          # client (axios, withCredentials, CSRF), endpoints
  types/        # Tipos TS alineados con API
  styles/       # theme (MUI)
  utils/        # Helpers
```

## Endpoints consumidos (existentes en backend)

Según `support/docs/backend/API.md` y `technical_plan.md`:

| Recurso | Método | Endpoint |
|--------|--------|----------|
| Auth | POST | `/api/auth/login/` |
| Auth | GET | `/api/auth/me/` |
| Dashboard | GET | `/api/dashboard/` |
| Casos | GET | `/api/casos/` |
| Caso | GET | `/api/casos/:id/` |
| Caso | PATCH | `/api/casos/:id/` (Idempotency-Key) |
| Timeline | GET | `/api/casos/:id/timeline/` |
| Adjuntos | GET | `/api/casos/:id/adjuntos/` |
| Respuesta preview | POST | `/api/casos/:id/respuesta/preview/` |
| Respuesta enviar | POST | `/api/casos/:id/respuesta/enviar/` (Idempotency-Key) |
| Copiloto por caso | GET | `/api/casos/:id/copiloto/mensajes/` |
| Copiloto por caso | POST | `/api/casos/:id/copiloto/mensajes/` (texto, guardar_respuesta_como_conocimiento) |
| Empresas | GET/POST | `/api/empresas/`, `/api/empresas/:id/` |
| Usuarios soporte | GET | `/api/usuarios-soporte/`, `/api/usuarios-soporte/:id/` |
| Agentes | GET | `/api/agentes/` |
| Métricas | GET | `/api/metricas/` |
| Knowledge (Admin) | POST | `/api/knowledge/ingest/` |
| Knowledge (Admin) | GET | `/api/knowledge/search/?q=...` |

## Endpoints esperados (no implementados en backend)

La sección **Configuración** (Admin) permite configurar todo por UI. Las siguientes áreas tienen UI completa; el backend debe exponer estos contratos para que la configuración se persista y se pueda probar/activar desde la interfaz.

### A) Canales

- **GET /api/config/channels/** – Listar config por canal (whatsapp, telegram, email). Estado: no_configurado | parcial | activo | error; último check, último error.
- **POST /api/config/channels/** – Crear/actualizar borrador.
- **PATCH /api/config/channels/:id/** – Actualizar (token, webhook URL, etc.).
- **POST /api/config/channels/:id/test/** – Probar conexión (ping o envío de prueba).
- **POST /api/config/channels/:id/activate/** – Activar (tras validar). **POST /api/config/channels/:id/deactivate/** – Desactivar.

### B) IA / Modelos

- **GET /api/config/ia/** – Config actual: proveedor, modelo, límites, prompt_version (por empresa o global).
- **PATCH /api/config/ia/** – Guardar (API key enmascarada en respuesta).
- **POST /api/config/ia/test/** – Test LLM (ping o prompt de prueba).

### C) RAG / Conocimiento

- Ingesta y búsqueda ya existen: POST `/api/knowledge/ingest/`, GET `/api/knowledge/search/`.
- **GET /api/config/rag/** – top_k, fuentes habilitadas, política global+empresa, cache TTL.
- **PATCH /api/config/rag/** – Guardar.
- **POST /api/config/rag/reindex/** – Disparar reindexación.
- **POST /api/config/rag/ingest/** – Ingesta bajo demanda.

### D) SLA

- ConfigSLA ya existe en backend por empresa/tipo. Falta API REST para CRUD desde UI.
- **GET /api/config/sla/** – Listar por empresa (o GET /api/empresas/:id/ con sla_configs).
- **POST /api/config/sla/**, **PATCH /api/config/sla/:id/** – Crear/actualizar.
- **POST /api/config/sla/test/** – Opcional: simular vencimiento para pruebas.

### E) Storage / Adjuntos

- **GET /api/config/storage/** – Endpoint, bucket, region, path_style; políticas (tamaño máx, tipos, retención).
- **PATCH /api/config/storage/** – Guardar (secret enmascarado).
- **POST /api/config/storage/test/** – Subir archivo de prueba o generar URL firmada.

### F) Seguridad operativa

- **GET /api/config/security/** – Rate limits por canal, anti-spam toggles, política PII.
- **PATCH /api/config/security/** – Guardar.
- **POST /api/config/security/self-check/** – Ejecutar comprobaciones y devolver resultado.

### G) Notificaciones y escalamiento

- **GET /api/config/notifications/** – Gerencia/supervisores, mensajes estándar SLA, canal de alertas.
- **PATCH /api/config/notifications/** – Guardar.

### H) Branding / Mensajes (opcional)

- **GET /api/config/branding/** – Nombre asistente, saludo, idioma (por empresa o global).
- **PATCH /api/config/branding/** – Guardar.

---

Las respuestas de los GET de configuración deberían incluir al menos: estado (`no_configurado` | `parcial` | `validando` | `activo` | `error`), `last_check_at`, `last_error` (mensaje humano), y los campos editables. Los POST de test deben devolver éxito/error y un mensaje legible.

## Autenticación y roles

- Login por sesión (cookie). El cliente envía `withCredentials: true` y el header `X-CSRFToken` (valor desde cookie `csrftoken`).
- Roles: `admin`, `agent`, `supervisor`. La respuesta de `/api/auth/me/` incluye `role`. Las rutas y la visibilidad del menú (p. ej. Configuración solo Admin) se basan en ese rol.
- No se hardcodean permisos en el front: si el backend devuelve 403, se muestra error; las acciones no permitidas pueden ocultarse según `role` para mejor UX.

## Idempotencia

En mutaciones sensibles (PATCH caso, enviar respuesta) el cliente genera un UUID y lo envía en el header `Idempotency-Key` (ver `api/client.ts` y `api/endpoints.ts`). El backend devuelve la misma respuesta si la clave se repite.

## Navegación

- Sidebar colapsable: Dashboard, Casos, Empresas, Usuarios, Agentes, Métricas, **Configuración** (solo Admin).
- Detalle de caso: tres columnas (Contexto | Timeline | Copiloto IA + caja de respuesta). Botón “Guardar como conocimiento” en el flujo del copiloto (checkbox en el panel).

## Calidad UX

- Skeleton loaders en listas y detalle.
- Toasts para éxito/error en mutaciones.
- Empty states y mensajes de error con retry implícito (recargar o reintentar).
- Drawers para configuración en lugar de modales pesados.

## Accesibilidad y rendimiento

- Foco visible, etiquetas ARIA donde aplica, navegación por teclado.
- Contraste según tema MUI.
- Lazy-loading de rutas (`React.lazy` + `Suspense`).
- Cache con TanStack Query (`staleTime`, invalidación tras mutaciones).
