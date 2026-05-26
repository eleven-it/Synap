# ui-fuente-verdad-reportes-mpr

## Purpose

Normativa de **referencia canónica de interfaz** en Synap para migraciones, revisiones y asistentes automatizados. Comportamiento exigible: **gobernanza documental y proceso**; no altera por sí misma rutas ni vistas de aplicación.

Documento operativo asociado: `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`.

*Archivado desde el cambio OpenSpec `fuente-verdad-ui-reportes-mpr` (06/05/2026).*

## Requirements

### Requirement: Superficies UI consideradas fuente de verdad

The organization MUST tratar como **referencia canónica de UX/UI** (layout, jerarquía visual, patrones de feedback, tablas responsive, héroes, modales de carga, breadcrumbs y accesibilidad mínima documentada) las siguientes superficies implementadas en el código:

- **Reportes:** vistas bajo la ruta HTTP `/reports/dashboard/<slug>/` resueltas por `DashboardDetailView`, usando por defecto la plantilla `reports/dashboard_detail.html`, y la plantilla `reports/executive_summary.html` cuando el slug sea el de resumen ejecutivo definido en código.
- **MPR:** vistas bajo `/mpr/wizard/` (asistente de producción) y el conjunto de rutas `/mpr/opt/...` (listado, detalle, creación, armado de OPT y acciones asociadas en `mpr/urls.py`), incluyendo el layout `mpr/base_mpr.html` y las plantillas que extienden dicho layout para esos flujos.

#### Scenario: Identificación de canon para un informe nuevo

- **GIVEN** un desarrollador o agente debe proponer una nueva pantalla de consulta tipo “dashboard” con filtros y tabla
- **WHEN** busca patrones de UI a reutilizar en Synap
- **THEN** MUST consultar primero `reports/dashboard_detail.html`, los includes bajo `reports/includes/` aplicables y los estáticos `reports/static/reports/js/` según el modo declarativo o legacy descrito en el diseño del cambio archivado
- **AND** MUST NOT tomar como referencia las plantillas de Objetivos de venta ni Presupuestos en `ventas/templates/` hasta que producto levante explícitamente esa exclusión

#### Scenario: Identificación de canon para un flujo tipo asistente o OPT

- **GIVEN** un desarrollador o agente debe alinear una pantalla de producción con el resto del módulo MPR
- **WHEN** elige componentes o clases Tailwind de referencia
- **THEN** MUST basarse en `mpr/wizard.html`, `mpr/opt_list.html`, `mpr/opt_detail.html` y `mpr/base_mpr.html`

### Requirement: Exclusión explícita de Ventas (objetivos y presupuestos) como referencia UI

The organization MUST NOT citar ni imitar como **patrón de referencia visual** las pantallas actuales de **Objetivos de venta** y **Presupuestos** servidas desde la app `ventas/` (rutas bajo `/ventas/objetivos-venta/` y `/ventas/presupuestos/`, plantillas en `ventas/templates/ventas/`) para nuevos diseños o migraciones, **hasta** que una decisión de producto documentada revoque esta exclusión.

#### Scenario: Code review de migración de formulario

- **GIVEN** un PR migra un formulario desde VB6 hacia Synap
- **WHEN** el autor justifica decisiones de UI solo con capturas o código de `ventas/objetivos_venta.html` o presupuestos
- **THEN** el revisor MUST pedir realineación a la fuente de verdad definida en `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` o MUST documentar la excepción aprobada por producto

#### Scenario: Asistente automatizado genera UI

- **GIVEN** un asistente propone markup o clases Tailwind para una pantalla ERP nueva
- **WHEN** la propuesta copia estructura predominante de `ventas/templates/ventas/` para objetivos o presupuestos
- **THEN** el resultado MUST ser rechazado o corregido para seguir el canon reportes/MPR, salvo instrucción explícita contraria de producto

### Requirement: Documento general de referencia

The system MUST mantener en el repositorio un documento en español en `docs/general/` que liste rutas canónicas, plantillas clave, estáticos relevantes, exclusiones y notas de consistencia (p. ej. paletas `slate` vs `gray`), actualizado cuando cambien sustancialmente las superficies canónicas.

#### Scenario: Cambio mayor en dashboard de reportes

- **GIVEN** se refactoriza la plantilla `dashboard_detail.html` o se introduce un nuevo modo de renderizado por defecto para dashboards
- **WHEN** el cambio se fusiona en la rama de desarrollo
- **THEN** el documento en `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` MUST actualizarse en el mismo commit o en uno inmediato

### Requirement: Coherencia con OpenSpec

Los cambios futuros que alteren la definición de “fuente de verdad UI” MUST actualizar esta capability en `openspec/specs/ui-fuente-verdad-reportes-mpr/spec.md` y el documento general correspondiente.

#### Scenario: Producto rehabilita Ventas como referencia

- **GIVEN** producto decide que una pantalla de `ventas/` pasa a ser canónica
- **WHEN** se aprueba la decisión
- **THEN** MUST modificarse este spec y `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` en la misma entrega de planificación
