# Proposal: Usabilidad pedidos mayorista + supervisor operativo

**Change:** `ecom-pedidos-usabilidad-supervisor`

## Intent

Cerrar brechas usabilidad/paridad en pedido simple y masivo: supervisor opera por vendedor, VCM dual, descuentos línea/pie, lista precios RO, precio real masivo, UI slate/sky. Fix bug `CodViajante`. Paridad `SPEC_PRESUPUESTO_VENTAS_SYNAP.md` §1.3–§1.4.

## Scope

### In Scope
- **A — Sesión:** `cod_viajante_operativo`, `vendedor_a_cargo`, selector supervisor, fix `_session_cod_viajante`, banner operativo.
- **B — VCM + lista simple:** Ternas en cliente/catálogo; badge lista RO + PDF (`cliente.ListaPrecio`).
- **C — Descuentos simple:** Precarga `descPie`; % desc renglón → PATCH; totales solo backend.
- **D — Masivo:** Precio real, % desc fila/pie lote, `descRenglon` real, preview totales, modal canon; `CodViajante` operativo.
- **E — Visual:** Purple → slate/sky (canon `ui-fuente-verdad-reportes-mpr`).
- **Spike:** Origen MySQL `vendedor_a_cargo` (PHP `control.php`).

### Out of Scope
Override lista; impersonación fuera pedidos; edición PED confirmado; domicilio simple (P0).

## Capabilities

### New Capabilities
- `ecom-vendedor-operativo`: Sesión operativa, cartera supervisor, selector, banner.
- `ecom-ui-pedidos-tokens`: Slate/sky y tokens `.pedidos-*` en flujos pedido.

### Modified Capabilities
- `ecom-pedido-venta-shell`: Badge lista, descuentos UI, supervisor, VCM, tokens.
- `ecom-vendedor-cliente-marca`: REQ-VCM-04 en pedido simple con viajante efectivo.
- `ecom-carrito-mayorista`: Precarga `descPie`; desc renglón UI↔API.
- `ecom-catalogo-producto-mayorista`: Filtro ternas simple; lista RO.
- `ecom-checkout-mayorista`: `CodViajante` operativo; fix sesión.
- `ecom-pedido-masivo-sucursales`: Precio real, descuentos, preview, modal, operativo.
- `ecom-descuentos-pedido-mayorista`: Contrato desc renglón/pie simple y masivo.

## Approach

Corte vertical A→E. Sesión antes UI supervisor; VCM antes descuentos; visual al final. APIs carrito existentes; `pedido_masivo_app.mjs`. Spike en design.

## Affected Areas

| Area | Impact |
|------|--------|
| `mayoristapp_sesion_contexto.py`, `checkout_relay_views.py` | Sesión operativa + fix |
| `cliente_relay.py`, `vendedor_asignacion_sql.py` | VCM + alcance |
| `carrito_relay_views.py`, `mayorista_cart_service.py` | Descuentos |
| `pedido_masivo_*`, `batch_checkout_masivo.py` | Masivo precio/desc |
| `pedidos_*`, `compra_mayorista.html`, `pedido_masivo_sucursales.html` | UI |
| `docs/ecom/*`, `docs/order-ui-redesign/*` | Docs |

## Risks

| Risk | L | Mitigation |
|------|---|------------|
| `vendedor_a_cargo` sin fuente MySQL | H | Spike PHP; seed manual |
| VCM reduce catálogo | M | Datos VCM + comunicación |
| Regresión checkout | M | Tests PED operativo/directo |
| Latencia preview masivo | M | Endpoint agregado + límites |
| PED nombre equivocado | M | Banner + limpiar en logout |

## Rollback Plan

Revert por oleada. Default operativo = `id_vendedor_usr`. Masivo fallback `confirm()`+Precio1V. UI: revert CSS.

## Dependencies

Spike `vendedor_a_cargo`; delta `ecom-pedido-venta-shell`; `price_rules_engine`; ternas VCM pobladas; canon UI reportes/MPR.

## Success Criteria

- [ ] Supervisor elige vendedor → PED con `CodViajante` elegido.
- [ ] VCM en simple y masivo con viajante efectivo.
- [ ] Lista precios badge RO + PDF; sin override.
- [ ] Descuentos línea/pie en simple; masivo precio real + preview + modal.
- [ ] Sin purple; tokens `.pedidos-*`; totales backend; spike documentado.
