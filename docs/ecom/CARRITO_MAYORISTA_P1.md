# Carrito mayorista — Fase P1

**Change SDD:** `catalogo-carrito-checkout-mayorista`
**Origen legacy:** `administraNET-ecom/mayoristapp/jcart/jcart.php` (clase `Jcart`, `$_SESSION['jcart']`), `carrito.js`, `ajax-calcula-precio.php`.
**Alcance P1:** carrito **borrador** con precio y totales. **Sin** escritura a MySQL legacy (el alta de comprobante llega en P2).

---

## 1. Decisión de arquitectura

- **Persistencia:** modelos Django `EcomCart` / `EcomCartItem` en la base **Postgres `synap`** (no se reutiliza `self_checkout_cart`, que es MySQL y está acoplado al TPV/kiosco). Esto da migraciones versionadas, ORM y tests sin depender de MySQL.
- **Precio:** fuente única `ecom.services.catalogo_producto.resolver_precio_articulo` → motor `price_rules_engine.calcular_precio_articulo_row`. Garantiza que el precio del carrito sea **idéntico** al del catálogo (Fase P0). El precio se resuelve **server-side**: la API nunca confía en un precio enviado por el cliente.
- **Stock:** `self_checkout.services.stock_service.StockService` (disponible = `max(0, saldo − saldo_pedido_cliente)`), sin duplicar lógica.
- **Autoridad:** el carrito es un borrador; el **checkout (P2) recalcula** precios y stock en la transacción de commit.

## 2. Modelo de datos (Postgres)

`EcomCart` (uno en estado `borrador` por `base_empresa` + `id_usuario`):

- Contexto: `base_empresa`, `id_usuario` (vendedor), `idcliente`, `lista_id`, `id_deposito`, `iva_incluido`, `tipo_comprobante` (`PED`/`PRE`), `estado`, `descuento_pie_pct`.
- Totales denormalizados: `neto_gravado_21`, `neto_gravado_105`, `iva_21`, `iva_105`, `exento`, `impuesto_interno_total`, `subtotal_neto`, `total`.

`EcomCartItem` (un renglón por artículo — `UniqueConstraint(cart, id_articulo)`):

- `id_articulo`, `codigo`, `id_manual`, `descripcion`, `cantidad`, `precio_unitario_neto`, `alicuota_iva`, `impuesto_interno_pct`, `porcentaje_descuento`, `lista_id`, datos de promoción, `orden`.
- Totales del renglón (con descuento de renglón, **antes** del descuento al pie): `neto`, `iva`, `total`.

Migración: `ecom/migrations/0015_ecomcart_ecomcartitem_and_more.py`.

## 3. Reglas de negocio

- **Un carrito por vendedor:** al pedir el carrito se obtiene el borrador o se crea. Al **cambiar el cliente** seleccionado, el carrito se **vacía** (paridad `session.pop("jcart")`).
- **Agregar / consolidar:** si el artículo ya está, se suma la cantidad en el mismo renglón. Se valida stock con la **cantidad total** del artículo.
- **Descuento de renglón** (`porcentaje_descuento`, 0–100) sobre el neto; el IVA se recalcula sobre el neto con descuento.
- **Descuento al pie** (`descuento_pie_pct`, 0–100): se aplica sobre el neto **por alícuota** y luego se recalcula el IVA (paridad `Jcart.update_subtotal`).
- **Desglose de totales:** neto e IVA separados para 21 % y 10,5 %, subtotal exento (alícuota 0), impuesto interno total y `total` final. Otras alícuotas se computan correctamente en el `total` (y en `iva_total` serializado).
- **Decimales:** `Decimal` en todos los cálculos, cuantización a 2 decimales (`ROUND_HALF_UP`).

## 4. API

Base: `/ecom/api/mayoristapp/carrito/` · Permiso: `EcomMayoristappSessionPermission`.

| Método | Ruta | Acción |
|---|---|---|
| GET | `carrito/` | Obtiene (o crea) el carrito activo del vendedor |
| POST | `carrito/` | Agrega ítem. Body: `{id_articulo, cantidad}` |
| PATCH | `carrito/items/<item_id>/` | Actualiza `cantidad` y/o `porcentaje_descuento` |
| DELETE | `carrito/items/<item_id>/` | Quita el renglón |
| POST | `carrito/vaciar/` | Vacía el carrito |
| POST | `carrito/descuento-pie/` | Aplica descuento al pie. Body: `{porcentaje}` |

Respuesta: carrito serializado (`items[]` + `totales{}`). Stock insuficiente devuelve **409** con el carrito actual; validaciones de entrada, **400**; errores internos, **500** con mensaje genérico (sin filtrar detalles).

## 5. Archivos

- `ecom/models.py` — `EcomCart`, `EcomCartItem`.
- `ecom/services/mayorista_cart_service.py` — lógica del carrito y totales.
- `ecom/services/catalogo_producto.py` — `obtener_articulo_row_precio`, `resolver_precio_articulo` (fuente única de precio para carrito y checkout).
- `ecom/carrito_relay_views.py` — vistas API.
- `ecom/urls.py` — rutas.
- `ecom/tests/test_mayorista_cart_service.py` — 15 tests.

## 6. Tests

`docker exec Synap_app python manage.py test ecom.tests.test_mayorista_cart_service --noinput --keepdb` → **15/15 OK**.

Cobertura: creación/reuso de carrito, reinicio por cambio de cliente, alta con precio del motor, stock insuficiente, consolidación de renglón, cantidad ≤ 0, actualización de cantidad con revalidación de stock, descuento de renglón, quitar ítem, desglose de dos alícuotas, descuento al pie, ítem exento, impuesto interno, serialización.

## 7. Pendiente para P2 (checkout)

- Escritura legacy transaccional (`comp_ped`, `stockp`, `stock_deposito`, `talonarios`, `codmov`, `percep_cli`, `cliente_datos_adicionales`).
- Numeración segura (`talonarios` con `FOR UPDATE`), validación de crédito, idempotencia, recálculo de precios en commit y selección de punto de venta.
