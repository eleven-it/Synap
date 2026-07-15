# Cabecera comercial de pedidos e-commerce — Specification

**Capability:** `ecom-pedido-cabecera-comercial`  
**Change:** `ecom-pedido-cabecera-comercial`  
**Consumidores:** checkout mayorista (`ecom-checkout-mayorista`), pedido masivo (`ecom-pedido-masivo-sucursales`)

## Purpose

Definir el modelo compartido de cabecera comercial (fechas, condición de venta, lista de precios) con paridad AdministraNET, cálculo de vencimiento por `cond_venta.Dias`, permisos supervisor/vendedor y persistencia legacy unificada para checkout simple y lote masivo.

## Requirements

### REQ-CC-01 — Servicio compartido de cabecera

El sistema MUST exponer un resolver único de cabecera comercial consumido por checkout simple y confirmación masiva. El resolver MUST devolver defaults desde el **cliente** (`cliente.ListaPrecio`, `cliente.id_cv`, fechas iniciales) y MUST validar overrides según rol antes de persistir.

#### Scenario: Defaults desde cliente al abrir checkout

- **GIVEN** cliente con `ListaPrecio` codificada y `id_cv=5`
- **WHEN** el vendedor abre checkout o pedido masivo para ese cliente
- **THEN** la cabecera MUST iniciar con lista y condición del cliente
- **AND** MUST NOT tomar condición por defecto del usuario operativo

#### Scenario: Mismo resolver en simple y masivo

- **GIVEN** mismos datos de cliente y payload de cabecera
- **WHEN** checkout simple y lote masivo invocan el resolver
- **THEN** ambos MUST obtener la misma cabecera normalizada y validada

---

### REQ-CC-02 — Vencimiento por condición de venta

El sistema MUST calcular `Vencimiento` como `fecha_pedido + cond_venta.Dias` (días corridos, paridad AdministraNET). MUST recalcular automáticamente cuando cambie `fecha_pedido` o `id_condventa`. MUST NOT usar offset fijo +30 días salvo que `Dias` de la condición sea 30.

#### Scenario: Vencimiento automático al cargar

- **GIVEN** `fecha_pedido=10/07/2026` y condición con `Dias=15`
- **WHEN** se resuelve la cabecera
- **THEN** `Vencimiento` MUST ser `25/07/2026`

#### Scenario: Recalculo al cambiar condición

- **GIVEN** cabecera con `fecha_pedido=10/07/2026` y condición `Dias=15`
- **WHEN** supervisor cambia condición a `Dias=30`
- **THEN** `Vencimiento` MUST recalcularse a `09/08/2026` sin intervención manual

#### Scenario: Recalculo al cambiar fecha pedido

- **GIVEN** condición con `Dias=7`
- **WHEN** el usuario edita `fecha_pedido` a otra fecha válida
- **THEN** `Vencimiento` MUST actualizarse sumando 7 días a la nueva fecha

---

### REQ-CC-03 — Fechas editables y override de vencimiento

`fecha_pedido` y `fecha_entrega` MUST ser editables en UI (PED). `Vencimiento` MUST mostrarse auto-calculado. Override manual de `Vencimiento` MUST permitirse solo a supervisor; MUST validar `Vencimiento >= fecha_pedido`. Vendedor MUST NOT poder override de vencimiento.

#### Scenario: Vendedor edita fechas pedido y entrega

- **GIVEN** vendedor sin permiso supervisor en checkout PED
- **WHEN** cambia `fecha_pedido` y `fecha_entrega` en el panel cabecera
- **THEN** ambas fechas MUST aceptarse si son válidas
- **AND** `Vencimiento` MUST recalcularse automáticamente

#### Scenario: Supervisor override vencimiento válido

- **GIVEN** supervisor con `fecha_pedido=01/07/2026` y vencimiento auto `16/07/2026`
- **WHEN** override manual a `20/07/2026`
- **THEN** MUST persistir `20/07/2026`

#### Scenario: Override vencimiento anterior a fecha pedido

- **GIVEN** `fecha_pedido=10/07/2026`
- **WHEN** supervisor intenta `Vencimiento=05/07/2026`
- **THEN** MUST rechazar con mensaje en español
- **AND** MUST NOT confirmar el pedido

#### Scenario: Vendedor no puede override vencimiento

- **GIVEN** vendedor sin permiso supervisor
- **WHEN** intenta enviar `Vencimiento` distinto al calculado
- **THEN** MUST ignorar o rechazar el override
- **AND** MUST usar vencimiento auto-calculado

---

### REQ-CC-04 — Lista de precios: default y permisos

La lista MUST iniciar con el default del **cliente** (`cliente.ListaPrecio` / `codListaPrecio`). Solo supervisor (`supervisor_venta` o `permiso_supervisor_venta_web`) MUST poder cambiarla. Vendedor MUST ver la lista en solo lectura y MUST NOT alterar `lista_id` en confirmación.

#### Scenario: Default lista del cliente

- **GIVEN** cliente con lista codificada `3`
- **WHEN** se abre cabecera comercial
- **THEN** `lista_id` MUST ser `3`

#### Scenario: Supervisor cambia lista

- **GIVEN** supervisor operativo y catálogo de listas disponible
- **WHEN** selecciona lista `7` en cabecera
- **THEN** `lista_id` MUST actualizarse a `7`
- **AND** precios del carrito/matriz MUST recalcularse antes de confirmar

#### Scenario: Vendedor no cambia lista

- **GIVEN** vendedor sin permiso supervisor
- **WHEN** envía payload con `lista_id` distinta al default del cliente
- **THEN** MUST rechazar o normalizar al default del cliente
- **AND** UI MUST mostrar lista solo lectura

---

### REQ-CC-05 — Condición de venta: default y permisos

La condición MUST iniciar con `cliente.id_cv` y descripción legacy asociada. Solo supervisor MUST poder cambiarla. Vendedor MUST ver condición en solo lectura. El default MUST provenir del **cliente**, no del usuario.

#### Scenario: Default condición del cliente

- **GIVEN** cliente con `id_cv=4` y `cond_venta.Dias=20`
- **WHEN** se resuelve cabecera
- **THEN** `id_condventa` MUST ser `4`
- **AND** vencimiento MUST usar `Dias=20`

#### Scenario: Supervisor cambia condición

- **GIVEN** supervisor en checkout
- **WHEN** selecciona otra condición válida del catálogo
- **THEN** `id_condventa` y `CondVenta` MUST actualizarse
- **AND** `Vencimiento` MUST recalcularse con los nuevos `Dias`

#### Scenario: Vendedor no cambia condición

- **GIVEN** vendedor sin permiso supervisor
- **WHEN** envía `id_condventa` distinto al del cliente
- **THEN** MUST rechazar o normalizar al `id_cv` del cliente

---

### REQ-CC-06 — Persistencia AdministraNET

Al confirmar PED/PRE, el sistema MUST persistir en `comp_ped`: `Fecha`, `Vencimiento`, `FechaEntrega`, `CondVenta`, `id_condventa` normalizados con `administranet_types`. MUST persistir `lista_precio` en cada renglón `stockp` del comprobante. MUST replicar `fechaEntrega` en `cliente_datos_adicionales` cuando aplique PED.

#### Scenario: Cabecera en comp_ped

- **GIVEN** cabecera validada con fechas y condición editadas
- **WHEN** se confirma un PED
- **THEN** `comp_ped` MUST contener los cinco campos de cabecera comercial acordes al payload validado

#### Scenario: Lista en renglones

- **GIVEN** cabecera con `lista_id=5` y 3 ítems
- **WHEN** se insertan renglones `stockp`
- **THEN** los tres MUST tener `lista_precio=5`

---

### REQ-CC-07 — Fuera de alcance

Este change MUST NOT introducir persistencia ni UI para `ImporteVentaL`, `CotiDolar`, `geo_latitud` ni `geo_longitud` en la cabecera de pedido e-commerce.

#### Scenario: Campos geo excluidos

- **GIVEN** confirmación de pedido con cabecera comercial completa
- **WHEN** se escribe `comp_ped`
- **THEN** MUST NOT depender de latitud/longitud del payload de cabecera
