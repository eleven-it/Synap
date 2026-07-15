# Delta — `reports-executive-dashboard`

**Cambio:** `adminnet-module-migration-command-center-finance`

---

## ADDED Requirements

### Requirement: Área tesorería en orquestador

El orquestador **MUST** incluir **`areas.tesoreria`** con el mismo subconjunto de campos que `GET .../tesoreria/resumen/` (sin `meta` anidado duplicado).

#### Scenario: Orquestador con tesorería

- GIVEN usuario gerencial con `base_empresa` válida
- WHEN `GET /api/reports/executive-dashboard/`
- THEN `areas.tesoreria` contiene `saldo_inicial`, `saldo_final`, `variacion_neta`, `banco_disponible=false`

### Requirement: Área ventas por cobro en orquestador

El orquestador **MUST** incluir **`areas.ventas_cobros`** con `facturado_por_medio` y `cobrado_caja_por_medio`.

#### Scenario: Orquestador con ventas cobros

- GIVEN usuario gerencial
- WHEN `GET /api/reports/executive-dashboard/`
- THEN `areas.ventas_cobros.facturado_por_medio` y `areas.ventas_cobros.cobrado_caja_por_medio` existen

### Requirement: Banco anidado en tesorería

El orquestador **MUST** incluir **`areas.tesoreria.banco`** con KPIs de `librobanco` (segunda llamada `_safe_legacy_area`), sin sumar con caja.

#### Scenario: Orquestador con banco anidado

- GIVEN usuario gerencial
- WHEN `GET /api/reports/executive-dashboard/`
- THEN `areas.tesoreria.banco` contiene `saldo_banco_inicial`, `saldo_banco_final`, `disponible`

### Requirement: Enlaces API P1 financiero

- **`meta.endpoints`** **MUST** incluir `tesoreria_banco`, `tesoreria_movimientos_caja`, `ventas_cobros_detalle`.

#### Scenario: Endpoints en meta

- GIVEN respuesta 200 del orquestador
- WHEN se lee `meta.endpoints`
- THEN existen claves que apuntan a `/api/reports/executive-dashboard/tesoreria/resumen/` y `/api/reports/executive-dashboard/ventas/cobros/resumen/`

---

## MODIFIED Requirements

### Requirement: Estructura `areas` del orquestador

El orquestador **MUST** devolver resúmenes P0 de: ventas, inventario, compras, manufactura, cruzados (demanda pendiente), **tesoreria**, **ventas_cobros**, y stub CRM.

- **`areas.tesoreria`** y **`areas.ventas_cobros`** **MUST** seguir el patrón de degradación parcial (`disponible: false` + `error`) si falla solo esa área, sin tumbar el payload completo (salvo fallo de ventas según política existente).
- **`areas.crm`** **MUST** permanecer stub sin KPIs inventados.

(Previously: orquestador con cinco áreas operativas sin tesorería ni ventas_cobros.)

#### Scenario: Orquestador completo P0 financiero

- GIVEN usuario gerencial con `base_empresa` válida
- WHEN `GET /api/reports/executive-dashboard/?fecha=2026-05-11`
- THEN respuesta 200 con `meta.definicion=executive-dashboard-v1` y siete áreas operativas (`ventas`, `inventario`, `compras`, `manufactura`, `cruzados`, `tesoreria`, `ventas_cobros`) más CRM stub

#### Scenario: Degradación tesorería

- GIVEN fallo transitorio MySQL solo al calcular tesorería
- WHEN `GET /api/reports/executive-dashboard/`
- THEN `areas.tesoreria.disponible=false` y otras áreas pueden seguir disponibles

#### Scenario: Sin área impuestos

- GIVEN respuesta del orquestador
- WHEN se listan claves de `areas`
- THEN no existe `areas.impuestos`

---

## REMOVED Requirements

*Ninguno.*
