# Spec — Shell reportes MPR

**Capability:** `mpr-reportes-shell`  
**Change:** `mpr-reportes-trazabilidad-produccion`

---

## Requirements

### REQ-SHELL-01 — Hub único en `/mpr/reportes/`

The system MUST render a single hub de reportes MPR con hero slate, breadcrumb MPR › Reportes, y contenido dinámico según grupo/reporte activo.

### REQ-SHELL-02 — Filtro de período sticky

The system MUST provide campos **Desde** y **Hasta** con formato de visualización **dd/MM/yyyy** y presets: Hoy, Últimos 7 días, Mes actual, Mes anterior.

The filter MUST persist in URL query parameters and apply to all reportes del grupo activo excepto trazabilidad (que MAY override con artículo obligatorio).

### REQ-SHELL-03 — Navegación por grupos

The system MUST organize reportes en grupos:

| Grupo | Reportes |
|-------|----------|
| Producción | Resumen diario, Operario, Cadena pipeline, Pendiente componentes |
| Demanda | Brecha pack, Pedidos por estado (P1) |
| Trazabilidad | Línea de tiempo, Movimientos (P1) |
| Histórico OPT | OPT cerradas, WIP OPT, Desperdicio legacy |

Default group MUST be **Producción** → **Resumen diario**.

### REQ-SHELL-04 — KPI strip contextual

When a report supports aggregated KPIs, the system MUST show up to four KPI cards between navigation and main content, updating when period or report changes.

### REQ-SHELL-05 — Export CSV

The system MUST offer **Exportar CSV** for the active report table with UTF-8 BOM and column headers in Spanish.

### REQ-SHELL-06 — Empty states

When a report returns zero rows, the system MUST show an explanatory message in Spanish and, where applicable, a link to the relevant operational screen (tablero, parte).

### REQ-SHELL-07 — UI canónica

The shell MUST follow patterns documented in `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` and reuse visual tokens from `tablero_produccion.html` / `tablero.html`.

The shell MUST NOT use ventas objetivos/presupuestos templates as visual reference.

### REQ-SHELL-08 — Idioma

All user-visible labels, tooltips, and error messages MUST be in Spanish.

### REQ-SHELL-09 — Compatibilidad URL legacy

Query param `tipo=` from pre-refactor URLs MUST map to equivalent `grupo` + `reporte` per `mpr-reportes-legacy` spec without 404.

---

## Scenarios

### ESC-SHELL-01 — Entrada default

**Given** usuario autenticado con acceso MPR  
**When** navega a `/mpr/reportes/`  
**Then** ve grupo Producción, reporte Resumen diario, período últimos 7 días, KPI strip y tabla o empty state

### ESC-SHELL-02 — Cambio de período

**Given** hub cargado  
**When** usuario selecciona preset «Hoy»  
**Then** URL actualiza `desde`/`hasta`, KPI strip y tabla recargan sin full page reload (Alpine fetch o submit GET)

### ESC-SHELL-03 — Histórico colapsado

**Given** hub cargado  
**When** usuario expande «Histórico OPT»  
**Then** ve reportes legacy etiquetados; copy advierte fuente OPT
