# Proposal: Unificación pedido simple en masivo (1 sucursal)

## Intent

Hoy existen dos workspaces de captura (OrderShell/`EcomCart` en `/venta/` y matriz masiva) con paridad funcional incompleta. Unificar «Pedido simple» como variante de masivo con una columna elimina duplicación, centraliza borrador en `EcomPedidoMasivoDraft` y habilita mail, crédito y repetir pedido en el flujo simple.

## Scope

### In Scope
- Modo `?modo=simple` en `/pedido-masivo-sucursales/` (1 domicilio, UI «Pedido simple»)
- Campos draft: `cod_mov_origen`, `id_domicilio_fijo`; servicio PED→celdas
- Hub/PWA/menú: URLs masivo; un solo tipo borrador; modal Continuar/Archivar en nuevo simple
- Redirect 302 `/venta/` y `/compra/` → masivo (preservar `cod_mov`, `draft`)
- Paridad UX: crédito, mail, repetir, PDF/anular en consulta-edición PED
- Confirmación vía `mayorista_checkout_service.confirmar`; edición Pendiente = anula+crea (REQ-VTA-04)
- Pack Bulto>Display; solo PED; sin filtro stock en catálogo de captura
- Unificación permisos simple↔masivo; migración suave borradores `EcomCart`

### Out of Scope
- PRE/DEV en flujo unificado; UPDATE in-place MySQL; eliminación física de `EcomCart`/OrderShell
- Cambios en `ecom-pedido-cabecera-comercial` (ya aplicado)

## Capabilities

### New Capabilities
- `ecom-pedido-simple-unificado`: modo 1 sucursal, carga/edición/consulta PED vía draft, `cod_mov_origen`, hero acciones (mail/crédito/repetir/PDF)

### Modified Capabilities
- `ecom-pedido-masivo-sucursales`: ADD modo simple 1 columna; MOD etiquetas UI; ADD repetir/mail/crédito/consulta `cod_mov`; campos draft
- `ecom-pedido-venta-shell`: DEPRECATE shell activa; redirect canónico; reqs migrados a simple-unificado
- `ecom-pedidos-hub-kanban`: MOD REQ-HUB-02/03 — borrador único masivo; URLs; modal nuevo simple
- `ecom-checkout-mayorista`: CLARIFY `EcomCart` solo efímero en batch confirmación
- `ecom-carrito-mayorista`: DEPRECATE borrador persistente como workspace de pedido simple

## Approach

1. **Backend:** migración Postgres + `cargar_pedido_en_draft_masivo` (fork `pedido_plantilla_service` → celdas, 1 domicilio).
2. **Routing:** canon `?modo=simple` (+ `draft`, `cod_mov`, `id_domicilio`); redirect `/venta/`.
3. **UI:** matriz 1 col; portar mixins mail/crédito/repetir; read-only en consulta.
4. **Hub:** pipeline sin `_borradores_carrito`; PED → masivo `?cod_mov=`.
5. **Orden:** draft/carga PED → hub URLs → UI simple → acciones → redirect → limpieza carrito.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `ecom/models.py` | Modified | `cod_mov_origen`, `id_domicilio_fijo` |
| `ecom/services/pedido_masivo_matriz.py` | Modified | Modo simple, carga PED |
| `ecom/services/pedidos_hub_pipeline.py` | Modified | URLs, borrador único |
| `ecom/pedido_masivo_views.py` + `pedido_masivo_app.mjs` | Modified | Modo simple, hero acciones |
| `ecom/mayoristapp_web_views.py` | Modified | Redirect venta |
| `core/pwa_nivel_a.py`, `mobile_level_a_middleware.py` | Modified | Deep links Nivel A |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Permisos simple sin `ecom.pedido_masivo.usar` | Med | Unificar o alias permiso en propose→spec |
| Borradores `EcomCart` en prod | Med | CTA migrar o script one-shot |
| Conversión packs al reabrir PED | Low | Tests edge UOM; mensaje si redondeo |
| PED origen anulado externamente | Med | Validar al confirmar |

## Rollback Plan

1. Revertir redirect `/venta/` y restaurar hub URLs a OrderShell.
2. Feature flag o quitar `modo=simple`; masivo multi-sucursal sin cambios.
3. Campos draft nuevos nullable — código anterior ignora.
4. Borradores masivo intactos; carritos legacy no se borran automáticamente.

## Dependencies

- `ecom-pedido-cabecera-comercial` (apply-complete)

## Success Criteria

- [ ] Nuevo/continuar/editar/consultar PED simple solo vía masivo `modo=simple`
- [ ] `/venta/` redirige preservando query; hub un borrador tipo masivo
- [ ] Mail, crédito, repetir operativos en simple; confirm usa checkout mayorista
- [ ] Tests hub, masivo, PWA y carga PED→draft verdes
