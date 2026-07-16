# Delta for ecom-carrito-mayorista

**Change:** `ecom-pedido-simple-unificado-masivo`  
**Base:** `openspec/specs/ecom-carrito-mayorista/spec.md`

## ADDED Requirements

### REQ-CAR-008 — Deprecación borrador persistente para pedido simple

`EcomCart` en estado `borrador` MUST NOT ser el workspace de captura de pedido simple tras la unificación. Nuevas sesiones de pedido simple MUST crear o continuar `EcomPedidoMasivoDraft`. Las APIs de carrito (`obtener_carrito`, autoguardado) MUST NOT ser invocadas desde la UI canónica de pedido simple.

#### Scenario: Nuevo pedido simple sin carrito borrador

- **GIVEN** usuario inicia pedido simple desde hub
- **WHEN** selecciona cliente y agrega artículos
- **THEN** MUST persistir en draft masivo
- **AND** MUST NOT crear `EcomCart` borrador de trabajo

#### Scenario: Repetir pedido hacia draft

- **GIVEN** usuario repite un PED desde pedido simple
- **WHEN** completa la acción
- **THEN** MUST poblar celdas de draft masivo
- **AND** MUST NOT poblar `EcomCart` borrador

---

### REQ-CAR-009 — Migración suave borradores legacy

Borradores `EcomCart` existentes en producción MUST tratarse con estrategia de migración documentada en diseño (script one-shot y/o tarjeta legacy en hub con CTA). MUST NOT eliminarse automáticamente sin intervención del usuario o proceso explícito.

#### Scenario: Borrador carrito legacy

- **GIVEN** `EcomCart` borrador previo a unificación
- **WHEN** el usuario abre el hub
- **THEN** MAY ver tarjeta legacy con opción migrar o descartar según diseño
- **AND** MUST NOT mezclarse con borrador masivo estándar sin conversión

---

## MODIFIED Requirements

### REQ-CAR-001: Un carrito activo por vendedor y cliente

El sistema MUST mantener, por combinación de empresa + usuario (vendedor), **un** carrito en estado `borrador` **solo para flujos que aún dependan explícitamente del carrito** (p. ej. carritos efímeros de checkout batch). Para pedido simple y captura mayorista unificada, el borrador activo MUST ser `EcomPedidoMasivoDraft`. Al cambiar el cliente seleccionado en flujos carrito legacy, el carrito borrador MUST vaciarse/recrearse (paridad `session.pop("jcart")` del PHP).

(Previously: carrito borrador era el workspace universal de pedido simple.)

#### Scenario: Crear u obtener el carrito activo (flujo legacy/técnico)

- **GIVEN** un vendedor autenticado con cliente y lista de precio en sesión en flujo que usa carrito
- **WHEN** solicita su carrito activo por primera vez
- **THEN** el sistema crea un carrito en estado borrador asociado a ese usuario y cliente
- **Y** devuelve el carrito vacío con totales en cero

#### Scenario: Cambio de cliente reinicia el carrito

- **GIVEN** un carrito borrador con ítems para el cliente A
- **WHEN** el vendedor selecciona el cliente B y solicita el carrito
- **THEN** el carrito del cliente A no se mezcla con el del cliente B
- **Y** el carrito devuelto para B no contiene los ítems de A

#### Scenario: Pedido simple no usa carrito borrador

- **GIVEN** captura en pedido simple unificado
- **WHEN** agrega artículos
- **THEN** MUST NOT crear ni actualizar `EcomCart` borrador de trabajo

---

### REQ-CAR-002: Agregar ítem con precio del motor y validación de stock

Al agregar un artículo **en flujos carrito activos**, el sistema MUST validar stock según reglas existentes. **Pedido simple en matriz masiva** MUST NOT aplicar filtro de stock en catálogo de captura (REQ-PSU-08); la validación en commit sigue REQ-CHK-003 cuando corresponda.

(Previously: validación de stock aplicaba uniformemente al agregar en carrito de pedido simple.)

#### Scenario: Agregar artículo con stock suficiente

- **GIVEN** un artículo con 100 unidades disponibles en el depósito activo
- **WHEN** el vendedor agrega 10 unidades en flujo carrito
- **THEN** el ítem se agrega con el precio calculado por el motor para la lista del cliente
- **Y** los totales del carrito se recalculan

#### Scenario: Agregar cantidad que excede el stock disponible

- **GIVEN** un artículo con 5 unidades disponibles
- **WHEN** el vendedor intenta agregar 8 unidades en flujo carrito
- **THEN** el sistema NO agrega el ítem
- **Y** devuelve un mensaje en español indicando el stock disponible

#### Scenario: Agregar un artículo ya presente consolida el renglón

- **GIVEN** un carrito con 3 unidades del artículo X
- **WHEN** el vendedor agrega 2 unidades más del artículo X (con stock suficiente)
- **THEN** el carrito tiene un único renglón del artículo X con cantidad 5
