# Delta for ecom-pedido-masivo-sucursales

**Change:** `ecom-pedido-cabecera-comercial`

## MODIFIED Requirements

### REQ-MAS-17 — Lista de precios en barra de contexto

La barra de contexto MUST mostrar lista de precios del pedido masivo. MUST iniciar con default del **cliente**. Supervisor MUST poder cambiar lista desde la barra; vendedor MUST verla en solo lectura. Al cambiar lista, MUST recalcular precios de filas (`REQ-MAS-07`) antes de preview/confirmación.

(Previously: badge de lista solo lectura sin override en pedido masivo.)

#### Scenario: Badge visible sin borrador

- **GIVEN** cliente seleccionado en barra de contexto sin borrador aún
- **WHEN** la UI muestra la barra
- **THEN** MUST aparecer lista de precios con valor default del cliente

#### Scenario: Supervisor cambia lista en masivo

- **GIVEN** supervisor con cliente lista `3` y catálogo disponible
- **WHEN** selecciona lista `5` en barra de contexto
- **THEN** precios de matriz MUST recalcularse con lista `5`
- **AND** confirmación MUST propagar `lista_id=5` a todos los PED del lote

#### Scenario: Vendedor no override lista

- **GIVEN** vendedor sin permiso supervisor
- **WHEN** interactúa con barra de contexto
- **THEN** control de lista MUST permanecer solo lectura

---

## ADDED Requirements

### REQ-MAS-20 — Cabecera comercial en barra de contexto masivo

Pedido masivo MUST integrar en la barra de contexto (junto a vendedor/cliente) los campos de cabecera comercial: `fecha_pedido`, `fecha_entrega` editable (`dias_entrega` o fecha directa), `vencimiento` auto (+ override supervisor), condición de pago. MUST reutilizar resolver `ecom-pedido-cabecera-comercial` y canon UI slate/sky. MUST exponer valores en API de contexto/preview para hidratar Alpine.

#### Scenario: Fecha entrega editable en lote

- **GIVEN** borrador masivo abierto para PED
- **WHEN** supervisor o vendedor edita fecha de entrega en barra
- **THEN** valor MUST persistir en estado del borrador
- **AND** preview MUST reflejar la nueva fecha

#### Scenario: Vencimiento auto al cambiar condición en masivo

- **GIVEN** `fecha_pedido=01/07/2026` y condición `Dias=10`
- **WHEN** supervisor cambia condición a `Dias=25` en barra
- **THEN** vencimiento mostrado MUST actualizarse a `26/07/2026`

#### Scenario: Condición solo lectura para vendedor

- **GIVEN** vendedor sin permiso supervisor en pedido masivo
- **WHEN** renderiza barra de cabecera
- **THEN** condición MUST ser solo lectura con default `cliente.id_cv`

---

### REQ-MAS-21 — Propagación de cabecera al lote

Al confirmar pedido masivo, la misma cabecera comercial validada (fechas, condición, lista) MUST aplicarse a **cada** PED generado por sucursal (`REQ-MAS-03`). `batch_checkout_masivo` MUST construir `CheckoutInput` por domicilio con la cabecera unificada del lote. MUST NOT calcular fechas distintas por sucursal salvo que producto defina domicilio-específico (fuera de alcance).

#### Scenario: Tres sucursales misma cabecera

- **GIVEN** lote con 3 sucursales con cantidades > 0 y cabecera `fecha_pedido=10/07/2026`, `lista_id=4`
- **WHEN** confirma pedido masivo
- **THEN** los 3 `comp_ped` MUST tener `Fecha=10/07/2026`, misma condición y mismo vencimiento
- **AND** renglones de cada PED MUST tener `lista_precio=4`

#### Scenario: Fallo en sucursal no altera cabecera de borrador

- **GIVEN** lote con cabecera editada y fallo en sucursal 2 (`REQ-MAS-05`)
- **WHEN** termina el intento con rollback/compensación
- **THEN** borrador MUST conservar cabecera y celdas intactas para reintento
