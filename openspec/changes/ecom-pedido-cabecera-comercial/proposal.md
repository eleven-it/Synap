# Proposal: Cabecera comercial de pedidos e-commerce

**Change:** `ecom-pedido-cabecera-comercial` · **Fecha:** 14/07/2026

## Intent

Hoy el checkout mayorista y el pedido masivo persisten cabecera comercial con valores fijos o solo del cliente (`Vencimiento` +30 días, `Fecha`=hoy, lista/condición no editables). Producto exige paridad AdministraNET con fechas editables, vencimiento por `cond_venta.Dias`, y permisos supervisor/vendedor sobre lista y condición de pago.

## Scope

### In Scope
- Servicio compartido de cabecera comercial (fechas, condición, lista) consumido por checkout simple y lote masivo.
- UI cabecera en compra mayorista y pedido masivo: fecha pedido, entrega, vencimiento (auto + override), condición de pago, lista de precios.
- Persistencia AdministraNET: `comp_ped.Fecha`, `Vencimiento`, `FechaEntrega`, `CondVenta`, `id_condventa`; `stockp.lista_precio`.
- Permisos: supervisor edita lista y condición; vendedor solo defaults del **cliente** (`cliente.ListaPrecio`, `cliente.id_cv`).
- Pedido masivo: `dias_entrega`/fecha entrega editable en cabecera de lote.
- Checkout simple: domicilio/ruta en UI si costo bajo (campos ya en `CheckoutInput`).

### Out of Scope
- `ImporteVentaL`, `CotiDolar`, `geo_latitud`/`geo_longitud`.
- Default de condición a nivel usuario (asumimos cliente salvo evidencia en código).

## Capabilities

### New Capabilities
- `ecom-pedido-cabecera-comercial`: modelo de cabecera, cálculo vencimiento, validación permisos, relay catálogos condición/lista.

### Modified Capabilities
- `ecom-checkout-mayorista`: REQ-CHK-008 extendido; nuevos requisitos cabecera editable y lista en commit.
- `ecom-pedido-masivo-sucursales`: cabecera comercial en barra contexto + propagación al lote.

## Approach

1. Extraer `PedidoCabeceraComercial` (dataclass) + `resolver_cabecera_comercial()` en `ecom/services/pedido_cabecera_comercial.py`: defaults desde cliente, `vencimiento = fecha_pedido + cond_venta.Dias`, override validado.
2. Extender `CheckoutInput` y API confirmar/masivo con payload cabecera; recalcular precios si supervisor cambia lista (`cart.lista_id` + `recalcular_totales`).
3. Supervisor: reutilizar `vendedor_operativo.listar_cartera_operativa` (`supervisor_venta` / `permiso_supervisor_venta_web`); flag `puede_editar_cabecera_comercial`.
4. UI: panel cabecera canon MPR/slate en checkout y barra contexto masivo; vendedor read-only en lista/condición.
5. Tests unitarios cálculo vencimiento, permisos y persistencia en `mayorista_checkout_service` / `batch_checkout_masivo`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `ecom/services/pedido_cabecera_comercial.py` | New | Resolver y validar cabecera |
| `ecom/services/mayorista_checkout_service.py` | Modified | Usar cabecera; quitar +30 fijo |
| `ecom/services/batch_checkout_masivo.py` | Modified | Cabecera lote → cada PED |
| `ecom/checkout_relay_views.py` | Modified | Body cabecera |
| `ecom/pedido_masivo_views.py` | Modified | API contexto + confirmación |
| `ecom/static/ecom/js/compra_mayorista_*.mjs` | Modified | UI checkout |
| `ecom/static/ecom/js/pedido_masivo_app.mjs` | Modified | UI masivo |
| `ecom/templates/ecom/` | Modified | Panel cabecera |
| `docs/ecom/` | Modified | Comportamiento cabecera |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Cambio lista invalida precios en carrito | Med | Recalcular totales antes de confirmar; bloquear si motor falla |
| Override vencimiento incoherente con condición | Med | Auto desde Dias; override solo supervisor con validación ≥ fecha pedido |
| Divergencia simple vs masivo | Low | Servicio único compartido |

## Rollback Plan

Revertir commit del change: servicios vuelven a `hoy`/`+30` y defaults cliente; UI cabecera oculta. Sin migración MySQL. Borradores Postgres sin campos nuevos siguen válidos (ignorar extras).

## Dependencies

- Specs vigentes `ecom-checkout-mayorista`, `ecom-pedido-masivo-sucursales`, `ecom-vendedor-operativo`.
- Relay `lista_precio_relay_json` y lectura `cond_venta` (tabla legacy).

## Success Criteria

- [ ] `Vencimiento` = `Fecha` + `cond_venta.Dias` por defecto (no +30).
- [ ] Supervisor cambia lista/condición; vendedor no puede.
- [ ] Fechas pedido/entrega editables; persisten en `comp_ped` y CDA.
- [ ] Masivo propaga misma cabecera a todos los PED del lote.
- [ ] Tests en contenedor pasan para checkout y lote.

## Decisiones producto (14/07/2026)

Ver bloque locked del orquestador: vencimiento por Dias, fechas editables, lista/condición por rol, masivo con fecha entrega, domicilio/ruta opcional en simple.
