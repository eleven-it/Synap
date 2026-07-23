# Spec — Campaña de inventario físico

**Capability:** `stock-inventario-fisico-campana`
**Change:** `stock-inventario-fisico`
**Estado:** Propuesto

---

## Purpose

Gestionar el ciclo de vida de campañas de conteo físico mensual en depósitos MPR: snapshot de saldo sin congelar movimientos, asignación de contadores, líneas por artículo y transición de estados hasta Aplicado o Anulado. MUST NOT reemplazar ni confundirse con la consulta pivote `/stock/inventario/` (capability `stock-inventario-tabla`).

---

## Requirements

### Requirement: Separación funcional de consulta pivote

El módulo de inventario físico MUST operar bajo rutas `/stock/inventario-fisico/` y MUST NOT modificar el comportamiento de `/stock/inventario/`. La UI y el menú MUST distinguir explícitamente «Inventario físico / conteo» de «Consulta de inventario».

#### Scenario: Usuario accede a consulta pivote existente

- **GIVEN** un usuario con permiso de consulta de stock
- **WHEN** navega a `/stock/inventario/`
- **THEN** ve la tabla pivote MPR sin cambios y sin acceso a campañas de conteo físico

#### Scenario: Usuario accede a inventario físico

- **GIVEN** un supervisor con permiso `stock.inventario_fisico.gestionar`
- **WHEN** navega a `/stock/inventario-fisico/`
- **THEN** ve la gestión de campañas de conteo y no la consulta pivote

---

### Requirement: Depósitos MPR elegibles

Una campaña MUST limitarse a depósitos cuyo `tipo_mpr` sea **Terminado**, **SemiElaborado** o **2daSeleccion**. El sistema MUST NOT permitir crear campañas sobre otros tipos de depósito.

#### Scenario: Creación con depósito MPR válido

- **GIVEN** un depósito con `tipo_mpr=Terminado` y stock activo
- **WHEN** el supervisor crea una campaña seleccionando ese depósito
- **THEN** la campaña queda en estado Borrador con el depósito asociado

#### Scenario: Rechazo de depósito no MPR

- **GIVEN** un depósito con `tipo_mpr` distinto de Terminado, SemiElaborado o 2daSeleccion
- **WHEN** el supervisor intenta crear una campaña sobre ese depósito
- **THEN** el sistema rechaza la operación e informa que el depósito no es elegible

---

### Requirement: Snapshot de saldo sin freeze

Al iniciar el conteo de una campaña, el sistema MUST capturar `saldo_snapshot` por línea desde `stock_deposito.saldo` en el momento de apertura. El snapshot MUST NOT congelar ni bloquear movimientos de stock; los movimientos posteriores MUST seguir registrándose con normalidad.

#### Scenario: Snapshot al abrir conteo

- **GIVEN** una campaña en Borrador con depósito y artículos elegibles
- **WHEN** el supervisor la pasa a estado En conteo
- **THEN** se generan líneas con `saldo_snapshot` por artículo y la campaña queda abierta para conteo

#### Scenario: Movimientos permitidos durante conteo

- **GIVEN** una campaña En conteo con snapshot ya capturado
- **WHEN** ocurre un movimiento de stock en el mismo depósito
- **THEN** el movimiento se aplica a `stock_deposito` y el `saldo_snapshot` de la línea MUST NOT cambiar

---

### Requirement: Ciclo de estados hasta Aplicado o Anulado

Una campaña MUST transitar por estados controlados: Borrador → En conteo → (Cerrado a revisión) → Aplicado **o** Anulado. El sistema MUST NOT aplicar ajustes MSTOCK ni marcar Aplicado sin pasar por autorización (ver capability `stock-inventario-fisico-ajuste`).

#### Scenario: Flujo feliz hasta cierre a revisión

- **GIVEN** una campaña En conteo con al menos un conteo registrado
- **WHEN** el supervisor cierra el conteo
- **THEN** la campaña pasa a estado Cerrado a revisión y queda disponible para analizador de diferencias

#### Scenario: Anulación en Borrador o En conteo

- **GIVEN** una campaña en Borrador o En conteo sin ajustes aplicados
- **WHEN** un admin stock anula la campaña
- **THEN** la campaña queda Anulada y MUST NOT generar movimientos MSTOCK

#### Scenario: Aplicado solo tras autorización

- **GIVEN** una campaña Cerrado a revisión con diferencias autorizadas
- **WHEN** se confirma la aplicación
- **THEN** la campaña pasa a Aplicado y se registran los ajustes MSTOCK auditados

---

### Requirement: Asignación de contadores

El supervisor MUST poder asignar uno o más operarios (contadores) a una campaña En conteo. Un operario MUST NOT contar en campañas a las que no está asignado.

#### Scenario: Operario asignado puede contar

- **GIVEN** una campaña En conteo con el operario A asignado
- **WHEN** el operario A abre `/stock/conteo/` para esa campaña
- **THEN** puede registrar conteos ciegos de artículos de la campaña

#### Scenario: Operario no asignado bloqueado

- **GIVEN** una campaña En conteo sin el operario B en la asignación
- **WHEN** el operario B intenta registrar un conteo
- **THEN** el sistema rechaza la operación por falta de asignación

---

### Requirement: Permisos por rol

| Permiso | Operario | Supervisor | Admin stock |
|---------|----------|------------|-------------|
| `stock.inventario_fisico.contar` | ✓ | ✓ | ✓ |
| `stock.inventario_fisico.gestionar` | — | ✓ | ✓ |
| `stock.inventario_fisico.autorizar` | — | ✓ | ✓ |

El sistema MUST NOT exponer acciones de gestión, analizador ni autorización a usuarios sin el permiso correspondiente.

#### Scenario: Operario sin permiso de gestión

- **GIVEN** un operario con solo `stock.inventario_fisico.contar`
- **WHEN** intenta crear o cerrar una campaña
- **THEN** el sistema deniega el acceso

---

### Requirement: Líneas de campaña y agregación de conteos

Cada línea de campaña MUST vincular un artículo del depósito con su `saldo_snapshot`. Los conteos de operarios MUST agregarse por artículo; la cantidad contada consolidada MUST ser visible solo para roles con permiso de gestión o autorización, nunca para el contador en UI/API de conteo.

#### Scenario: Múltiples contadores en el mismo artículo

- **GIVEN** dos operarios asignados que cuentan el mismo artículo con cantidades distintas
- **WHEN** el supervisor consulta el monitor de campaña
- **THEN** ve los conteos por operario y la consolidación interna sin exponer `saldo_snapshot` al operario
