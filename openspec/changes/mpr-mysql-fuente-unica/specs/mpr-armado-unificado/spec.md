# Delta for mpr-armado-unificado

## ADDED Requirements

### Requirement: Persistencia armado surtido en MySQL

El sistema MUST persistir trazabilidad de armado en tablas MySQL: `mpr_articulo_armado_surtido`, `mpr_armado_lote`, `mpr_armado_surtido_movimiento`, `mpr_armado_surtido_linea`. PK autonuméricas `id_mpr_*`; UUID opcionales para migración. MUST NOT columna `base_empresa`. MSTOCK legacy MUST seguir en `movimiento_stock`/`stock`.

#### Scenario: Lote armado crea cabecera MySQL

- DADO ejecución exitosa de lote modo 2da
- CUANDO commit transacción
- ENTONCES MUST existir fila en `mpr_armado_lote` y movimiento en `mpr_armado_surtido_movimiento` con `codigo_movimiento` MSTOCK

#### Scenario: Sin Postgres tras cutover

- DADO cutover P3
- CUANDO se ejecuta armado
- ENTONCES MUST NOT insertarse en Postgres tablas `mpr_armado*`

---

## MODIFIED Requirements

### Requirement: Lote exclusivo por modo

The system MUST NOT permitir mezclar packs de modo 1ra y 2da en el mismo lote. Referencia de lote MUST usar `id_mpr_armado_lote` MySQL (no UUID Postgres como PK operativa).

(Previously: `MprArmadoLote` UUID PK en Postgres.)

#### Scenario: Cambio de modo con carrito ocupado

- GIVEN carrito con ítems modo 2da
- WHEN el usuario cambia a modo 1ra
- THEN MUST pedir confirmación
- AND MUST vaciar el carrito al confirmar
