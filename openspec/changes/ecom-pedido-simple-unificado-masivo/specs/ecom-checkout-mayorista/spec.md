# Delta for ecom-checkout-mayorista

**Change:** `ecom-pedido-simple-unificado-masivo`  
**Base:** `openspec/specs/ecom-checkout-mayorista/spec.md`

## ADDED Requirements

### REQ-CHK-013 — EcomCart efímero; borrador de trabajo en draft masivo

`EcomCart` MUST usarse **solo** como carrito efímero creado en runtime durante la confirmación batch masiva (`batch_checkout_masivo`) o flujos técnicos equivalentes. MUST NOT ser el workspace persistente de pedido simple. El borrador de captura para pedido simple y masivo MUST ser `EcomPedidoMasivoDraft` en Postgres hasta confirmar.

#### Scenario: Confirmación masiva crea carritos efímeros

- **GIVEN** draft masivo con celdas en 2 sucursales
- **WHEN** confirma el lote
- **THEN** MAY instanciar `EcomCart` temporales por sucursal para invocar `confirmar()`
- **AND** MUST NOT depender de un `EcomCart` borrador preexistente del usuario

#### Scenario: Pedido simple confirma vía checkout mayorista

- **GIVEN** draft simple con 1 columna y cantidades > 0
- **WHEN** confirma
- **THEN** MUST invocar `mayorista_checkout_service.confirmar` (directo o vía batch 1 sucursal)
- **AND** MUST aplicar REQ-CHK-001–012 y REQ-CHK-MAS-01/02 según corresponda

#### Scenario: Borrador simple no escribe MySQL

- **GIVEN** draft simple con celdas editadas sin confirmar
- **WHEN** autoguarda
- **THEN** MUST persistir solo en Postgres draft/celdas
- **AND** MUST NOT escribir en `comp_ped`/`stockp`

---

### REQ-CHK-014 — Edición PED simple: anula origen antes de alta

Cuando el draft simple tiene `cod_mov_origen`, la confirmación MUST anular el PED origen dentro de la política transaccional existente **antes** o **como parte** del flujo anula+crea, alineado con REQ-PSU-06. MUST validar que el origen sigue Pendiente no anulado al confirmar.

#### Scenario: Origen válido

- **GIVEN** draft con `cod_mov_origen` pendiente
- **WHEN** confirma edición
- **THEN** MUST anular origen y crear nuevo PED
- **AND** MUST NOT dejar dos PED activos equivalentes

#### Scenario: Origen ya anulado

- **GIVEN** `cod_mov_origen` anulado externamente
- **WHEN** intenta confirmar
- **THEN** MUST hacer ROLLBACK o abortar sin alta parcial
- **AND** MUST devolver error en español
