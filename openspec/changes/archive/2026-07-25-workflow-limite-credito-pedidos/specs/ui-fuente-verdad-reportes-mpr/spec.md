# Delta for ui-fuente-verdad-reportes-mpr

## ADDED Requirements

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
