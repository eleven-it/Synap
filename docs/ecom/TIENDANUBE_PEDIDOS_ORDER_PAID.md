# Pedidos Tiendanube — `order/paid`

Flujo TN → AdministraNET para órdenes ya pagadas en la tienda online.

## Disparador

- Webhook **`order/paid`** (único alta de pedido en Adminet).
- Se enriquece la orden con **`GET /orders/{id}`** para obtener `payment_details`, `gateway_id`, `gateway_name`, `paid_at`, etc.

## Alta en AdministraNET

| Campo / tabla | Valor |
|---------------|--------|
| `comp_ped.Estado` | `En preparación` (paridad VB6 / e-commerce legacy) |
| `comp_ped.estado_pago_ecom` | `Si` |
| `comp_ped.TipoPedido` | `Ecom cliente` |
| `comp_ped.id_tiendanube` / `ped_eco` | ID / número TN |
| `comp_ped.info_ped_eco` | JSON con envío, cliente y **pago TN** |
| `stockp` + `stock_deposito` | Reserva: `saldo_pedido_cliente += cantidad` en **depósito TN** |

Idempotencia: si ya existe `comp_ped` con `id_tiendanube`, no se duplica.

## Adelanto (fase 2 — REC a cuenta)

Cuando el pago está confirmado (`payment_status` ∈ `paid`, `authorized`, `partially_paid`):

1. **`cuentacliente`** — REC `TipoRecibo='A Cuenta'`, `Detalle='TN-WEB'`.
2. **`recibo_factura`** + **`recibo_factura_par`** — saldo a favor del cliente (imputable al facturar).
3. **`caja`** — ingreso según medio inferido de TN:
   - tarjeta / Mercado Pago → caja tarjeta del usuario (`usuarios.id_caja_tarjeta`)
   - transferencia → caja efectivo, tipo `Transferencia`
   - efectivo → caja efectivo, tipo `Cobranza Efectivo`
4. **`cliente.saldo`** — actualizado como en `json_recibo.php`.

Servicios: `order_payment.py`, `adelanto_recibo_service.py`.

### Datos de pago que envía Tiendanube

| Campo API | Uso |
|-----------|-----|
| `payment_status` | Confirmación de cobro |
| `payment_details.method` | Etiqueta / clasificación medio |
| `payment_details.credit_card_company` | Info en `info_ped_eco` |
| `payment_details.installments` | Cuotas |
| `gateway`, `gateway_id`, `gateway_name` | Pasarela e ID transacción externo |
| `gateway_method` | `credit_card`, `wire_transfer`, `cash`, etc. |
| `paid_at` | Fecha de pago |
| `total` | Importe del adelanto |

Opcional futuro: `GET /orders/{id}/transactions` para detalle fino de la pasarela.

## Stock hacia Tiendanube

- **Disponible publicado:** `max(0, saldo - saldo_pedido_cliente)` del `deposito_tiendanube_id`.
- Tras crear el pedido: **push inmediato** `PATCH /products/stock-price` solo para artículos afectados (`order_stock_push.py`).

## Configuración requerida

- Migración MySQL: `verify_and_migrate_schema()` añade `id_tiendanube` en `cliente`, `articulo` y **`comp_ped`** (`core/services/legacy_mysql_schema/catalog.py`).
- `AdministraNETConfig.deposito_tiendanube_id`
- `punto_venta_tiendanube_id` (talonario REC)
- `sucursal_tiendanube_id`
- Usuario operativo (hoy `id_usuario=1`) con **cajas** en `usuarios` (`id_caja`, `id_caja_tarjeta`)
- Talonario REC en `talonarios` para el PV
- Fila `codmov` con `codigo=1`

## Pendiente

- Imputación automática del adelanto al facturar desde el pedido TN.
- Sync periódico Adminet → TN de estados de pedido (fulfillment).

## Tests

```bash
docker exec Synap_app python manage.py test \
  tiendanube_administranet.tests.test_order_payment \
  tiendanube_administranet.tests.test_product_stock
```
