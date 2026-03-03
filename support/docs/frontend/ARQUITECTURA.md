# Arquitectura del frontend

## Stack tecnológico

| Tecnología | Uso |
|------------|-----|
| **React 18** | UI y componentes |
| **Vite** | Build y dev server; proxy a la API en desarrollo |
| **TypeScript** | Tipado estático; tipos alineados con la API |
| **TanStack Query** | Datos servidor: cache, fetching, mutaciones, invalidación |
| **React Router** | Rutas SPA; rutas protegidas y lazy-loading |
| **MUI (Material UI)** | Kit de componentes: tablas, formularios, drawers, chips, etc. Justificación: estándar en backoffices, accesibilidad, theming y documentación amplia |
| **React Hook Form** | Formularios (login y futuros CRUD) |
| **Zod** | Esquemas de validación (login) |
| **Axios** | Cliente HTTP con interceptores (CSRF, withCredentials) |
| **notistack** | Snackbars/toasts para feedback de éxito y error |

## Estructura del proyecto

```
support/frontend/
  public/              # favicon, assets estáticos
  src/
    app/               # Capa de aplicación
      App.tsx          # Providers (Query, Theme, Snackbar), RouterProvider
      Layout.tsx       # AppBar + Drawer (sidebar) + Outlet
      routes.tsx       # createBrowserRouter, rutas protegidas, lazy pages
    features/          # Módulos por dominio
      auth/            # Login, useAuth, AuthGuard
      cases/           # CasesListPage, CaseDetailPage (3 columnas)
      copilot/         # CopilotPanel (chat por caso, guardar como conocimiento)
      companies/       # CompaniesPage
      users/           # UsersPage (usuarios de soporte)
      agents/          # AgentsPage
      metrics/         # MetricsPage
      settings/        # SettingsPage (hub) + ConfigCanales, ConfigIA, ConfigRAG, etc.
    api/               # Capa de acceso a datos
      client.ts        # Axios: baseURL, withCredentials, X-CSRFToken, Idempotency-Key
      endpoints.ts     # Funciones por recurso (auth, cases, companies, …)
    types/             # Tipos TypeScript (User, Case, Message, etc.)
    styles/            # theme.ts (MUI)
    utils/             # Helpers (vacío por ahora)
    vite-env.d.ts      # Tipos para import.meta.env
  index.html
  vite.config.ts
  tsconfig.json
  package.json
  .env.example
  README.md
```

## Flujo de datos

- **Servidor como fuente de verdad:** TanStack Query mantiene cache por `queryKey`; las mutaciones invalidan las queries relacionadas para refrescar datos.
- **Autenticación:** Tras login (POST `/api/auth/login/`), el backend fija la cookie de sesión. Las peticiones siguientes llevan `withCredentials: true` y el header `X-CSRFToken` (leído de la cookie `csrftoken`). El estado de usuario se obtiene con GET `/api/auth/me/` y se cachea; si el backend responde 401, el interceptor de Axios dispara lógica de logout (redirección a `/login`).
- **Roles:** El frontend no hardcodea permisos; usa el campo `role` de `/api/auth/me/` para mostrar u ocultar menús (p. ej. Configuración solo para `admin`). Las acciones no permitidas devuelven 403 desde el backend.

## Decisiones de diseño

- **Una sola SPA:** Todo el backoffice en una aplicación; no hay microfrontends.
- **Rutas lazy:** Las páginas se cargan con `React.lazy` y `Suspense` para reducir el bundle inicial.
- **Configuración por UI:** Toda la configuración operativa (canales, IA, RAG, SLA, storage, seguridad, notificaciones, branding) se realiza desde la sección Configuración; no se exige editar `.env` para operar. Donde el backend aún no expone endpoints de config, la UI está implementada y se documentan los **endpoints esperados** (ver API_Y_CONFIG.md).
- **Idempotencia en mutaciones:** PATCH caso y POST enviar respuesta envían el header `Idempotency-Key` (UUID generado en cliente) para evitar efectos duplicados si el usuario o la red reintentan.
