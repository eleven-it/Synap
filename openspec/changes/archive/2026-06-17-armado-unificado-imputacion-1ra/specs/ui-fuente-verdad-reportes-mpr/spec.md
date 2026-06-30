# Delta for ui-fuente-verdad-reportes-mpr

## MODIFIED Requirements

### Requirement: Superficies UI consideradas fuente de verdad

The organization MUST tratar como **referencia canónica de UX/UI** (layout, jerarquía visual, patrones de feedback, tablas responsive, héroes, modales de carga, breadcrumbs y accesibilidad mínima documentada) las siguientes superficies implementadas en el código:

- **Reportes:** vistas bajo la ruta HTTP `/reports/dashboard/<slug>/` resueltas por `DashboardDetailView`, usando por defecto la plantilla `reports/dashboard_detail.html`, y la plantilla `reports/executive_summary.html` cuando el slug sea el de resumen ejecutivo definido en código.
- **MPR:** vistas bajo `/mpr/wizard/` (asistente de producción), el conjunto de rutas `/mpr/opt/...` para listado, detalle, creación y OPP (sin CTAs de armado en detalle), **`/mpr/armado/`** (Armado 1ra y 2da unificado), **`/mpr/imputacion-armado-1ra/`** (supervisor), incluyendo `mpr/base_mpr.html` y plantillas que extienden dicho layout para esos flujos.

(Previously: incluía armado de OPT en `/mpr/opt/...` y no listaba `/mpr/armado/` como canon.)

#### Scenario: Identificación de canon para un informe nuevo

- **GIVEN** un desarrollador o agente debe proponer una nueva pantalla de consulta tipo “dashboard” con filtros y tabla
- **WHEN** busca patrones de UI a reutilizar en Synap
- **THEN** MUST consultar primero `reports/dashboard_detail.html`, los includes bajo `reports/includes/` aplicables y los estáticos `reports/static/reports/js/` según el modo declarativo o legacy descrito en el diseño del cambio archivado
- **AND** MUST NOT tomar como referencia las plantillas de Objetivos de venta ni Presupuestos en `ventas/templates/` hasta que producto levante explícitamente esa exclusión

#### Scenario: Identificación de canon para un flujo tipo asistente o OPT

- **GIVEN** un desarrollador o agente debe alinear una pantalla de producción con el resto del módulo MPR
- **WHEN** elige componentes o clases Tailwind de referencia
- **THEN** MUST basarse en `mpr/wizard.html`, `mpr/opt_list.html`, `mpr/opt_detail.html`, **`mpr/armado.html`** (o evolución de `armado_surtido.html`) y `mpr/base_mpr.html`

#### Scenario: Canon para pantalla de armado POS

- **GIVEN** un desarrollador implementa o migra flujo de armado con carrito
- **WHEN** busca referencia visual en MPR
- **THEN** MUST usar `/mpr/armado/` y includes asociados
- **AND** MUST NOT usar `mpr/armado_opt.html` ni CTAs de armado en `opt_detail.html` como patrón canónico
