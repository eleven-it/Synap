# mpr-imputacion-armado-1ra Specification

## Purpose

Reconciliar demanda de pedidos **1.ª** tras Armado 1ra: el **supervisor** imputa cada **MSTOCK** a pedidos/demanda abierta. UI agrupa por lote de ejecución; unidad contable = movimiento.

*Archivado desde el cambio OpenSpec `armado-unificado-imputacion-1ra` (17/06/2026).*

## Requirements

### Requirement: Cola de MSTOCK pendientes

The system MUST listar MSTOCK de Armado 1ra con imputación incompleta. Armado 2da MUST NOT aparecer en esta cola. Each MSTOCK MUST show comprobante, pack, cantidad armada, fecha, operario, lote de ejecución.

#### Scenario: MSTOCK 1ra pendiente visible

- GIVEN un MSTOCK Armado 1ra recién grabado
- WHEN supervisor abre `/mpr/imputacion-armado-1ra/`
- THEN MUST aparecer en lista pendientes con cantidad imputable

#### Scenario: MSTOCK 2da excluido

- GIVEN MSTOCK de Armado 2da
- WHEN supervisor abre imputación
- THEN MUST NOT listarse

### Requirement: Permiso supervisor

Only users with permission `mpr.imputar_armado_1ra` (or equivalent) MUST confirmar imputación. Operarios sin permiso MUST receive 403.

#### Scenario: Operario sin permiso

- GIVEN usuario sin permiso imputación
- WHEN accede POST imputación
- THEN MUST respond 403

### Requirement: Imputación por movimiento

The supervisor MUST imputar against individual `codigo_movimiento` (MSTOCK). Sum of imputed quantities MUST NOT exceed `cantidad_armada` of that MSTOCK. Partial imputation across multiple pedidos MUST be allowed.

#### Scenario: Imputación parcial a un pedido

- GIVEN MSTOCK con 10 packs y pedido con demanda 6
- WHEN supervisor confirma imputación 6 al pedido
- THEN MUST quedar 4 packs pendientes de imputar en ese MSTOCK

#### Scenario: Exceder cantidad armada

- GIVEN MSTOCK con 5 packs
- WHEN supervisor intenta imputar 8
- THEN MUST rechazar con mensaje claro

### Requirement: Sugerencia FIFO

The system SHOULD suggest imputation FIFO over open demand (`lista_produccion_detalle`) for the same `id_articulo`. Supervisor MUST confirm or adjust manually with audit trail (`origen_regla`: FIFO | MANUAL).

#### Scenario: Confirmar sugerencia FIFO

- GIVEN demanda abierta pedido A (más antiguo) y B del mismo artículo
- WHEN supervisor confirma sugerencia
- THEN MUST asignar primero a pedido A hasta agotar demanda o cantidad MSTOCK

### Requirement: Actualización demanda

On confirmed imputation, the system MUST reduce pending demand in legacy `lista_produccion_detalle` / agrupada and MUST update `comp_ped.estado_pedido_opt` when rules apply (Parcial / Terminado).

#### Scenario: Pedido cubierto por imputación

- GIVEN pedido con demanda restante 0 tras imputación
- WHEN se confirma última imputación
- THEN MUST actualizar estado pedido según reglas MPR existentes
