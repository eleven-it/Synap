# Delta for mpr-imputacion-armado-1ra

## ADDED Requirements

### Requirement: Persistencia imputación en MySQL

El sistema MUST registrar imputaciones supervisor en **`mpr_imputacion_armado`**: PK `id_mpr_imputacion_armado`, `codigo_movimiento` (MSTOCK 1ra), `id_articulo_pack`, `cantidad`, `codigo_movimiento_pedido`, `id_lista_detalle` NULL, `origen_regla` (FIFO/MANUAL), `id_usuario_supervisor`, `imputado_en`, `notas`. MUST NOT columna `base_empresa`.

#### Scenario: Imputación parcial persiste MySQL

- DADO MSTOCK 1ra con 10 packs
- CUANDO supervisor imputa 6 a un pedido
- ENTONCES MUST existir fila en `mpr_imputacion_armado` con cantidad=6

#### Scenario: Cola lee imputaciones MySQL

- DADO cutover P3
- CUANDO supervisor abre cola pendientes
- ENTONCES MUST calcular pendiente desde `mpr_imputacion_armado` + MSTOCK MySQL
- Y MUST NOT consultar Postgres `MprImputacionArmado`

---

## MODIFIED Requirements

### Requirement: Imputación por movimiento

The supervisor MUST imputar against individual `codigo_movimiento` (MSTOCK). Registro contable MUST persistir en `mpr_imputacion_armado` MySQL. Sum of imputed quantities MUST NOT exceed `cantidad_armada` of that MSTOCK.

(Previously: `MprImputacionArmado.objects` Postgres con `base_empresa`.)

#### Scenario: Exceder cantidad armada

- GIVEN MSTOCK con 5 packs
- WHEN supervisor intenta imputar 8
- THEN MUST rechazar con mensaje español
- AND MUST NOT insertar en `mpr_imputacion_armado`
