# Spec (delta) — Roster con override de línea

**Capability:** `mpr-turnos-roster` (existente)
**Change:** `mpr-trazabilidad-maquina-linea-operario`
**Estado:** Propuesto (delta)

---

## MODIFIED Requirements

### Requirement: Override de línea por día en el roster

La tabla `mpr_roster_dia` SHALL incluir una columna `id_linea` (INT NULL) que permite **sobrescribir** la línea habitual del operario (`mpr_operario_linea`) para esa fecha/turno. `NULL` significa "usar la línea habitual".

La unicidad `(base_empresa, fecha, id_operario)` SHALL mantenerse; el override no crea filas nuevas, solo agrega el dato a la asignación del día.

#### Scenario: Asignación con override

- **GIVEN** operario con línea habitual `Línea 1`
- **WHEN** el supervisor asigna en el roster de hoy turno Noche con `id_linea = Línea 3`
- **THEN** la resolución de línea del operario para hoy/Noche devuelve `Línea 3`

#### Scenario: Asignación sin override

- **WHEN** el supervisor asigna solo turno (sin `id_linea`)
- **THEN** `id_linea=NULL` y la resolución usa la línea habitual del operario

#### Scenario: Compatibilidad con roster existente

- **GIVEN** filas de roster anteriores al cambio (sin `id_linea`)
- **THEN** se interpretan como `id_linea=NULL` (usar habitual), sin romper la planificación

---

### Requirement: Persistencia del override vía catálogo central

La columna `id_linea` en `mpr_roster_dia` SHALL agregarse mediante `core/services/legacy_mysql_schema/catalog.py` con DDL en `mpr/sql/`, de forma idempotente.

#### Scenario: Idempotencia

- **WHEN** se ejecuta dos veces el ALTER
- **THEN** no falla ni duplica la columna
