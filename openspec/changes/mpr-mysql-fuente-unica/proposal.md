# Propuesta — MPR fuente única en MySQL (AdministraNET)

**Cambio:** `mpr-mysql-fuente-unica`  
**Fecha:** 04/07/2026  
**Modo:** Evolution Mode (migración de persistencia; comportamiento funcional E7–E11 preservado)  
**Plan de referencia:** `docs/mpr/PLAN_MIGRACION_MPR_MYSQL_FUENTE_UNICA.md` (v1.1)

---

## 1. Intención

Unificar **toda la persistencia operativa MPR** (ledgers, turnos, config, armado surtido) en la **base MySQL de la empresa** (`base_empresa` como selector de conexión), eliminando la dualidad Postgres/MySQL introducida en E3–E11.

AdministraNET **no es multiempresa por BD**: una instalación = una base MySQL. Synap MUST NOT persistir `base_empresa` en tablas `mpr_*`.

---

## 2. Problema

| Hoy | Problema |
|-----|----------|
| Ledgers en Postgres (`MprEnvioProduccion`, `MprParte*`, …) | Backup, auditoría y futuros lectores VB6 requieren dos motores |
| `MprEmpresaConfig` + columna `base_empresa` | Anti-patrón vs modelo AdministraNET |
| Trazabilidad E8 sin `id_lista_produccion` | No hay registro MySQL unificado |

---

## 3. Alcance

### Incluido (P0–P3)

- DDL `mpr_*` en MySQL (`utf8mb4`, PK autonuméricas, FK entre cluster MPR y catálogos legacy).
- Proveedor catálogo `mpr_core_tables` + `docs/mpr/sql/001_mpr_core_tables.sql`.
- Repositorios `mpr/repositories/*` vía `get_connection(base_empresa)`.
- Migración datos Postgres → MySQL + ventana dual-write → cutover.
- Renombre config: `mpr_empresa_config` → **`mpr_config`** (singleton por BD).
- Deprecación escritura Postgres MPR operativa.

### Fase posterior (P4–P5, spec parcial)

- Tabla `mpr_evento` (trazabilidad unificada).
- Deprecación columnas/tables OPT (`lista_produccion_*` parcial).

### Fuera de alcance

- Cambio de fórmulas tablero, UX canon, wizard OPT (solo persistencia).
- Migración VB6.
- Índices PostgreSQL Synap no-MPR.

---

## 4. Capabilities (contrato para spec)

### New Capabilities

| Capability | Descripción |
|------------|-------------|
| `mpr-mysql-persistence` | Esquema `mpr_*`, tenancy, repositorios, migración, cutover, deprecación Postgres |

### Modified Capabilities

| Capability | Delta |
|------------|-------|
| `mpr-envio-produccion-tablero` | Ledger `mpr_envio_produccion` MySQL; sin Postgres |
| `mpr-opp-parte-produccion` | `mpr_parte*` MySQL; config `mpr_config`; scoping por conexión |
| `mpr-turnos-roster` | `mpr_turno` / `mpr_roster_dia` MySQL; sin `base_empresa` en tabla |
| `mpr-transiciones-lote` | `mpr_transicion_lote` MySQL |
| `mpr-armado-unificado` | Tablas armado surtido en MySQL |
| `mpr-imputacion-armado-1ra` | `mpr_imputacion_armado` MySQL |
| `mpr-trazabilidad-opt` | Lectura ledgers desde MySQL; ADDED `mpr_evento` (P4) |

---

## 5. Fases

| Fase | Entregable |
|------|------------|
| P0 | DDL + proveedor catalog |
| P1 | Repositorios + refactor services |
| P2 | `migrate_mpr_ledgers_to_mysql` |
| P3 | Cutover solo MySQL; tests verdes |
| P4 | `mpr_evento` + trazabilidad componente |
| P5 | Deprecación OPT/lista_produccion |

---

## 6. Rollback

- Flag feature dual-read Postgres durante W1–W2.
- Snapshot Postgres antes de cutover W3.
- DDL MySQL idempotente (no DROP en P0).

---

## 7. Criterios de éxito (P3)

1. Cero escrituras MPR operativas en Postgres (E7–E11).
2. Proveedor aplicado en bases productivas.
3. `docker exec Synap_app python manage.py test mpr --keepdb` verde.
4. Docs + specs actualizados.

---

*Propuesta lista para **spec** (esta entrega), **design** y **tasks**.*
