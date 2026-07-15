# Delta for ecom-checkout-mayorista

**Change:** `ecom-pedido-cabecera-comercial`

## MODIFIED Requirements

### REQ-CHK-008: Fecha de entrega y cabecera comercial editable (solo PED)

Para **PED**, el sistema **MUST** aceptar `fecha_pedido`, `fecha_entrega` y cabecera comercial desde `CheckoutInput` (o payload API equivalente) validada por `ecom-pedido-cabecera-comercial`. Si el usuario no envía `fecha_entrega`, **MUST** calcularla sumando `dias_entrega` y evitando días no laborables (paridad legacy). Si envía `fecha_entrega` explícita, **MUST** persistirla tras validación. `Vencimiento` **MUST** derivarse de `fecha_pedido + cond_venta.Dias` salvo override supervisor válido. `Fecha` **MUST** ser la `fecha_pedido` editada (no forzar «hoy»). El resultado **MUST** persistirse en `comp_ped.Fecha`, `comp_ped.Vencimiento`, `comp_ped.FechaEntrega`, `comp_ped.CondVenta`, `comp_ped.id_condventa` y `cliente_datos_adicionales.fechaEntrega`. Para **PRE** la fecha de entrega no aplica; `Fecha` y vencimiento/condición **MUST** seguir reglas de cabecera comercial cuando producto lo habilite para presupuesto.

(Previously: `FechaEntrega` solo auto-calculada; `Fecha`=hoy; `Vencimiento` fijo +30 días; lista/condición implícitas del cliente sin UI editable.)

**Acceptance Scenarios:**

```gherkin
Escenario: Fecha de entrega salta día no laborable
  DADO días de entrega = 2 y que el día resultante es no laborable
  Y el usuario NO envió fecha_entrega manual
  CUANDO se confirma el pedido
  ENTONCES FechaEntrega se corre al siguiente día hábil según la configuración
```

```gherkin
Escenario: Fecha de entrega manual del usuario
  DADO un PED con fecha_entrega=20/07/2026 enviada en CheckoutInput
  CUANDO el vendedor confirma el pedido
  ENTONCES comp_ped.FechaEntrega y cliente_datos_adicionales.fechaEntrega MUST ser 20/07/2026
```

```gherkin
Escenario: Fecha pedido editable reemplaza hoy
  DADO fecha_pedido=05/07/2026 en cabecera validada
  CUANDO se confirma el PED
  ENTONCES comp_ped.Fecha MUST ser 05/07/2026
  Y MUST NOT usar la fecha del servidor como única fuente
```

```gherkin
Escenario: Vencimiento por condición no por +30 fijo
  DADO fecha_pedido=10/07/2026 y condición del cliente con Dias=15
  CUANDO se confirma sin override de supervisor
  ENTONCES comp_ped.Vencimiento MUST ser 25/07/2026
```

---

## ADDED Requirements

### REQ-CHK-013 — Panel cabecera comercial en checkout mayorista

El checkout mayorista MUST mostrar panel de cabecera comercial (canon MPR/slate): fecha pedido, fecha entrega (PED), vencimiento (auto + override supervisor), condición de pago y lista de precios. MUST consumir relays de catálogo (`lista_precio`, `cond_venta`). Vendedor MUST ver lista y condición solo lectura; supervisor MUST poder editarlas. Domicilio/ruta MAY mostrarse en UI cuando el costo de envío sea bajo (campos ya soportados en `CheckoutInput`).

#### Scenario: Panel visible en checkout PED

- **GIVEN** carrito PED con cliente seleccionado
- **WHEN** el vendedor abre confirmación
- **THEN** MUST ver panel cabecera con fechas, condición y lista
- **AND** vencimiento MUST mostrarse calculado automáticamente

#### Scenario: Vendedor solo lectura en lista y condición

- **GIVEN** vendedor sin permiso supervisor
- **WHEN** renderiza panel cabecera
- **THEN** controles de lista y condición MUST estar deshabilitados o en solo lectura

---

### REQ-CHK-014 — Propagación CheckoutInput y lista en commit

`CheckoutInput` MUST extenderse con campos de cabecera comercial (`fecha_pedido`, `fecha_entrega`, `vencimiento` opcional, `id_condventa`, `lista_id`). La API de confirmar MUST validar vía resolver compartido y MUST propagar `lista_id` a renglones `stockp.lista_precio`. Si supervisor cambia lista, MUST recalcular totales del carrito (`cart.lista_id` + `recalcular_totales`) antes del commit; si el recálculo falla, MUST bloquear confirmación.

#### Scenario: Payload cabecera en confirmar

- **GIVEN** POST confirmar con cabecera válida en body
- **WHEN** `mayorista_checkout_service.confirmar` ejecuta
- **THEN** MUST mapear campos a `comp_ped` y `stockp` según REQ-CC-06

#### Scenario: Cambio de lista recalcula antes de commit

- **GIVEN** supervisor cambia lista en UI y carrito con ítems
- **WHEN** confirma pedido
- **THEN** importes de renglones MUST reflejar la nueva lista
- **AND** MUST NOT confirmar si el motor de precios falla

#### Scenario: Vendedor no propaga lista alterada

- **GIVEN** vendedor envía `lista_id` distinta al cliente
- **WHEN** backend valida cabecera
- **THEN** MUST usar lista default del cliente
- **AND** MUST NOT escribir lista arbitraria en `stockp`
