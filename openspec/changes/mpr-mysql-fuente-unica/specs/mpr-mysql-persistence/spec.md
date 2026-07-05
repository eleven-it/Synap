# mpr-mysql-persistence Specification

## Purpose

Define la persistencia operativa MPR en **MySQL AdministraNET** (una BD = una empresa): esquema `mpr_*`, reglas de tenancy, despliegue DDL, acceso por repositorios, migración desde Postgres y deprecación de ledgers Django en `default`.

Referencia: `docs/mpr/PLAN_MIGRACION_MPR_MYSQL_FUENTE_UNICA.md`.

---

## Requirements

### Requirement: Tenancy — Sin base_empresa en tablas mpr_*

Ninguna tabla `mpr_*` MUST incluir columna `base_empresa`. La empresa MUST quedar implícita en la base MySQL conectada. Synap MUST usar `base_empresa` únicamente como argumento de `get_connection` / `mysql_cursor`.

#### Scenario: Tabla creada sin columna empresa

- DADO el proveedor DDL aplicado en `administranet92`
- CUANDO se inspecciona `mpr_envio_produccion`
- ENTONCES MUST NOT existir columna `base_empresa`

#### Scenario: Repositorio scoped por conexión

- DADO sesión Synap con `base_empresa='administranet92'`
- CUANDO el repositorio inserta en `mpr_parte`
- ENTONCES la fila MUST persistir solo en la BD `administranet92`
- Y MUST NOT requerir filtro SQL por `base_empresa`

---

### Requirement: Esquema mpr_* — Nomenclatura, PK y charset

Todas las tablas operativas MPR MUST:

- Usar prefijo `snake_case` `mpr_` (ej. `mpr_envio_produccion`).
- Tener PK `BIGINT AUTO_INCREMENT` (`id_mpr_<entidad>`).
- Usar `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`.
- Declarar FK físicas entre tablas `mpr_*` y hacia catálogos legacy cuando el engine lo permita.

Códigos de negocio (`codigo_movimiento`, etc.) MUST ser columnas adicionales, no PK.

#### Scenario: Charset utf8mb4 en tablas nuevas

- DADO DDL aplicado
- CUANDO se consulta `information_schema.TABLES` para `mpr_turno`
- ENTONCES `TABLE_COLLATION` MUST ser `utf8mb4_unicode_ci`

---

### Requirement: Catálogo tablas core — Despliegue idempotente

El sistema MUST registrar proveedor `mpr_core_tables` en `core/services/legacy_mysql_schema/catalog.py` que ejecute `docs/mpr/sql/001_mpr_core_tables.sql` de forma idempotente (`CREATE TABLE IF NOT EXISTS`).

Tablas P0 MUST incluir como mínimo: `mpr_config`, `mpr_turno`, `mpr_roster_dia`, `mpr_envio_produccion`, `mpr_parte`, `mpr_parte_linea`, `mpr_parte_ajuste`, `mpr_transicion_lote`, `mpr_articulo_armado_surtido`, `mpr_armado_lote`, `mpr_armado_surtido_movimiento`, `mpr_armado_surtido_linea`, `mpr_imputacion_armado`.

#### Scenario: Segunda ejecución no falla

- DADO proveedor ya aplicado
- CUANDO supervisor ejecuta de nuevo «MPR — tablas core Synap»
- ENTONCES MUST completarse sin error
- Y MUST NOT duplicar tablas ni filas seed de `mpr_config`

---

### Requirement: Configuración MPR — Tabla mpr_config singleton

El sistema MUST persistir configuración MPR en `mpr_config` (no `mpr_empresa_config`). MUST existir como máximo una fila operativa por BD. Campo inicial MUST incluir `bloquear_parte_supera_fabricando` (default activo).

#### Scenario: Seed config en BD vacía

- DADO BD sin filas en `mpr_config`
- CUANDO se aplica proveedor DDL
- ENTONCES MUST existir una fila con `bloquear_parte_supera_fabricando=1`

---

### Requirement: Acceso — Repositorios MySQL, no ORM Postgres

Lecturas y escrituras operativas MPR MUST usar repositorios bajo `mpr/repositories/` con SQL parametrizado y `core.utils.administranet_types`. MUST NOT usar `Mpr*.objects` en Postgres para flujos E7–E11 tras cutover P3.

#### Scenario: Envío tablero escribe MySQL

- DADO cutover P3 activo
- CUANDO `enviar_a_produccion_lote` registra un envío
- ENTONCES MUST existir fila en `mpr_envio_produccion` de la BD conectada
- Y MUST NOT crearse fila en Postgres `default`

---

### Requirement: Migración Postgres → MySQL

El sistema MUST proveer comando `migrate_mpr_ledgers_to_mysql` con `--dry-run` y `--empresa=<base_empresa>` que copie datos en orden de FK y valide conteos. MUST preservar `uuid_parte` / `uuid_ajuste` / `uuid_lote` donde existían en Postgres.

#### Scenario: Paridad de conteos post-migración

- DADO 10 filas `MprEnvioProduccion` en Postgres para empresa E
- CUANDO se ejecuta migración para E
- ENTONCES `COUNT(*)` en `mpr_envio_produccion` de BD E MUST ser 10

---

### Requirement: Cutover — Dual-write y apagado Postgres

Entre P2 y P3 el sistema SHOULD soportar dual-write (MySQL + Postgres) configurable. Tras P3 MUST NOT escribir ledgers MPR en Postgres. Tablas Postgres MPR operativas MUST eliminarse en migración Django de limpieza posterior.

#### Scenario: Post-cutover sin escritura Postgres

- DADO feature cutover P3 activo
- CUANDO se registra un parte de producción
- ENTONCES MUST persistir en `mpr_parte` MySQL
- Y MUST NOT insertar en tabla Postgres `mpr_parte`

---

## REMOVED (Postgres)

Tras cutover, MUST eliminarse persistencia operativa en Postgres: `mpr_envio_produccion`, `mpr_parte*`, `mpr_transicion_lote`, `mpr_turno`, `mpr_roster_dia`, tablas armado surtido, `mpr_imputacion_armado`, `mpr_empresa_config`, `mpr_opt`, `mpr_opt_linea`.

(Razón: fuente única MySQL AdministraNET.)
