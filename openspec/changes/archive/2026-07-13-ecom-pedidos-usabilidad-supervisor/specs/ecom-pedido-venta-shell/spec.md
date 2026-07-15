# Delta for ecom-pedido-venta-shell

**Change:** `ecom-pedidos-usabilidad-supervisor`  
**Base:** change `ecom-venta-pedido-unificada` (REQ-VTA-01–04)

## ADDED Requirements

### REQ-VTA-05 — Badge lista de precios solo lectura

En el header de captura (`pedidos_order_header.html`), el sistema MUST mostrar badge solo lectura con el nombre/código de la lista de precios del cliente (`cliente.ListaPrecio`) y enlace al PDF de lista vigente. MUST NOT ofrecer selector para cambiar lista.

#### Scenario: Cliente con lista asignada

- **GIVEN** cliente seleccionado con `ListaPrecio=2` («Mayorista»)
- **WHEN** se renderiza el header de venta
- **THEN** MUST mostrar badge «Lista: Mayorista» no editable
- **AND** MUST mostrar enlace «Ver PDF» que abre `lista_precios_pdf` para esa lista

#### Scenario: Sin override de lista

- **GIVEN** usuario supervisor en pedido simple
- **WHEN** intenta cambiar lista desde la UI
- **THEN** MUST NOT existir control editable de lista

---

### REQ-VTA-06 — Columna descuento por línea

La tabla de líneas (`pedidos_lineas_tabla.html`) MUST exponer columna «% desc.» editable por renglón (0–100). Al cambiar el valor, MUST invocar `PATCH …/carrito/items/<id>/` con `porcentaje_descuento` y refrescar totales vía respuesta del backend (`setCart`). MUST NOT recalcular totales en frontend.

#### Scenario: Editar descuento renglón

- **GIVEN** carrito con ítem neto 1000 y 0% descuento
- **WHEN** el vendedor ingresa 10% en la columna del renglón
- **THEN** MUST persistir 10% vía API
- **AND** totales mostrados MUST coincidir con `serializar_carrito` del backend

---

### REQ-VTA-07 — Selector supervisor en shell

Si el usuario es supervisor con cartera (`REQ-VOP-03`), la shell MUST incluir selector de vendedor operativo accesible desde el header o barra de contexto, sin salir de `/venta/`.

#### Scenario: Selector visible para supervisor

- **GIVEN** supervisor con `vendedor_a_cargo=[20,21]`
- **WHEN** abre pedido simple
- **THEN** MUST ver dropdown/combobox para elegir vendedor operativo

---

### REQ-VTA-08 — Banner operativo en shell

La shell MUST mostrar banner «Operando como: …» cuando aplica `REQ-VOP-04`, integrado en el layout OrderShell sin ocultarse al scroll de líneas.

#### Scenario: Banner con vendedor distinto al logueado

- **GIVEN** supervisor operando como vendedor 21
- **WHEN** captura líneas en la shell
- **THEN** MUST ver banner persistente con nombre del vendedor 21

---

### REQ-VTA-09 — Descuento al pie precargado

El resumen (`pedidos_order_summary.html`) MUST precargar el input de descuento al pie con `cliente.Descuento` al seleccionar cliente y sincronizar vía `POST …/carrito/descuento-pie/` si difiere del carrito.

#### Scenario: Selección de cliente con descuento comercial

- **GIVEN** cliente con `Descuento=5`
- **WHEN** el vendedor lo selecciona en predictive
- **THEN** el campo descuento pie MUST mostrar `5`
- **AND** MUST aplicarse al carrito mediante API
