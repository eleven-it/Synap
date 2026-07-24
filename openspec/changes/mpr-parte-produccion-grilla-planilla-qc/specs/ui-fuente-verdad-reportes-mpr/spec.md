# Delta — ui-fuente-verdad-reportes-mpr

**Change:** `mpr-parte-produccion-grilla-planilla-qc`

---

## ADDED Requirements

### Requirement: Grilla analista parte-produccion alineada al canon MPR

La pantalla `/mpr/parte-produccion/` (captura analista) MUST implementar filtros, tabla planilla, estados vacíos, feedback AJAX y confirmaciones siguiendo el canon definido en `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` y las superficies MPR (`mpr/base_mpr.html`, `mpr/opt_list.html`, patrones de `/reports/dashboard/<slug>/` para filtros y tablas responsive). MUST NOT tomar como referencia visual Objetivos de venta ni Presupuestos en `ventas/templates/`. MUST NOT usar diálogos nativos del navegador.

#### Scenario: Revisión de layout filtros y grilla

- **GIVEN** un PR modifica `mpr/templates/mpr/parte_produccion.html`
- **WHEN** un revisor evalúa la UI
- **THEN** MUST verificarse alineación con filtros MPR existentes, tabla responsive y modales Synap del canon
- **AND** MUST rechazarse patrones copiados de `ventas/templates/ventas/`

#### Scenario: Feedback operativo sin alert nativo

- **GIVEN** una acción AJAX en la grilla analista (guardar, validación cupo)
- **WHEN** el usuario recibe feedback
- **THEN** MUST usarse toast/modal Synap documentado
- **AND** MUST NOT usarse `alert`/`confirm`/`prompt`

#### Scenario: Documentación actualizada tras cambio sustancial

- **GIVEN** el refactor de grilla planilla QC se fusiona
- **WHEN** cambia sustancialmente la UX de `/mpr/parte-produccion/`
- **THEN** `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` MUST actualizarse en el mismo commit o uno inmediato
- **AND** MUST mencionar la pantalla como implementación alineada al canon (no como nueva fuente de verdad)

---

## MODIFIED Requirements

### Requirement: Superficies UI consideradas fuente de verdad

The organization MUST tratar como **referencia canónica de UX/UI** (layout, jerarquía visual, patrones de feedback, tablas responsive, héroes, modales de carga, breadcrumbs y accesibilidad mínima documentada) las siguientes superficies implementadas en el código:

- **Reportes:** vistas bajo la ruta HTTP `/reports/dashboard/<slug>/` resueltas por `DashboardDetailView`, usando por defecto la plantilla `reports/dashboard_detail.html`, y la plantilla `reports/executive_summary.html` cuando el slug sea el de resumen ejecutivo definido en código.
- **MPR:** vistas bajo `/mpr/wizard/` (asistente de producción), el conjunto de rutas `/mpr/opt/...` para listado, detalle, creación y OPP (sin CTAs de armado en detalle), **`/mpr/armado/`** (Armado 1ra y 2da unificado), **`/mpr/imputacion-armado-1ra/`** (supervisor), **`/mpr/parte-produccion/`** (captura analista; MUST seguir el canon, no redefinirlo), incluyendo `mpr/base_mpr.html` y plantillas que extienden dicho layout para esos flujos.

(Previously: `/mpr/parte-produccion/` no listada; sin obligación explícita de alineación al canon en esta capability.)

#### Scenario: Identificación de canon para un informe nuevo

- **GIVEN** un desarrollador o agente debe proponer una nueva pantalla de consulta tipo “dashboard” con filtros y tabla
- **WHEN** busca patrones de UI a reutilizar en Synap
- **THEN** MUST consultar primero `reports/dashboard_detail.html`, los includes bajo `reports/includes/` aplicables y los estáticos `reports/static/reports/js/` según el modo declarativo o legacy descrito en el diseño del cambio archivado
- **AND** MUST NOT tomar como referencia las plantillas de Objetivos de venta ni Presupuestos en `ventas/templates/` hasta que producto levante explícitamente esa exclusión

#### Scenario: Identificación de canon para un flujo tipo asistente o OPT

- **GIVEN** un desarrollador o agente debe alinear una pantalla de producción con el resto del módulo MPR
- **WHEN** elige componentes o clases Tailwind de referencia
- **THEN** MUST basarse en `mpr/wizard.html`, `mpr/opt_list.html`, `mpr/opt_detail.html`, **`mpr/armado_surtido.html`** (POS armado unificado 1ra/2da), **`mpr/imputacion_armado_1ra.html`**, **`mpr/parte_produccion.html`** (layout filtros/grilla analista) y `mpr/base_mpr.html`

#### Scenario: Canon para pantalla de armado POS

- **GIVEN** un desarrollador implementa o migra flujo de armado con carrito
- **WHEN** busca referencia visual en MPR
- **THEN** MUST usar `/mpr/armado/` y includes asociados (`armado_surtido.html`)
- **AND** MUST NOT usar `mpr/armado_opt.html` ni CTAs de armado en `opt_detail.html` como patrón canónico
