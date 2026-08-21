# Delta — Transiciones de lote (confirmación CC atómica)

**Capability:** `mpr-transiciones-lote`  
**Change:** `mpr-cc-consolidado-articulo`  
**Base:** `openspec/specs/mpr-transiciones-lote/spec.md`

---

## ADDED Requirements

### Requirement: Confirmación CC atómica por artículo

El flujo de **confirmación de control de calidad** (`RegistrarClasificacionProduccionView` y servicio asociado) MUST ejecutar todas las transferencias de **un mismo artículo** (Semi + todas las 2da + todas las scrap del POST) dentro de **una transacción Django `atomic()`** por artículo. Si cualquier destino del artículo falla, MUST hacer rollback completo de ese artículo (stock, MSTOCK y `mpr_transicion_lote`). Los demás artículos del mismo POST MAY procesarse en transacciones independientes.

#### Scenario: Semi y 2da en un solo commit

- DADO POST con Semi 80 y 2da 20 del mismo artículo y saldo 100
- CUANDO se confirma exitosamente
- ENTONCES Prod disminuye 100, existen filas Semi y 2da, y ambas comparten el mismo resultado atómico del artículo

#### Scenario: Fallo en 2da tras Semi validado

- DADO POST Semi+2da del mismo artículo y fallo inyectado en transferencia 2da
- CUANDO se confirma
- ENTONCES rollback del artículo: saldo Producción intacto, sin fila Semi nueva, sin fila 2da

#### Scenario: Éxito parcial entre artículos

- DADO POST con artículo 1 válido y artículo 2 que excede saldo
- CUANDO se confirma el lote
- ENTONCES artículo 1 persiste completo; artículo 2 no mueve stock ni ledger

---

### Requirement: Wrapper CC sin alterar transferir_stock_lote genérico

El sistema MUST proveer un **wrapper o ruta dedicada CC** (p. ej. `confirmar_clasificacion_articulo_atomic` o equivalente) que agrupe llamadas a `transferir_stock_entre_etapas` por artículo dentro de `atomic()`. `transferir_stock_lote` MUST conservar comportamiento **best-effort sin `atomic()`** para otros consumidores (pantallas de lote, tablero). MUST NOT modificar la firma ni semántica best-effort de `transferir_stock_lote`.

(Previously: no existía ruta atómica; CC reutilizaba best-effort.)

#### Scenario: Lote genérico sigue best-effort

- DADO `transferir_stock_lote` con dos ítems y el segundo falla por saldo
- CUANDO se invoca desde pantalla de lote no-CC
- ENTONCES `exitosas=1`, `fallidas=1` y el primer ítem permanece confirmado

#### Scenario: CC no usa transferir_stock_lote directo

- DADO confirmación de control de calidad desde clasificación-producción
- CUANDO se procesa un artículo
- ENTONCES MUST NOT delegar en `transferir_stock_lote` sin envoltorio atómico por artículo

---

### Requirement: Borrador CC solo tras éxito del artículo

Tras confirmación CC, el sistema MUST borrar líneas de borrador **solo** de artículos confirmados OK. MUST NOT borrar borrador de artículos cuya transacción atómica falló o no se intentó por validación previa.

#### Scenario: Borrador preservado en fallo

- DADO borrador con artículos A y B y fallo atómico en B
- CUANDO termina el POST
- ENTONCES borrador de A se elimina y borrador de B permanece

---

### Requirement: Escritura CC en transicion_lote

Dentro de la transacción atómica CC, cada transferencia exitosa MUST crear `mpr_transicion_lote` con `cantidad_extra = 0`, `fecha_produccion` del día clasificado, Semi con operario/turno NULL, 2da/scrap con operario y turno del parte. MUST NOT insertar filas con cantidad ≤ 0.

#### Scenario: Semi CC sin operario en ledger

- CUANDO la transacción CC acredita Semi
- ENTONCES la fila SemiElaborado tiene `id_operario NULL`, `id_mpr_turno NULL`, `cantidad_extra = 0`

#### Scenario: Suma insertada igual al POST

- CUANDO la transacción CC confirma qty del POST del artículo
- ENTONCES `SUM(cantidad)` de filas insertadas en esa transacción equals qty confirmada del artículo
