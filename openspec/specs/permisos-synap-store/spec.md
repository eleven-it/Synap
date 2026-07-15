# permisos-synap-store Specification

## Purpose

Persistencia y resolución runtime de permisos Synap en tablas propias `synap_*` por empresa MySQL, desacoplada de `permiso_sistema` / `permiso_sistema_puesto` compartidas con VB6. Conserva lecturas complementarias legacy (`permisos`, `permisos_sistema`) sin migrarlas.

Referencias: `docs/general/APPS_CORE_Y_PERMISOS_ADMINISTRANET.md`, `SYNC_PERMISOS_SYNAP.md`.

---

## Requirements

### Requirement: Esquema synap_* — Tablas y relaciones

El sistema MUST crear y mantener en cada BD empresa las tablas:

| Tabla | Propósito |
|-------|-----------|
| `synap_permiso` | Catálogo (`key_permiso` único, módulo, nombre, activo) |
| `synap_rol` | Roles Synap (nombre, es_sistema, activo) |
| `synap_rol_permiso` | M2M rol ↔ permiso |
| `synap_puesto_rol` | Mapeo `idpuesto` (valor) → `synap_rol` |

Las FK MUST existir solo entre tablas `synap_*`. MUST NOT declarar FK hacia `puestos`, `permiso_sistema` ni `permiso_sistema_puesto`.

#### Scenario: Tablas creadas sin FK a VB6

- DADO el proveedor DDL aplicado en una BD empresa
- CUANDO se inspecciona `information_schema.KEY_COLUMN_USAGE` para `synap_puesto_rol`
- ENTONCES MUST NOT existir FK referenciando tablas legacy VB6
- Y MUST existir FK hacia `synap_rol`

---

### Requirement: Despliegue DDL idempotente vía catálogo central

El sistema MUST registrar proveedor en `core/services/legacy_mysql_schema/catalog.py` que ejecute DDL idempotente (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`). MUST NOT usar `DROP TABLE` ni `DROP COLUMN`. La segunda ejecución MUST completarse sin error ni duplicar estructura.

#### Scenario: Re-ejecución del proveedor sin fallo

- DADO el proveedor `synap_*` ya aplicado en la BD
- CUANDO supervisor o bootstrap ejecuta de nuevo el proveedor
- ENTONCES MUST completarse sin error
- Y MUST NOT alterar datos existentes en `synap_permiso` ni `synap_rol`

---

### Requirement: Seed del catálogo desde PERMISOS_POR_MODULO

El sistema MUST poblar `synap_permiso` desde `core/constantes_permisos.py::PERMISOS_POR_MODULO`, incluyendo comodines `modulo.*`. El seed MUST ser idempotente: re-ejecutarlo MUST NOT duplicar filas por `key_permiso` ni sobrescribir asignaciones en `synap_rol_permiso` / `synap_puesto_rol`.

#### Scenario: Seed en BD vacía

- DADO BD sin filas en `synap_permiso`
- CUANDO se ejecuta el seed
- ENTONCES MUST existir una fila por cada `key_permiso` definido en `PERMISOS_POR_MODULO`
- Y MUST existir comodines `ventas.*`, `reports.*`, etc. según constantes

#### Scenario: Segunda ejecución del seed

- DADO seed ya aplicado con asignaciones rol↔permiso existentes
- CUANDO se re-ejecuta el seed
- ENTONCES el conteo de filas en `synap_permiso` MUST permanecer estable
- Y MUST NOT modificarse filas en `synap_rol_permiso`

---

### Requirement: Backfill idempotente desde legacy grupo Synap

El sistema MUST migrar asignaciones existentes desde `permiso_sistema` (grupo `'Synap'`) y `permiso_sistema_puesto` hacia `synap_rol` / `synap_rol_permiso` / `synap_puesto_rol`. El backfill MUST ser idempotente y MUST NOT escribir en tablas legacy.

#### Scenario: Backfill preserva permisos activos por puesto

- DADO puesto con `valor_permiso='Si'` en `permiso_sistema_puesto` para keys del grupo Synap
- CUANDO se ejecuta backfill
- ENTONCES los `key_permiso` equivalentes MUST quedar activos vía cadena `synap_puesto_rol → synap_rol_permiso → synap_permiso`
- Y MUST NOT insertarse filas en `permiso_sistema` ni `permiso_sistema_puesto`

#### Scenario: Re-ejecución del backfill

- DADO backfill ya completado
- CUANDO se ejecuta de nuevo
- ENTONCES MUST NOT duplicar filas en `synap_puesto_rol` ni `synap_rol_permiso`

---

### Requirement: Fuente de verdad runtime y feature flag

`get_permisos_totales_administranet` MUST resolver permisos Synap según `SYNAP_PERMISOS_SOURCE`:

| Valor | Comportamiento |
|-------|----------------|
| `legacy` | Lectura actual (`permiso_sistema` + `permiso_sistema_puesto`) |
| `synap` | Lectura `synap_puesto_rol → synap_rol_permiso → synap_permiso` |

Con `synap`, si faltan tablas, filas o mapeo para un puesto, el sistema MUST aplicar dual-read con fallback a legacy para ese cálculo. El valor por defecto SHOULD ser `legacy` hasta cutover P2.

#### Scenario: Flag legacy mantiene comportamiento actual

- DADO `SYNAP_PERMISOS_SOURCE=legacy` y datos en tablas legacy
- CUANDO se calculan permisos de un usuario no supervisor
- ENTONCES el resultado MUST coincidir con el comportamiento pre-migración

#### Scenario: Flag synap con fallback por dato faltante

- DADO `SYNAP_PERMISOS_SOURCE=synap` y puesto sin fila en `synap_puesto_rol`
- CUANDO se calculan permisos del puesto
- ENTONCES MUST usarse asignaciones legacy de `permiso_sistema_puesto` como fallback
- Y MUST registrarse advertencia diagnóstica

#### Scenario: Flag synap con datos completos

- DADO `SYNAP_PERMISOS_SOURCE=synap` y backfill completo para el puesto
- CUANDO se calculan permisos
- ENTONCES MUST leerse exclusivamente tablas `synap_*` para permisos Synap
- Y MUST NOT consultarse `permiso_sistema_puesto` para keys del grupo Synap

---

### Requirement: Paridad de permisos efectivos post-migración

Tras seed + backfill, el cálculo de permisos efectivos MUST producir el mismo resultado que hoy para cada combinación usuario/puesto, incluyendo:

- Usuario con `cod_usuario='supervisor'` ⇒ set `{"*"}` (acceso total).
- Comodines por módulo (`modulo.*`) que expanden verificación de permisos individuales.
- Permisos individuales (`ventas.ver`, `reports.dashboard`, etc.).

#### Scenario: Supervisor acceso total

- DADO usuario con `cod_usuario='supervisor'`
- CUANDO se invoca `get_permisos_totales_administranet`
- ENTONCES el resultado MUST ser exactamente `{"*"}`

#### Scenario: Comodín de módulo

- DADO puesto con `reports.*` activo (vía legacy o `synap_*` según flag)
- CUANDO se verifica permiso `reports.dashboard`
- ENTONCES `tiene_permiso_administranet` MUST retornar verdadero

#### Scenario: Permiso individual sin comodín

- DADO puesto con solo `ventas.ver` activo
- CUANDO se verifica `ventas.editar`
- ENTONCES MUST retornar falso
- Y `ventas.ver` MUST retornar verdadero

---

### Requirement: Lecturas legacy complementarias conservadas

El sistema MUST seguir leyendo, sin migrar ni escribir:

- Tabla `permisos` (Clavemenu VB6) con mapeo `MAPEO_MENU_A_PERMISO`.
- Tabla `permisos_sistema` (reglas anchas TPV: límites descuento, etc.).

Estas lecturas MUST aplicarse en el cálculo de permisos efectivos independientemente del valor de `SYNAP_PERMISOS_SOURCE`.

#### Scenario: Clavemenu otorga permiso Synap

- DADO puesto con `keyCompStock` activo en `permisos` y sin `stock.crear_movimiento` en `synap_*`
- CUANDO se calculan permisos
- ENTONCES el set MUST incluir `stock.crear_movimiento`

#### Scenario: permisos_sistema no se escribe desde Synap

- DADO operación de guardado en `/core/permisos-puesto/`
- CUANDO se persisten cambios de permisos Synap
- ENTONCES MUST NOT modificarse filas en `permisos_sistema`

---

### Requirement: Prohibición de escritura en tablas VB6 compartidas

Synap MUST NOT insertar, actualizar ni eliminar filas en `permiso_sistema`, `permiso_sistema_puesto` ni `puestos` tras cutover P2. `sync_permisos_synap` MUST quedar deshabilitado/retirado en P3.

#### Scenario: Login sin inyección legacy

- DADO cutover P2 activo y `SYNAP_PERMISOS_SOURCE=synap`
- CUANDO un usuario inicia sesión
- ENTONCES MUST NOT ejecutarse INSERT/UPDATE en `permiso_sistema`
- Y MUST NOT ejecutarse INSERT/UPDATE en `permiso_sistema_puesto`

---

### Requirement: Operaciones UI escriben solo en synap_*

Las operaciones de crear/editar roles, asignar permisos a roles y asignar roles a puestos desde `/core/permisos-puesto/` MUST persistir exclusivamente en tablas `synap_*`.

#### Scenario: Toggle permiso Synap en UI

- DADO supervisor en `/core/permisos-puesto/<id>/toggle-synap/`
- CUANDO activa un `key_permiso` para el puesto
- ENTONCES MUST crearse o actualizarse fila en `synap_rol_permiso` (vía rol del puesto)
- Y MUST NOT modificarse `permiso_sistema_puesto`

#### Scenario: Atajo módulo en UI

- DADO supervisor que activa atajo `+ Ventas` en pestaña Permisos Synap
- CUANDO confirma la acción
- ENTONCES MUST activarse en `synap_*` todos los `key_permiso` del módulo y `ventas.*`
- Y MUST NOT escribirse en tablas legacy Synap
