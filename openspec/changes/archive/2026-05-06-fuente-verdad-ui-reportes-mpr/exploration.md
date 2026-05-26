# Exploración: fuente de verdad UI (Reportes + MPR)

## Pregunta

Definir en el proyecto qué superficies de Synap son **referencia canónica** de UX/UI para futuras migraciones y para alinear documentación y agentes, excluyendo temporalmente Presupuestos y Objetivos de venta.

## Hallazgos (evidencia en código)

### Reportes — `/reports/dashboard/<slug>/`

- Vista: `reports.views.DashboardDetailView`, plantilla por defecto `reports/dashboard_detail.html`.
- Excepción de plantilla: slug `resumen-ejecutivo-ventas` → `reports/executive_summary.html`.
- Contexto expone `dashboard_api_url` (query), `schema_api_url`, `is_declarative`, `report_config_for_script`.
- **Modo declarativo:** `widget_engine.js`, D3, script inline de inicialización; configuración vía `json_script` + `window.REPORT_CONFIG`.
- **Modo legacy:** `dashboard.js` (módulo); scripts por slug (p. ej. logística, BO stock). Slugs de objetivos cargan `objetivos_ventas_bo.js` — **no** se usan como referencia de producto/UI según decisión de negocio; el **shell** del dashboard (hero, filtros includes, modales de carga, export) sí.
- Patrones visuales: paleta slate/sky/violet, fullscreen opcional, includes `reports/includes/filters_*.html`, modal `#reports-legacy-query-loading-modal` para ciertos informes legacy.

### MPR — `/mpr/wizard/` y `/mpr/opt/...`

- Rutas en `mpr/urls.py`: `wizard`, `opt_list`, `opt_detail`, `armado_opt`, etc.
- Layout: `mpr/base_mpr.html` → `base_app.html`; formularios `.mpr-post-loading` abren modal de espera; error de esquema MySQL con modal accesible.
- `wizard.html`: hero oscuro slate alineado a OPT, pasos 1–5, barra de progreso con ARIA, tarjetas `rounded-2xl`, acento purple, Material Icons.
- `opt_list.html` / `opt_detail.html`: breadcrumbs, tablas responsive, Alpine para búsqueda en listado, chips de fase/estado.

### Fuera de canon (explícito)

- Plantillas `ventas/templates/ventas/*` (objetivos, presupuestos): **no** son fuente de verdad UI hasta nuevo diseño.

## Conclusión

El cambio debe **documentar y gobernar** esta decisión (docs + OpenSpec), sin obligar refactor inmediato de pantallas ventas.
