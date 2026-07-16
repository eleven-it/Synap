# Delta for ecom-pedido-venta-shell

**Change:** `ecom-pedido-simple-unificado-masivo`  
**Base:** `openspec/specs/ecom-pedido-venta-shell/spec.md`

## MODIFIED Requirements

### REQ-VTA-01 — Redirect canónico (deprecación OrderShell activa)

El sistema MUST NOT servir OrderShell como pantalla activa de captura en `/ecom/mayoristapp/venta/`. MUST responder **302** hacia `/ecom/mayoristapp/pedido-masivo-sucursales/?modo=simple`, preservando query string (`cod_mov`, `draft` u otros). El código de OrderShell MAY permanecer en repositorio para compatibilidad transitoria pero MUST NOT ser destino operativo.

(Previously: OrderShell era la pantalla canónica de alta y edición con `EcomCart`.)

#### Scenario: Alta sin cod_mov

- **GIVEN** usuario autenticado con permiso de pedidos
- **WHEN** abre `/ecom/mayoristapp/venta/`
- **THEN** MUST recibir 302 a pedido masivo `?modo=simple`
- **AND** MUST NOT renderizar shell OrderShell con carrito

#### Scenario: Abrir PED existente vía venta

- **GIVEN** un `CodigoMovimiento` PED válido
- **WHEN** abre `/ecom/mayoristapp/venta/?cod_mov={id}`
- **THEN** MUST recibir 302 a `?modo=simple&cod_mov={id}`
- **AND** MUST cargar el PED en draft masivo en el destino

---

## REMOVED Requirements

### REQ-VTA-02 — Modo según estado

(Razón: comportamiento migrado a `ecom-pedido-simple-unificado` REQ-PSU-05 sobre matriz masiva 1 columna.)

### REQ-VTA-03 — Acciones de gestión en la shell

(Razón: acciones migradas a `ecom-pedido-simple-unificado` REQ-PSU-07 en hero de pedido simple.)

### REQ-VTA-04 — Confirmar edición de Pendiente

(Razón: semántica anula+crea migrada a `ecom-pedido-simple-unificado` REQ-PSU-06 vía checkout mayorista.)

### REQ-VTA-05 — Badge lista de precios solo lectura

(Razón: UI de captura simple vive en matriz masiva; badge MUST aplicarse en contexto masivo según diseño.)

### REQ-VTA-06 — Columna descuento por línea

(Razón: descuentos fila en simple usan REQ-MAS-08/09 de matriz masiva, no tabla carrito.)

### REQ-VTA-07 — Selector supervisor en shell

(Razón: selector operativo migrado a REQ-MAS-11 en pedido masivo/simple.)

### REQ-VTA-08 — Banner operativo en shell

(Razón: banner operativo migrado a REQ-MAS-11 en pedido masivo/simple.)

### REQ-VTA-09 — Descuento al pie precargado

(Razón: descuento pie en simple usa REQ-MAS-08/09 en draft masivo, no API carrito.)
