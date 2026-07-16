# Delta for ecom-pedidos-hub-kanban

**Change:** `ecom-pedido-simple-unificado-masivo`  
**Base:** `openspec/specs/ecom-pedidos-hub-kanban/spec.md`

## ADDED Requirements

### REQ-HUB-07 — URLs canónicas pedido simple y PED

El hub MUST enlazar «Nuevo → Pedido simple», tarjetas PED pendientes y deep links PWA/menú hacia `/ecom/mayoristapp/pedido-masivo-sucursales/?modo=simple` (con `cod_mov` o `draft` según corresponda). MUST NOT enlazar captura simple activa a `/ecom/mayoristapp/venta/`.

#### Scenario: Tarjeta PED en kanban

- **GIVEN** PED pendiente visible en columna Enviado
- **WHEN** el usuario abre para editar
- **THEN** MUST navegar a masivo `?modo=simple&cod_mov={id}`

#### Scenario: Menú Nuevo pedido simple

- **GIVEN** hub con acción Nuevo → Pedido simple
- **WHEN** el usuario la elige
- **THEN** MUST abrir masivo `?modo=simple` sin pasar por `/venta/`

---

## MODIFIED Requirements

### REQ-HUB-02 — Columnas de estado

El Kanban/Lista MUST incluir al menos: Borrador, Enviado, Por autorizar, Aprobado, Anulado. Borrador MUST incluir **únicamente** borradores `EcomPedidoMasivoDraft` del usuario (incluidos los de pedido simple). MUST NOT listar `EcomCart` como borrador de trabajo activo salvo tarjeta legacy de migración documentada en diseño.

(Previously: Borrador incluía carritos `EcomCart` con ítems y borradores masivos.)

#### Scenario: Borrador masivo visible

- **GIVEN** un borrador masivo en estado BORRADOR del usuario
- **WHEN** abre el hub
- **THEN** MUST aparecer en Borrador con CTA Continuar

#### Scenario: Sin borrador carrito en columna Borrador

- **GIVEN** `EcomCart` en estado borrador con ítems
- **WHEN** abre el hub tras unificación
- **THEN** MUST NOT aparecer como borrador estándar
- **AND** MAY mostrar CTA legacy de migración si producto lo define

---

### REQ-HUB-03 — Recuperación

Al continuar un borrador, el sistema MUST abrir pedido masivo (matriz multi-sucursal o `?modo=simple` según origen) con los datos persistidos. Si el usuario elige **Nuevo → Pedido simple** o **Nuevo → Masivo** con borrador activo, MUST pedir confirmación Continuar vs Archivar y crear.

(Previously: «compra simple» abría OrderShell/`EcomCart`; modal solo para Nuevo Masivo.)

#### Scenario: Nuevo simple con borrador existente

- **GIVEN** borrador masivo activo del usuario
- **WHEN** elige Nuevo → Pedido simple
- **THEN** MUST mostrar modal Continuar vs Archivar
- **AND** MUST NOT pisar el borrador sin confirmación

#### Scenario: Continuar borrador simple

- **GIVEN** borrador creado en `modo=simple`
- **WHEN** pulsa Continuar en hub
- **THEN** MUST abrir `/pedido-masivo-sucursales/?modo=simple&draft={id}`

#### Scenario: Nuevo masivo con borrador existente

- **GIVEN** borrador activo
- **WHEN** elige Nuevo → Masivo
- **THEN** MUST mostrar modal de decisión y MUST NOT pisar el borrador sin confirmación
