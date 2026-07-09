# Spec — Asignación máquina→artículo (habilitación versionada)

**Capability:** `mpr-asignacion-maquina-articulo`
**Change:** `mpr-trazabilidad-maquina-linea-operario`
**Estado:** Propuesto

---

## ADDED Requirements

### Requirement: Habilitación máquina→artículo versionada

El sistema MUST permitir habilitar en cada máquina **uno o varios artículos** que puede fabricar, registrados en `mpr_maquina_articulo` con `vigencia_desde` y `vigencia_hasta` (NULL = vigente). Varios artículos MAY estar vigentes simultáneamente en una misma máquina.

#### Scenario: Habilitar varios artículos

- **GIVEN** la máquina `M-001`
- **WHEN** el supervisor habilita los artículos `A` y `B` con `vigencia_desde=hoy`
- **THEN** ambos quedan vigentes para `M-001`

#### Scenario: Deshabilitar un artículo

- **GIVEN** `A` y `B` vigentes en `M-001`
- **WHEN** el supervisor deshabilita `A`
- **THEN** la fila de `A` recibe `vigencia_hasta` (fecha de corte) y `B` sigue vigente

---

### Requirement: Histórico de seteo consultable

El sistema MUST conservar el histórico de todos los períodos en que cada artículo estuvo habilitado en cada máquina, para trazabilidad.

#### Scenario: Consultar seteos históricos

- **WHEN** se consulta la máquina `M-001` por un rango de fechas
- **THEN** el sistema devuelve los artículos que estuvieron habilitados y entre qué fechas

#### Scenario: Trazabilidad de un parte pasado

- **GIVEN** un parte de producción de una fecha pasada para `M-001`
- **WHEN** se audita ese parte
- **THEN** se puede determinar qué artículos estaban habilitados en `M-001` en esa fecha

---

### Requirement: Habilitación a nivel máquina (independiente del turno)

La habilitación máquina→artículo MUST ser a nivel máquina y MUST NOT depender del turno. El turno solo actúa como contexto del operario al cargar producción.

#### Scenario: Mismos artículos en todos los turnos

- **GIVEN** `A` habilitado en `M-001`
- **WHEN** un operario del turno Mañana y otro del turno Noche cargan producción de `M-001`
- **THEN** ambos ven `A` disponible

---

### Requirement: El artículo debe estar habilitado para poder cargarse

Al construir la grilla de carga (móvil) o el parte, el sistema MUST ofrecer únicamente artículos con habilitación **vigente** en la máquina a la fecha de producción.

#### Scenario: Artículo no habilitado

- **GIVEN** el artículo `C` no habilitado en `M-001`
- **WHEN** el operario abre la carga de `M-001`
- **THEN** `C` no aparece como opción cargable

---

### Requirement: Persistencia vía catálogo central

La tabla `mpr_maquina_articulo` MUST crearse mediante `core/services/legacy_mysql_schema/catalog.py` con DDL en `mpr/sql/`, de forma idempotente.

#### Scenario: Idempotencia

- **WHEN** la migración se ejecuta dos veces
- **THEN** no falla ni duplica la tabla
