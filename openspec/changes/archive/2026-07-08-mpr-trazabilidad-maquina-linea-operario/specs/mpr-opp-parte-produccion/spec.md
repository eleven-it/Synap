# Spec (delta) — Parte de producción: estado, máquina y gap

**Capability:** `mpr-opp-parte-produccion` (existente)
**Change:** `mpr-trazabilidad-maquina-linea-operario`
**Estado:** Propuesto (delta)

> Modifica el capability archivado `mpr-opp-parte-produccion` para soportar el flujo de dos etapas y la dimensión máquina.

---

## MODIFIED Requirements

### Requirement: Cabecera de parte con estado y origen

La tabla `mpr_parte` SHALL incluir:
- `estado` (VARCHAR): `borrador` | `pendiente` | `aprobado`.
- `origen` (VARCHAR): `movil_operario` | `directo_supervisor`.
- `id_usuario_supervisor` (INT NULL) y `aprobado_en` (DATETIME NULL): auditoría de aprobación.

El asiento físico a depósito "Producción" SHALL ejecutarse **solo** cuando el parte alcanza `estado=aprobado` (móvil) o al crear un parte directo del supervisor (`origen=directo_supervisor`, nace aprobado). Los partes `borrador`/`pendiente` MUST NOT mover stock.

#### Scenario: Parte pendiente no mueve stock

- **WHEN** se guarda un parte con `estado=pendiente`
- **THEN** `movimiento_fisico_ok=false` y `stock_deposito` de Producción no cambia

#### Scenario: Compatibilidad de partes históricos

- **GIVEN** partes anteriores al cambio sin `estado`
- **THEN** el sistema los trata como `aprobado`/`directo_supervisor` (backfill por defecto) sin romper reportes

---

### Requirement: Línea de parte con máquina y gap

La tabla `mpr_parte_linea` SHALL incluir:
- `id_maquina` (INT NULL) + `maquina_nombre` (VARCHAR) snapshot.
- `cantidad_declarada` (DECIMAL): lo cargado por el operario.
- `cantidad_aprobada` (DECIMAL NULL): lo aprobado por el supervisor.
- `gap` (DECIMAL): `cantidad_aprobada − cantidad_declarada`.
- `motivo` (VARCHAR NULL): requerido si `gap != 0`.

Para partes directos del supervisor, `cantidad_declarada = cantidad_aprobada` y `gap=0`. La columna `cantidad` histórica SHALL mantenerse compatible (equivalente a `cantidad_aprobada`).

#### Scenario: Línea de operario con corrección

- **WHEN** el operario declara 41 y el supervisor aprueba 39
- **THEN** la línea guarda `cantidad_declarada=41`, `cantidad_aprobada=39`, `gap=-2`, `motivo` presente

#### Scenario: Migración idempotente vía catálogo

- **WHEN** se ejecuta dos veces el ALTER de columnas en `core/services/legacy_mysql_schema/catalog.py`
- **THEN** no falla ni duplica columnas
