# ui-fuente-verdad-reportes-mpr

## Purpose

Normativa de **referencia canónica de interfaz** en Synap para migraciones, revisiones y asistentes automatizados. Comportamiento exigible: **gobernanza documental y proceso**; no altera por sí misma rutas ni vistas de aplicación.

Documento operativo asociado: `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`.

*Archivado desde los cambios OpenSpec `fuente-verdad-ui-reportes-mpr` (06/05/2026) y `armado-unificado-imputacion-1ra` (17/06/2026).*

## Requirements

### Requirement: Superficies UI consideradas fuente de verdad

The organization MUST tratar como **referencia canónica de UX/UI** (layout, jerarquía visual, patrones de feedback, tablas responsive, héroes, modales de carga, breadcrumbs y accesibilidad mínima documentada) las siguientes superficies implementadas en el código:

- **Reportes:** vistas bajo la ruta HTTP `/reports/dashboard/<slug>/` resueltas por `DashboardDetailView`, usando por defecto la plantilla `reports/dashboard_detail.html`, y la plantilla `reports/executive_summary.html` cuando el slug sea el de resumen ejecutivo definido en código.
- **MPR:** vistas bajo `/mpr/wizard/` (asistente de producción), el conjunto de rutas `/mpr/opt/...` para listado, detalle, creación y OPP (sin CTAs de armado en detalle), **`/mpr/armado/`** (Armado 1ra y 2da unificado), **`/mpr/imputacion-armado-1ra/`** (supervisor), incluyendo `mpr/base_mpr.html` y plantillas que extienden dicho layout para esos flujos.

#### Scenario: Identificación de canon para un informe nuevo

- **GIVEN** un desarrollador o agente debe proponer una nueva pantalla de consulta tipo “dashboard” con filtros y tabla
- **WHEN** busca patrones de UI a reutilizar en Synap
- **THEN** MUST consultar primero `reports/dashboard_detail.html`, los includes bajo `reports/includes/` aplicables y los estáticos `reports/static/reports/js/` según el modo declarativo o legacy descrito en el diseño del cambio archivado
- **AND** MUST NOT tomar como referencia las plantillas de Objetivos de venta ni Presupuestos en `ventas/templates/` hasta que producto levante explícitamente esa exclusión

#### Scenario: Identificación de canon para un flujo tipo asistente o OPT

- **GIVEN** un desarrollador o agente debe alinear una pantalla de producción con el resto del módulo MPR
- **WHEN** elige componentes o clases Tailwind de referencia
- **THEN** MUST basarse en `mpr/wizard.html`, `mpr/opt_list.html`, `mpr/opt_detail.html`, **`mpr/armado_tablero.html`** (Armado unificado 1ra/2da en grilla), **`mpr/imputacion_armado_1ra.html`** y `mpr/base_mpr.html`
- **AND** MUST NOT usar `mpr/armado_surtido.html` (POS deprecado) como patrón canónico

#### Scenario: Canon para pantalla de armado

- **GIVEN** un desarrollador implementa o migra flujo de armado
- **WHEN** busca referencia visual en MPR
- **THEN** MUST usar `/mpr/armado/?vista=tablero` y la plantilla `armado_tablero.html`
- **AND** MUST NOT usar `mpr/armado_opt.html`, CTAs de armado en `opt_detail.html` ni `armado_surtido.html` (POS) como patrón canónico

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

---

### Requirement: Pantallas crédito pedidos — look Alta Movimiento

Las pantallas nuevas del módulo crédito pedidos (ABM políticas, cola Finanzas, editor plantillas cobranza) MUST seguir el patrón visual **Alta Movimiento** (`stock/alta_movimiento.html`, `docs/stock/ALTA_MOVIMIENTO_UX.md`) y/o canon reports/MPR (`reports/dashboard_detail.html`, `mpr/base_mpr.html`). MUST usar modales Synap y toasts `mprShowAviso`/`SynapMessages`. MUST NOT extender ni reutilizar como base las plantillas ecom de pedidos (`ecom/templates/ecom/pedidos_*`, hub kanban, detalle pedido).

#### Scenario: ABM políticas alineado a Alta Movimiento

- **GIVEN** desarrollador implementa pantalla ABM de políticas crédito
- **WHEN** define layout y componentes
- **THEN** MUST basarse en estructura Alta Movimiento (header, paneles, tablas, CTAs)
- **AND** MUST NOT copiar markup predominante de `ventas/templates/ventas/` ni hub ecom pedidos

#### Scenario: Cola Finanzas — canon UI

- **GIVEN** pantalla de cola de aprobación Finanzas
- **WHEN** se renderiza listado con acciones aprobar/rechazar
- **THEN** MUST usar modales Synap para confirmaciones
- **AND** MUST NOT usar `alert`/`confirm`/`prompt` nativos

#### Scenario: Code review rechaza ecom pedidos como referencia

- **GIVEN** PR de UI crédito que cita `ecom/templates/ecom/pedidos_hub.html` como patrón principal
- **WHEN** revisa contra este spec
- **THEN** MUST exigirse realineación a Alta Movimiento o reports/MPR
