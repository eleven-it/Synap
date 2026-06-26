# Tiendanube — precios y stock hacia la API

## Precios (sin IVA desglosado)

La API **Product Variant** (versión **2025-03**) expone un único campo **`price`** (precio de venta) y **`cost`** (costo interno). No hay campos de IVA ni neto/bruto: lo que se envía es el **monto final** que ve el cliente / usa el panel TN.

Referencia: [Product Variant | Nuvemshop API](https://tiendanube.github.io/api-documentation/resources/product-variant).

### Origen en AdministraNET

| Campo TN | Origen Synap | Notas |
|----------|--------------|--------|
| `variant.price` | `articulo.Precio{i}VI` | **Precio final** de la lista configurada (default **Lista 4 — Web**) |
| `variant.cost` | `articulo.PrecioCosto` × (`Precio{i}VI` / `Precio{i}V`) | Costo **final** con el mismo factor IVA que la lista |

### Visualización en Synap (listado y detalle de productos)

En pantallas de productos, **AdministraNET y Tiendanube** muestran siempre **precio de venta final** y **costo final** (con IVA, sin desglose neto). Adminet: `adminet_precio_venta_final` / `adminet_costo_final` en `ProductMapping` (calculados al sincronizar). TN: `tiendanube_price` / `tiendanube_cost` desde la variante. Filtros: `{% load tiendanube_precios %}`.

Helper: `tiendanube_administranet/services/product_pricing.py` → `precios_tiendanube_desde_articulo()`.

**No** se publican `Precio1V` ni `PrecioCosto` netos (evita el desfasaje ej. art. 3134: TN mostraba 1429,74 en lugar de 1829,99 de Lista Web).

### Actualización masiva

- `PATCH /products/stock-price` — acepta `price` y `stock` por variante (hasta 50 por request).
- El **costo** se actualiza con `PUT /products/{id}/variants/{id}` en sync de alta/edición de producto.

## Stock

- **Disponible publicado:** `max(0, saldo − saldo_pedido_cliente)` del `deposito_tiendanube_id`.
- Helper: `product_stock.stock_unidades_articulo_deposito()`.
- Push post-pedido: `order_stock_push.push_stock_for_article_ids()`.

## Sincronización incremental (re-sync sin forzar todo)

La sync masiva **AdministraNET → Tiendanube** (`sync_products_from_adminet`) ya no omite productos en estado `synced` sin más: re-evalúa si hubo cambios.

| Entidad | Criterio de cambio | Campo fecha en Adminet |
|---------|-------------------|------------------------|
| **Producto** | `articulo.fecha_mod` > `ProductMapping.adminet_fecha_mod` | Sí (`fecha_mod`) |
| **Precio/costo** | `tiendanube_price` / `tiendanube_cost` del mapeo ≠ valores calculados (`precios_tiendanube_desde_articulo`) | Cubierto por `fecha_mod` en la mayoría de casos |
| **Stock** | `adminet_stock` del mapeo ≠ unidades disponibles del depósito TN | No (`stock_deposito` no tiene fecha) |
| **Cliente → TN** | Comparación de nombre, email, CUIT, teléfono, dirección, `cliente_ecommerce` | No |
| **Cliente ← TN** | `updated_at` de TN > `CustomerMapping.tiendanube_updated_at` | N/A (origen TN) |

Helper: `tiendanube_administranet/services/sync_change_detection.py`.

Tras cada push exitoso, `_finalize_product_sync_success` persiste snapshot (`adminet_fecha_mod`, precios TN, stock). Parámetro opcional `force=True` en sync masiva para ignorar detección.

### Detalle de producto en Synap (`/products/<id>/`)

La columna **Tiendanube** no consultaba la API en vivo: mostraba solo lo guardado en `ProductMapping`. Además, precio/stock/handle en la API **2025-03** están en la **variante**, no en la raíz del producto; el mapeo leía `product.stock` / `product.price` (siempre vacío → stock 0, handle N/A).

- Al abrir el detalle, si hay `tiendanube_id`, se hace `GET /products/{id}` y se actualiza el snapshot (`tiendanube_product_fields.py`).
- Tras sync Adminet→TN, `_finalize_product_sync_success` guarda también `tiendanube_stock`, nombre y SKU publicados.

## Tests

```bash
docker exec Synap_app python manage.py test \
  tiendanube_administranet.tests.test_product_pricing \
  tiendanube_administranet.tests.test_product_stock \
  tiendanube_administranet.tests.test_sync_change_detection
```
