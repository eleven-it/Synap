# Delta for ecom-pedido-masivo-sucursales

**Change:** `ecom-pedido-masivo-consolidado-hub`  
**Base:** `openspec/specs/ecom-pedido-masivo-sucursales/spec.md`

## ADDED Requirements

### REQ-MAS-20 — Post-confirmación hacia resumen y hub

Tras confirmación exitosa de pedido masivo (`batch_checkout_masivo`), el sistema MUST redirigir o presentar descubrimiento claro del lote consolidado: enlace/CTA hacia resumen `/ecom/mayoristapp/pedidos/lote/<draft_id>/` y referencia al lane **Cargas masivas** del hub. MUST NOT dejar al usuario solo con N PED sueltos sin contexto de lote. Mensajes MUST estar en español.

#### Scenario: Redirección tras confirmar

- **GIVEN** matriz confirmada exitosamente con 3 sucursales
- **WHEN** finaliza checkout masivo
- **THEN** MUST navegar al resumen del lote o mostrar pantalla de éxito con CTA «Ver resumen del lote»
- **AND** MUST incluir `draft_id` del draft confirmado

#### Scenario: Descubrimiento desde hub

- **GIVEN** usuario que confirma y vuelve manualmente al hub
- **WHEN** abre `/ecom/mayoristapp/pedidos/`
- **THEN** MUST encontrar tarjeta `lote_masivo` en Cargas masivas (REQ-HUB-07)
- **AND** PED hijos MUST mostrar chip de lote (REQ-HUB-09)

#### Scenario: Confirmación con workflow comercial

- **GIVEN** subflag aprobación ON y PED pendientes tras confirmar
- **WHEN** muestra post-confirmación
- **THEN** MUST indicar que la autorización es a nivel lote
- **AND** MUST NOT sugerir aprobar PED uno a uno

---

### REQ-MAS-21 — Matriz read-only reutilizable

El componente de matriz masiva MUST soportar modo `readonly=1` reutilizable desde pestaña «Qué se cargó» del resumen de lote (REQ-LOT-03). En readonly MUST renderizar cantidades, precios y descuentos persistidos sin inputs editables, autoguardado ni CTAs de confirmación. MUST conservar semántica UOM packs y columnas por sucursal (REQ-MAS-01).

#### Scenario: Query readonly en resumen

- **GIVEN** draft confirmado con matriz persistida
- **WHEN** resumen embebe matriz con `readonly=1`
- **THEN** MUST mostrar mismas filas/columnas que captura original
- **AND** MUST NOT disparar POST de autoguardado ni abrir modal confirmar

#### Scenario: Readonly no habilita re-edición

- **GIVEN** matriz embebida en pestaña «Qué se cargó»
- **WHEN** usuario intenta modificar cantidades vía teclado o DOM
- **THEN** MUST NOT persistir cambios
- **AND** MUST NOT ofrecer CTA «Confirmar lote»

#### Scenario: Coherencia con captura activa

- **GIVEN** mismo draft en captura activa (BORRADOR) vs resumen confirmado
- **WHEN** compara estructura de matriz
- **THEN** columnas sucursal MUST coincidir con domicilios del draft al confirmar
- **AND** readonly MUST NOT requerir selector cliente/vendedor editable
