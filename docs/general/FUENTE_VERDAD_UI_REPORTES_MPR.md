# Fuente de verdad UX/UI — Reportes (dashboard) y MPR (wizard / OPT)

Documento normativo para **equipo humano y agentes**: define qué superficies de Synap se usan como **referencia canónica** de interfaz al migrar formularios, diseñar pantallas nuevas o revisar PRs.

**Fecha de referencia del análisis:** 06/05/2026.

## 1. Resumen ejecutivo

| Pregunta | Respuesta |
|----------|-----------|
| ¿Qué UI copiar como patrón? | Dashboards en **`/reports/dashboard/<slug>/`** y flujos MPR **`/mpr/wizard/`**, **`/mpr/opt/...`**. |
| ¿Qué UI no usar como referencia? | Pantallas actuales de **Objetivos de venta** y **Presupuestos** bajo **`ventas/`** hasta decisión explícita de producto. |
| ¿Cambia esto código? | No por sí mismo: es **gobernanza**. Los cambios de código vienen de otros proyectos. |

## 2. Superficies canónicas

### 2.1 Reportes — dashboard por slug

- **Ruta HTTP:** `/reports/dashboard/<slug>/`
- **Vista:** `DashboardDetailView` en `reports/views.py`.
- **Plantilla por defecto:** `reports/templates/reports/dashboard_detail.html`.
- **Excepción:** slug `resumen-ejecutivo-ventas` → `reports/templates/reports/executive_summary.html`.

**Patrones de UI a respetar en nuevas pantallas “tipo informe”:**

- Sección principal con jerarquía clara (hero / barra de acciones).
- Filtros mediante includes reutilizables en `reports/templates/reports/includes/` (p. ej. `filters_period.html`, `filters_interval.html`, `filters_logistica_lista_comprobantes_rutas.html`, etc.).
- Configuración al cliente vía `json_script` y `window.REPORT_CONFIG` donde aplique.
- Modo **declarativo:** motor en `reports/static/reports/js/widget_engine.js` y D3 (`reports/static/reports/vendor/d3.min.js`).
- Modo **legacy:** `reports/static/reports/js/dashboard.js` (módulo); scripts adicionales según slug.

**Nota:** Algunos slugs cargan `objetivos_ventas_bo.js`. El **contenedor** del dashboard sigue siendo referencia; la **presentación específica de objetivos vs BO** no autoriza a usar las pantallas de `ventas/` como patrón de migración.

### 2.2 MPR — asistente y OPT

- **Rutas:** definidas en `mpr/urls.py`, en particular:
  - `wizard` → `/mpr/wizard/`
  - `armado` → `/mpr/armado/?modo=1ra|2da` (Armado unificado 1ra/2da)
  - `imputacion_armado_1ra` → `/mpr/imputacion-armado-1ra/` (supervisor)
  - `opt_list`, `opt_create`, `opt_detail`, etc. → bajo `/mpr/opt/...` (`armado_opt` redirige a `armado?modo=1ra`)
- **Layout obligatorio del módulo:** `mpr/templates/mpr/base_mpr.html` (extiende `base_app.html`).
- **Plantillas de referencia:**
  - `mpr/templates/mpr/wizard.html` — asistente por pasos, hero oscuro, barra de progreso con ARIA.
  - `mpr/templates/mpr/armado_surtido.html` — POS armado unificado (toggle 1ra/2da, carrito lote).
  - `mpr/templates/mpr/imputacion_armado_1ra.html` — cola MSTOCK e imputación supervisor.
  - `mpr/templates/mpr/opt_list.html` — listado con filtros, búsqueda con Alpine, tabla responsive.
  - `mpr/templates/mpr/opt_detail.html` — detalle con hero, estado, pasos y tablas.
- **Feedback en envíos:** formularios con clase `mpr-post-loading` / `synap-post-loading` y modal compartido `theme/templates/partials/synap_post_loading_modal.html` (API `synapShowPostLoading*`; aliases `mprShowPostLoading*`). El include legacy `mpr/includes/mpr_post_loading_modal.html` reexporta el de theme.
- **Contenedor de página:** clase **`mpr-contenedor-pagina`** (o include `mpr/includes/contenedor_pagina_open.html`) en todas las pantallas del módulo: **`w-full max-w-none`** con padding horizontal responsive (`px-3 … 2xl:px-12`). No usar `max-w-7xl`, `max-w-4xl` ni otros topes de ancho en el shell principal; las tablas usan `overflow-x-auto` cuando hace falta.

### 2.3 Implementaciones alineadas al canon (no fuentes de verdad)

Las pantillas siguientes **implementan** los patrones de §2.2 y pueden usarse como **referencia secundaria** al migrar flujos similares (filtros server-side, tabla densa, feedback Synap). **No** sustituyen a `wizard.html`, `opt_list.html` ni `dashboard_detail.html` como fuente de verdad normativa.

| Ruta | Plantilla | Uso como referencia |
|------|-----------|---------------------|
| `/mpr/parte-produccion/` | `mpr/templates/mpr/parte_produccion.html` | Planilla analista con filtros MPR, columnas sticky, turnos M/T/N, docenas/pares, modales/toast Synap (change `mpr-parte-produccion-grilla-planilla-qc`). Ver `docs/mpr/PARTE_PRODUCCION.md` § planilla QC. |

Al copiar patrones desde estas pantallas, MUST mantener `base_mpr.html`, `mpr-contenedor-pagina` y la política de modales sin diálogos nativos (`.cursor/rules/modales-sin-dialogos-nativos.mdc`).

## 3. Exclusiones explícitas (hasta nuevo aviso)

No usar como **referencia visual** para nuevas migraciones:

- `ventas/templates/ventas/objetivos_venta.html`, `objetivos_periodos_list.html`
- `ventas/templates/ventas/presupuesto_*.html`
- Rutas `/ventas/objetivos-venta/` y `/ventas/presupuestos/`

**Aclaración operativa (Presupuesto):** aunque `presupuesto_*.html` no es patrón canónico para migrar otras pantallas, debe mantener **coherencia visual y de comportamiento** con Synap (paleta, estados, accesibilidad, filtros tags compartidos). Ver `docs/general/MATRIZ_COHERENCIA_UI_PRESUPUESTO_OPERATIVO.md`.

Cuando producto apruebe un rediseño, se actualizará este documento y el spec OpenSpec `ui-fuente-verdad-reportes-mpr`.

## 4. Consistencia visual (guía práctica)

- **Reportes:** predominio de paleta **slate** / **sky** / acentos en violeta en modales de carga.
- **MPR:** mezcla de **slate** en héroes y **purple** en acentos y foco; fondos **gray** o **slate** según pantalla.
- **Objetivo a medio plazo:** converger en una convención única de grises (documentado como deuda en el `design.md` del cambio OpenSpec).

## 5. Enlaces relacionados

- Spec normativo vigente: `openspec/specs/ui-fuente-verdad-reportes-mpr/spec.md`
- Auditoría del cambio (archivado): `openspec/changes/archive/2026-05-06-fuente-verdad-ui-reportes-mpr/`
- Política de documentación: [POLITICA_DOCUMENTACION.md](POLITICA_DOCUMENTACION.md)
- Metodología inventarios VB6: [INVENTARIO_MIGRACION_FORMULARIOS.md](INVENTARIO_MIGRACION_FORMULARIOS.md)

## 6. Mantenimiento

Quien altere de forma **sustancial** el shell de `dashboard_detail.html`, el wizard MPR o el layout `base_mpr.html` MUST actualizar este archivo en el mismo commit o en uno inmediato, y planificar actualización del spec al archivar el cambio OpenSpec correspondiente.
