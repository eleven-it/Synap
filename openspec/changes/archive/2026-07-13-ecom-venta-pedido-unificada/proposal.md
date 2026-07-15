# Proposal: Pedido de venta unificado (`/venta/`)

**Change:** `ecom-venta-pedido-unificada`  
**Fecha:** 13/07/2026

## Intent

Unificar crear, editar (solo Pendiente) y visualizar PED en una sola pantalla OrderShell con slug de **venta** (`/ecom/mayoristapp/venta/`). Deprecar `/compra/` y `/pedidos/<cod_mov>/`. Exponer allí Anular, Repetir, PDF y mail. Impedir modificación cuando el pedido ya entró en producción.

## Scope

### In Scope
- Ruta canónica `/mayoristapp/venta/` + redirects desde `/compra/`
- Redirect `/pedidos/<cod_mov>/` → `/venta/?cod_mov=`
- Modos OrderShell: nuevo/borrador | editar Pendiente | consulta (producción+)
- Acciones: Anular, Repetir, PDF, mail en la shell
- Confirmar edición Pendiente = modal Synap + anular origen + checkout nuevo
- Actualizar hub, menú, relay `frm=0`, post-checkout, docs y tests

### Out of Scope
- UPDATE in-place del mismo `CodigoMovimiento` / `stockp`
- Unificar detalle PRE/DEV (`/comprobantes/<cod_mov>/`)
- Rename masivo obligatorio de archivos `compra_mayorista*` (opcional; rutas/textos primero)

## Capabilities

### New Capabilities
- `ecom-pedido-venta-shell`: OrderShell en `/venta/` con modos por estado PED
- `ecom-gestion-pedidos-navegacion`: redirects y URLs canónicas venta/detalle deprecado

### Modified Capabilities
- (implícito) checkout / anulación / plantilla desde pedido — reutilizados, sin contrato nuevo

## Approach

Mantener template/JS OrderShell; agregar `?cod_mov=` y flags Alpine. Renombrar URL name a `mayoristapp_venta` con alias redirect `mayoristapp_compra`. Hub y listados apuntan a venta con query.

## Affected Areas

| Area | Impact |
|------|--------|
| `ecom/urls.py` | venta + redirects |
| `ecom/mayoristapp_web_views.py` | vista venta, URLs bootstrap |
| `ecom/pedido_gestion_views.py` | detalle → redirect |
| Hub / menu / cliente_relay | reverse venta |
| OrderShell HTML/JS | modos + acciones |
| `docs/ecom/` | spec gestión + UI |

## Success Criteria

- Nuevo pedido y “Ver PED” del hub abren `/venta/`
- `/compra/` y `/pedidos/7/` redirigen
- PED en preparación no permite editar líneas ni confirmar checkout
- Acciones Anular/Repetir visibles en venta cuando correspondan
