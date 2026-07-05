# Delta for mpr-transiciones-lote

## MODIFIED Requirements

### Requirement: Modelo MprTransicionLote

El sistema MUST registrar trazabilidad de transiciones en MySQL **`mpr_transicion_lote`**: `id_mpr_transicion_lote` PK AI, `id_articulo`, `tipo_origen`, `tipo_destino`, `cantidad`, `codigo_movimiento` (MSTOCK), `id_usuario`, `creado_en`. Índice `(id_articulo, creado_en)`. MUST NOT columna `base_empresa`. MUST crearse en la misma transacción MySQL que el MSTOCK.

(Previously: modelo Django Postgres `MprTransicionLote` con `base_empresa`.)

#### Scenario: Transición crea fila MySQL

- DADO transferencia Produccion→SemiElaborado exitosa
- CUANDO commit MSTOCK
- ENTONCES MUST existir fila en `mpr_transicion_lote` con tipos y cantidad correctos

#### Scenario: Sin fila Postgres tras cutover

- DADO cutover P3
- CUANDO se ejecuta transición
- ENTONCES MUST NOT insertarse en Postgres `mpr_transicion_lote`

---

### Requirement: Servicio de Transferencia Entre Etapas

`transferir_stock_entre_etapas` MUST invocar repositorio MySQL para insertar `mpr_transicion_lote`. Comportamiento de validación, MSTOCK y `stock_deposito` MUST permanecer inalterado.

(Previously: `MprTransicionLote.objects.create(base_empresa=...)`.)

#### Scenario: Happy path Produccion→Semi Elaborado

- DADO stock Produccion=100, Semi=20
- CUANDO transferir 30 unidades
- ENTONCES saldos físicos MUST actualizarse
- Y `mpr_transicion_lote` MUST registrar origen/destino/cantidad
