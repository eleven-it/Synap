# Delta for mpr-envio-produccion-tablero

## MODIFIED Requirements

### Requirement: Modelo MprEnvioProduccion

El sistema MUST persistir cada envío en la tabla MySQL **`mpr_envio_produccion`** (no en Postgres). Campos mínimos: `id_mpr_envio_produccion` (PK AI), `id_articulo` (COMPONENTE), `cantidad` (DECIMAL), `id_usuario`, `creado_en`, `anulado` (default 0). MUST existir índices `(id_articulo, creado_en)`. MUST NOT existir columna `base_empresa`. El despliegue MUST ser vía proveedor catalog MySQL, no migración Django Postgres.

(Previously: ledger Django Postgres `MprEnvioProduccion` con `base_empresa` y migración 0014.)

#### Scenario: Registro de un envío

- DADO un componente válido con pendiente > 0 y un usuario autenticado en BD `administranet92`
- CUANDO el servicio registra un envío de cantidad 10
- ENTONCES MUST existir una fila en `mpr_envio_produccion` con `id_articulo` correcto, `cantidad=10`, `anulado=0`, `creado_en` poblado

#### Scenario: Despliegue vía catalog MySQL

- DADO BD empresa sin tabla `mpr_envio_produccion`
- CUANDO se ejecuta proveedor `mpr_core_tables`
- ENTONCES MUST crearse la tabla utf8mb4 sin modificar tablas Postgres Synap

---

### Requirement: Helper de Consulta Backward-Safe

El sistema MUST proveer `_query_enviado_tablero_componente(base_empresa, comp_ids)` leyendo **`mpr_envio_produccion`** en la BD indicada por `base_empresa`, sumando `cantidad` donde `anulado=0`. Si no hay filas, MUST retornar `{}`.

(Previously: consulta ORM `MprEnvioProduccion.objects` filtrado por `base_empresa`.)

#### Scenario: Con envíos registrados — suma correcta excluyendo anulados

- DADO comp_id=42 con 2 envíos activos (10 y 15) y 1 anulado (5) en MySQL
- CUANDO se llama el helper
- ENTONCES MUST retornar `{42: Decimal('25')}`

#### Scenario: Sin envíos — backward-safe

- DADO BD sin filas en `mpr_envio_produccion`
- CUANDO se llama el helper
- ENTONCES MUST retornar `{}`
- Y el tablero MUST funcionar sin error

---

## ADDED Requirements

### Requirement: Sin escritura Postgres tras cutover

Tras fase P3, MUST NOT crearse ni actualizarse filas en Postgres para envíos tablero.

#### Scenario: Cutover activo

- DADO cutover P3
- CUANDO se envía lote desde tablero
- ENTONCES MUST NOT existir INSERT en Postgres `mpr_mprenvio_produccion` o equivalente
