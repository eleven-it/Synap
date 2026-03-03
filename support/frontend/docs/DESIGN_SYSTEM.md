# Design System – Synap Support (Kora-like)

Refactor visual del frontdesk con look & feel tipo admin premium (Kora). Sin cambiar rutas, API ni lógica de negocio.

## Tema (light/dark)

- **Persistencia:** El modo se guarda en `localStorage` con la clave `synap-support-theme-mode` (`src/styles/tokens.ts`: `STORAGE_THEME_KEY`).
- **Cambiar tema desde código:** Usar el contexto `ThemeModeContext` desde `@/app/ThemeProvider`:
  - `mode`: `'light' | 'dark'`
  - `setMode(mode)`: fija el modo y persiste.
  - `toggleMode()`: alterna entre light y dark.
- **En la UI:** El Topbar incluye un botón (sol/luna) que llama a `toggleMode()`.

## Tokens

Definidos en `src/styles/tokens.ts`:

- **Spacing:** 0, 4, 8, 12, 16, 24, 32, 40, 48 (px).
- **Radius:** sm 8, md 12, lg 16, pill.
- **Sombras:** sm, md, lg (suaves).
- **Tipografía:** h1–h3, body, small, caption.
- **Transiciones:** 150–250 ms.

El tema MUI (`src/styles/theme.ts`) usa estos tokens para `palette`, `shape`, `shadows`, `typography` y `transitions`. Se crea con `createAppTheme(mode)`.

## Componentes base (`src/components/ui/`)

Usar siempre que sea posible estos componentes para mantener consistencia.

| Componente | Uso |
|------------|-----|
| **AppShell** | Layout principal: Sidebar + Topbar + área de contenido. Usado en rutas protegidas. |
| **Sidebar** | Navegación colapsable; ítem activo con fondo primary (estilo “pill”). |
| **Topbar** | Barra superior con título, toggle tema, usuario y “Salir”. |
| **PageHeader** | Título de página, subtítulo opcional, breadcrumbs y acciones. |
| **Card** | Contenedor con borde sutil, radius y sombra. |
| **StatCard** | Métrica con título, valor, icono opcional y badge opcional (success/warning/error/info). |
| **DataTable** | Tabla con header sticky, loading, empty y paginación. Columnas con `id`, `label`, `render`. |
| **Badge** | Chip semántico: `variant` success | warning | error | info | default. |
| **SlaBar** | Indicador de SLA: status ok | at_risk | breached | none, con fecha si aplica. |
| **SidePanel** | Drawer lateral (anchor right) para configuración. |
| **EmptyState** | Icono + título + descripción + CTA cuando no hay datos. |
| **Skeleton** | MUI Skeleton + `SkeletonText`, `SkeletonTableRow`, `SkeletonStatCard`. |

Import desde el barrel:

```ts
import { Card, PageHeader, DataTable, Badge } from '@/components/ui'
```

## Convenciones de estilos

- **Sin estilos inline dispersos:** Usar `sx` con valores del tema (ej. `bgcolor: 'background.paper'`, `borderRadius: 2`).
- **Radius:** Preferir `borderRadius: 2` (12px) en cards, botones e inputs para alinear con tokens.
- **Transiciones:** 150–250 ms en hover, expand/collapse y drawers.
- **Accesibilidad:** Foco visible en controles; usar `aria-label` en iconos y botones sin texto.
- **Densidad:** Tablas con tamaño `medium` por defecto; no compactar en exceso.

## Mensajes de error (UX)

En login y flujos críticos se mapean códigos HTTP a mensajes en español:

- **401:** “Credenciales inválidas…”
- **403:** “No tenés permisos…”
- **409:** “Transición no permitida…”
- **5xx:** “Error del servidor, reintentá…”

Función helper reutilizable: `messageForStatus(status)` (ej. en `LoginPage`).
