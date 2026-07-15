# Delta for ecom-carrito-mayorista

**Change:** `ecom-pedidos-usabilidad-supervisor`

## ADDED Requirements

### REQ-CAR-005 — Precarga descuento al pie desde cliente

Al seleccionar cliente (`cliente_seleccion_relay`), el sistema MUST inicializar `descPie` del carrito con `cliente.Descuento` (normalizado 0–100). Si el carrito borrador ya tiene `descuento_pie_pct`, MUST sincronizar vía `POST …/carrito/descuento-pie/` para reflejar el valor del cliente al cambiar de cliente.

#### Scenario: Cliente con 5% descuento comercial

- **GIVEN** cliente con `Descuento=5` y carrito vacío
- **WHEN** el vendedor selecciona ese cliente
- **THEN** `cart.descuento_pie_pct` MUST ser `5`
- **AND** la UI MUST mostrar 5 en el input de descuento pie

#### Scenario: Cambio de cliente actualiza descuento pie

- **GIVEN** carrito con cliente A (`Descuento=0`) y pie en 0
- **WHEN** cambia a cliente B (`Descuento=10`)
- **THEN** descuento pie MUST pasar a `10` tras selección

---

### REQ-CAR-006 — Coherencia descuento renglón UI ↔ API

El campo `EcomCartItem.porcentaje_descuento` MUST persistirse exclusivamente vía `PATCH …/carrito/items/<id>/`. La UI MUST enviar el valor editado y MUST refrescar el carrito serializado del backend. MUST NOT recalcular netos/IVA en JavaScript.

#### Scenario: PATCH descuento renglón

- **GIVEN** ítem con `porcentaje_descuento=0` y neto 1000
- **WHEN** la UI envía PATCH con `porcentaje_descuento=15`
- **THEN** el ítem MUST quedar con 15%
- **AND** totales del carrito MUST reflejar descuento en neto e IVA vía backend

#### Scenario: descRenglon del cliente al agregar

- **GIVEN** cliente con `descRenglon=8` configurado
- **WHEN** agrega un artículo al carrito
- **THEN** el ítem MUST crearse con `porcentaje_descuento=8` si no hay override manual previo

---

### REQ-CAR-007 — Totales exclusivamente backend

El frontend de pedido simple MUST NOT recalcular subtotales, IVA ni total final localmente. MUST usar únicamente valores de `mayorista_cart_service.serializar_carrito` tras cada mutación (agregar, PATCH cantidad/descuento, descuento pie).

#### Scenario: Totales tras editar descuento línea

- **GIVEN** carrito serializado con total T
- **WHEN** edita % descuento de un renglón
- **THEN** total mostrado MUST ser el T' devuelto por API, no un cálculo JS
