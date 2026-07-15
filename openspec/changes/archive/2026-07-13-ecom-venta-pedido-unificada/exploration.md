# Exploration — Pedido de venta unificado (`/venta/`)

**Change:** `ecom-venta-pedido-unificada`  
**Fecha:** 13/07/2026

## Contexto

| Pieza | Hoy |
|-------|-----|
| Alta OrderShell | `/ecom/mayoristapp/compra/` → `CompraMayoristaView` + `compra_mayorista*.mjs` |
| Detalle PED | `/ecom/mayoristapp/pedidos/<cod_mov>/` → `PedidoDetalleView` + `pedido_detalle.html` |
| Hub | links a compra (nuevo) y detalle (cards PED) |
| Post-checkout | `detalleTrasExitoUrl` en `compra_mayorista_checkout.mjs` |
| Anulación | solo `Estado='Pendiente'` (`puede_anular_pedido_relay`) |
| Spec §6.2 | PED confirmado no editable (anular + repetir) |

## Problema

1. Dos pantallas para el ciclo de vida del mismo pedido de venta.
2. Slug `/compra/` no refleja pedidos de **venta**.
3. Acciones (Repetir, Anular, PDF, mail) viven solo en el detalle.
4. Producto exige: no modificar si el PED entró en producción; unificar UX en una sola shell.

## Decisiones acordadas

- Ruta canónica: `/ecom/mayoristapp/venta/`.
- `/compra/` y `/pedidos/<cod_mov>/` → redirect.
- `Estado='Pendiente'` → editable vía anular origen + checkout nuevo.
- Estados posteriores → solo lectura (+ Repetir/PDF/mail; Anular si aplica).

## Archivos clave a tocar

- `ecom/urls.py`, `ecom/mayoristapp_web_views.py`, `ecom/pedido_gestion_views.py`
- `ecom/services/pedidos_hub_pipeline.py`, `ecom/services/cliente_relay.py`
- `core/utils/utils.py`, `ecom/menu_config.py`
- `ecom/templates/ecom/compra_mayorista.html`, `ecom/static/ecom/js/compra_mayorista_*.mjs`
- `ecom/templates/ecom/pedido_detalle.html` (deprecar uso)
- Docs `docs/ecom/SPEC_GESTION_PEDIDOS_SYNAP.md`, `UI_COMPRA_MAYORISTA_P3.md`
- Tests `test_compra_mayorista_*`, `test_pedido_gestion`, hub pipeline

## Riesgos

- Rename amplio de reverse names en menú/tests.
- Edición Pendiente como anular+nuevo cambia el `CodigoMovimiento` (usuario debe confirmarlo).
- PRE/DEV detalle en `/comprobantes/` queda fuera de alcance.
