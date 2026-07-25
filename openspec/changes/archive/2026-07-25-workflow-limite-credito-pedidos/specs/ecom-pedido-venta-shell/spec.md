# Delta for ecom-pedido-venta-shell

## ADDED Requirements

### REQ-VTA-10 — Semáforo de crédito en toma de pedido

Cuando `ecom_credito_pedidos_activa` ON, el header de captura (`pedidos_order_header.html`) MUST mostrar semáforo rojo/amarillo/verde con: exposición actual, límite monetario (si aplica), días de mora vs límite, monto disponible y total del carrito. MUST actualizarse al seleccionar cliente y al modificar totales del carrito. MUST NOT reutilizar solo widget legacy de saldo CC + días sin monto disponible.

#### Scenario: Semáforo verde pre-confirmación

- **GIVEN** cliente con cupo disponible y sin mora excedida
- **WHEN** el vendedor agrega ítems dentro del disponible
- **THEN** MUST mostrarse semáforo verde con monto disponible positivo

#### Scenario: Semáforo rojo por exceso

- **GIVEN** total carrito supera monto disponible según política
- **WHEN** se renderiza header antes de confirmar
- **THEN** MUST mostrarse semáforo rojo con motivo visible (monto y/o días)
- **AND** MUST permitir confirmar igual (alta no bloqueada)

#### Scenario: Credito=0 sin tope $

- **GIVEN** cliente con `Credito=0`
- **WHEN** se muestra semáforo
- **THEN** MUST indicar ausencia de tope monetario
- **AND** MUST evaluar y mostrar mora en días según política

---

### REQ-VTA-11 — Pre-evaluación API antes de confirmar

La shell MUST invocar API de pre-evaluación de crédito antes de confirmar checkout cuando flag ON, mostrando resultado en modal o banner si el semáforo es rojo/amarillo. MUST usar modales Synap; MUST NOT usar `alert`/`confirm` nativos.

#### Scenario: Confirmación con advertencia crédito

- **GIVEN** semáforo rojo por exceso de monto
- **WHEN** el vendedor pulsa Confirmar
- **THEN** MUST mostrarse modal Synap informando hold y `No Autorizado` esperado
- **AND** MUST permitir continuar o cancelar sin diálogo nativo

#### Scenario: Flag OFF sin pre-evaluación ampliada

- **GIVEN** `ecom_credito_pedidos_activa` OFF
- **WHEN** captura pedido en shell
- **THEN** MUST conservar widget legacy de días/saldo
- **AND** MUST NOT invocar API de exposición $
