# Delta for permisos-synap-store

## ADDED Requirements

### Requirement: Permiso finance.credito.aprobar

El catálogo `PERMISOS_POR_MODULO` MUST incluir `finance.credito.aprobar` (módulo finanzas/crédito) con seed idempotente en `synap_permiso`. El permiso MUST autorizar aprobar o rechazar PED en cola Finanzas. MUST NOT reutilizar `ecom.pedidos.aprobar` para acciones de crédito.

#### Scenario: Seed incluye permiso crédito

- **GIVEN** BD empresa con seed Synap aplicado
- **WHEN** se consulta `synap_permiso` por `key_permiso='finance.credito.aprobar'`
- **THEN** MUST existir fila activa con nombre en español
- **AND** re-ejecutar seed MUST NOT duplicar la fila

#### Scenario: Verificación runtime

- **GIVEN** puesto con `finance.credito.aprobar` activo vía `synap_*`
- **WHEN** se invoca `tiene_permiso_administranet` para aprobar crédito
- **THEN** MUST retornar verdadero
- **AND** `ecom.pedidos.aprobar` solo MUST NOT otorgar aprobación Finanzas

#### Scenario: Sin permiso crédito

- **GIVEN** puesto con `ecom.pedidos.aprobar` pero sin `finance.credito.aprobar`
- **WHEN** intenta aprobar PED en cola Finanzas
- **THEN** MUST retornar falso para acción de crédito

### Requirement: Permiso finance.credito.configurar

El catálogo MUST incluir `finance.credito.configurar` con seed idempotente. MUST autorizar ABM de políticas de crédito y plantillas de aviso. MUST NOT ser requerido para aprobar/rechazar en cola Finanzas. `finance.credito.aprobar` MUST NOT por sí solo autorizar el ABM.

#### Scenario: Seed incluye configurar

- **GIVEN** BD empresa con seed Synap aplicado
- **WHEN** se consulta `key_permiso='finance.credito.configurar'`
- **THEN** MUST existir fila activa con nombre en español

#### Scenario: Segregación aprobar vs configurar

- **GIVEN** puesto solo con `finance.credito.aprobar`
- **WHEN** intenta guardar política o plantilla de crédito
- **THEN** MUST denegarse
- **AND** MUST poder operar la cola Finanzas
