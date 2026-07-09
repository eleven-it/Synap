# Spec — Catálogo de máquinas y líneas

**Capability:** `mpr-catalogo-maquina-linea`
**Change:** `mpr-trazabilidad-maquina-linea-operario`
**Estado:** Propuesto

> Nombres de tablas nuevas con separador `_` (snake_case), estándar AdministraNET.

---

## ADDED Requirements

### Requirement: Modelo de línea de producción

El sistema MUST proveer una tabla `mpr_linea` con, al menos: identificador, `base_empresa`, `nombre`, `activo`. El `nombre` MUST ser único por empresa.

#### Scenario: Crear línea

- **GIVEN** un supervisor con `base_empresa="Empresa1"`
- **WHEN** crea una línea con `nombre="Línea 1"`
- **THEN** la línea se guarda con `activo=true` y es visible en el listado de "Empresa1"

#### Scenario: Rechazar nombre duplicado

- **GIVEN** una línea `"Línea 1"` en `"Empresa1"`
- **WHEN** se intenta crear otra `"Línea 1"` en la misma empresa
- **THEN** el sistema rechaza con mensaje en español y no duplica

---

### Requirement: Modelo de máquina

El sistema MUST proveer una tabla `mpr_maquina` con, al menos: identificador, `base_empresa`, `codigo`/`nombre`, `activo`. El identificador visible (código) MUST ser único por empresa.

#### Scenario: Alta de máquina

- **WHEN** el supervisor crea la máquina `"M-001"`
- **THEN** queda `activo=true` y disponible para asignar a una línea

#### Scenario: Baja lógica

- **WHEN** el supervisor inactiva una máquina
- **THEN** deja de ofrecerse para nuevas asignaciones pero su histórico se conserva

---

### Requirement: Pertenencia máquina→línea versionada

El sistema MUST registrar la pertenencia de cada máquina a una línea en `mpr_maquina_linea` con `vigencia_desde` y `vigencia_hasta` (NULL = vigente). Una máquina MUST tener a lo sumo **una** pertenencia vigente a la vez.

#### Scenario: Asignar máquina a línea

- **WHEN** el supervisor asigna la máquina `M-001` a la `Línea 1` con `vigencia_desde=hoy`
- **THEN** se crea una fila vigente (`vigencia_hasta=NULL`)

#### Scenario: Reasignar cierra vigencia previa

- **GIVEN** `M-001` vigente en `Línea 1`
- **WHEN** el supervisor la reasigna a `Línea 2`
- **THEN** la fila de `Línea 1` recibe `vigencia_hasta` (fecha de corte) y se crea una fila vigente para `Línea 2`
- **AND** no quedan dos pertenencias vigentes simultáneas para `M-001`

#### Scenario: Consultar histórico

- **WHEN** se consulta la máquina `M-001`
- **THEN** el sistema lista todos sus períodos de pertenencia (línea + rango de fechas)

---

### Requirement: Persistencia vía catálogo central

Las tablas `mpr_linea`, `mpr_maquina` y `mpr_maquina_linea` MUST crearse mediante `core/services/legacy_mysql_schema/catalog.py` (proveedor registrado) con DDL en `mpr/sql/`, ejecutable por la herramienta global de migración legacy.

#### Scenario: Idempotencia

- **WHEN** la migración se ejecuta dos veces
- **THEN** no falla ni duplica tablas/columnas

---

### Requirement: Acceso restringido a supervisor

La gestión de catálogos (alta/baja/edición de líneas, máquinas y pertenencia) MUST estar restringida a usuarios con rol Supervisor MPR o administrador.

#### Scenario: Operario sin acceso

- **WHEN** un operario intenta abrir la gestión de máquinas/líneas
- **THEN** el sistema deniega el acceso
