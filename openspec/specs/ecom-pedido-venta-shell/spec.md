# Spec: Shell de pedido de venta (OrderShell)

**Capability:** `ecom-pedido-venta-shell`  
**Origen:** change `ecom-venta-pedido-unificada` (REQ-VTA-01–04, archivado 13/07/2026); change `ecom-pedidos-usabilidad-supervisor` (REQ-VTA-05–09, archivado 13/07/2026)  
**Ruta:** `/ecom/mayoristapp/venta/`

## Requirements

### REQ-VTA-01 — Pantalla canónica de pedido de venta

El sistema MUST exponer OrderShell en `/ecom/mayoristapp/venta/` para crear un PED (borrador `EcomCart`) y para abrir un PED existente con `?cod_mov=`.

#### Scenario: Alta sin cod_mov

- **GIVEN** usuario autenticado con permiso de pedidos
- **WHEN** abre `/ecom/mayoristapp/venta/`
- **THEN** MUST mostrar shell de carga (cliente, catálogo, carrito, confirmar)

#### Scenario: Abrir PED existente

- **GIVEN** un `CodigoMovimiento` PED válido
- **WHEN** abre `/ecom/mayoristapp/venta/?cod_mov={id}`
- **THEN** MUST cargar cabecera y líneas del PED en la misma shell

---

### REQ-VTA-02 — Modo según estado

Si el PED tiene `Estado='Pendiente'` y `Anulado≠Si`, el shell MUST permitir editar líneas. Si el PED ya entró en producción (`Estado` distinto de `Pendiente`) o está anulado, el shell MUST ser de solo lectura (sin confirmar checkout ni mutar cantidades).

#### Scenario: Pendiente editable

- **GIVEN** PED Pendiente no anulado
- **WHEN** se abre en `/venta/?cod_mov=`
- **THEN** el usuario MUST poder modificar cantidades / renglones en la UI

#### Scenario: En preparación solo lectura

- **GIVEN** PED con `Estado='En preparación'`
- **WHEN** se abre en `/venta/?cod_mov=`
- **THEN** MUST NOT permitir confirmar ni editar cantidades

---

### REQ-VTA-03 — Acciones de gestión en la shell

Con un PED cargado, la shell MUST ofrecer según corresponda: Repetir pedido, Anular (solo si `puede_anular`), Ver PDF, Enviar mail — reutilizando las APIs existentes del detalle.

#### Scenario: Anular visible solo si permitido

- **GIVEN** cabecera con `puede_anular=true`
- **WHEN** se muestra el hero de venta
- **THEN** MUST mostrar acción Anular

---

### REQ-VTA-04 — Confirmar edición de Pendiente

Al confirmar cambios sobre un PED Pendiente, el sistema MUST requerir modal Synap y MUST ejecutar anulación del origen + alta de un nuevo PED vía checkout (no UPDATE in-place del mismo `CodigoMovimiento` en esta entrega).

#### Scenario: Modal de confirmación

- **GIVEN** modo editar Pendiente con cambios en carrito
- **WHEN** el usuario confirma cambios
- **THEN** MUST mostrar modal de riesgos (anula origen, crea nuevo número) y solo entonces invocar anulación + checkout

---

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

---

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
