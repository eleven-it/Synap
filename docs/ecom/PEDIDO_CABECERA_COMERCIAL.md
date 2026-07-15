# Cabecera comercial de pedidos e-commerce

**Change:** `ecom-pedido-cabecera-comercial` · **Fecha:** 14/07/2026

## Resumen

Cabecera comercial unificada para checkout mayorista y pedido masivo: fechas editables, vencimiento por `cond_venta.Dias`, lista y condición con permisos supervisor/vendedor.

## Reglas de negocio

| Campo | Default | Editable por vendedor | Editable por supervisor |
|-------|---------|----------------------|-------------------------|
| Fecha pedido | Hoy (o sesión) | Sí | Sí |
| Fecha entrega (PED) | `fecha_pedido + dias_entrega` (días hábiles) | Sí | Sí |
| Vencimiento | `fecha_pedido + cond_venta.Dias` | No (auto) | Sí (≥ fecha pedido) |
| Condición (`id_condventa`) | `cliente.id_cv` | Solo lectura | Sí |
| Lista (`lista_id`) | `cliente.ListaPrecio` (1–5) | Solo lectura | Sí |

- El vencimiento **no** usa offset fijo +30 días.
- Overrides de lista/condición/vencimiento enviados por vendedor se **ignoran** en servidor.
- Al confirmar: `comp_ped` recibe `Fecha`, `Vencimiento`, `FechaEntrega`, `CondVenta`, `id_condventa`; `stockp.lista_precio` en cada renglón.

## Servicio

`ecom/services/pedido_cabecera_comercial.py`:

- `resolver_cabecera_comercial()` — resolver único simple + masivo
- `puede_editar_cabecera_comercial()` — reutiliza `_si_no_supervisor` (`supervisor_venta` / `permiso_supervisor_venta_web`)
- `condiciones_venta_relay_json()` en `precio_relays.py` — catálogo `cond_venta` (`Codigo`, `Descripcion`, `Dias`)

## UI

- Fechas en pantalla: **dd/MM/yyyy**; APIs y MySQL: ISO / `DATE`.
- Checkout: panel en `pedidos_cabecera_comercial.html` + `compra_mayorista_checkout.mjs`.
  - Desktop (`lg+`): una sola instancia en el resumen lateral (`pedidos_order_summary.html`).
  - Mobile/tablet: instancia en columna principal (`compra_mayorista.html`, `lg:hidden`).
- Masivo: barra de contexto + `pedido_masivo_app.mjs`.
- Cambio de lista (supervisor): `PATCH /ecom/api/mayoristapp/carrito/lista-precio/` repricing antes de confirmar.

## APIs

| Endpoint | Uso |
|----------|-----|
| `GET .../venta/contexto/` | Defaults cabecera + `puede_editar_cabecera` |
| `GET .../precios/condiciones-venta/` | Catálogo condiciones |
| `POST .../checkout/confirmar/` | Body: fechas ISO, `id_condventa`, `lista_id` |
| `POST .../pedido-masivo/preview/` y `confirmar/` | Misma cabecera al lote |

## Tests

```bash
docker exec Synap_app python manage.py test \
  ecom.tests.test_pedido_cabecera_comercial \
  ecom.tests.test_mayorista_checkout_service \
  ecom.tests.test_batch_checkout_masivo \
  --keepdb
```

## Referencias

- `docs/ecom/CHECKOUT_MAYORISTA_P2.md`
- `docs/ecom/PEDIDO_MASIVO_SUCURSALES.md`
- `reports/docs/tablas/cond_venta.md` — columnas `Codigo`, `Descripcion`, `Dias`
