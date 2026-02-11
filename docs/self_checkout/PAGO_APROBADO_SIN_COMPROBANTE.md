# Pago aprobado sin comprobante emitido

## Listado unificado "Carritos pagados sin comprobante"

La pantalla **Self-Checkout → Configuración → Carritos pendientes** muestra un listado detallado con columnas: Nro carrito, Estado, Autoservicio, Total, Nro factura (si existe), Forma de pago. **Un solo botón principal** por carrito según la tarea pendiente:

| Estado carrito   | Acción del botón |
|------------------|------------------|
| `confirmado` con factura | **Reimprimir** ticket/factura |
| `pago_aprobado` (pago MP sincronizado) | **Emitir comprobante** |
| `error_confirmacion` | **Reintentar** emisión |
| `pago_pendiente` / `borrador` sin pago local | **Buscar pago en MP** → si hay match → emitir comprobante |
| `borrador` (abandonado) | **Eliminar** |

### Carritos borrador

- Un carrito en `borrador` puede estar **abandonado** (cliente se fue sin pagar). Debe poder **eliminarse**.
- Un `borrador` puede **recuperarse en el autoservicio** para modificar, eliminar o agregar ítems; el proceso continúa desde el mismo autoservicio.

### Vinculación carrito–pago MP (external_reference)

La relación carrito–pago se establece con `external_reference = "cart_{cart_id}_pi_{payment_intent_id}"`. Cada pago en MP está asociado a un único carrito. Se usa en `sincronizar_pagos_desde_mp` para buscar pagos aprobados en MP y actualizar el carrito a `pago_aprobado`.

---

## Condiciones para aparecer (pago aprobado sin comprobante)

Los carritos en `pago_aprobado` sin comprobante cumplen:

1. **`self_checkout_cart.estado = 'pago_aprobado'`**
2. **Al menos un `self_checkout_payment_intent` con `estado = 'aprobado'`** (cobro confirmado en Mercado Pago).
3. **`created_at`** en los últimos 90 días.

El estado `pago_aprobado` también puede setearse por el **stub** en `cart_confirm` (cuando el carrito está en `pago_pendiente` y se intenta confirmar). Si la confirmación falla (ej. error AFIP), el carrito queda en `pago_aprobado` pero **sin** comprobante emitido.

## Qué pasa

Cuando el cliente **ya pagó** en Mercado Pago (QR o dispositivo físico) pero **no se llegó a emitir el comprobante** en Synap, el carrito queda en uno de estos estados:

| Estado carrito   | Significado |
|------------------|-------------|
| `pago_aprobado`  | Mercado Pago marcó el pago como aprobado; el flujo de confirmación no se completó (error de red, cierre del navegador, fallo AFIP, etc.). |
| `pago_pendiente` | En algunos flujos el pago se aprobó en MP pero el backend no actualizó el carrito a `pago_aprobado` (ej. webhook no llegó). |
| `borrador`       | Carrito sin pagar; puede estar abandonado o recuperarse en el autoservicio para continuar. |

**Consecuencias (para pago_aprobado / pago_pendiente con pago real):**

- El dinero **sí** fue cobrado por Mercado Pago.
- En Synap **no** se generó:
  - Comprobante (factura/ticket)
  - Registro en `cuentacliente`
  - Movimiento de stock
  - Código de movimiento (codmov)
  - Inscripción en caja (si aplica)

Es decir: **cobro en MP sin venta registrada en administraNET**.

## Cómo recuperar

### 1. Reintentar confirmación por comando (recomendado)

Hay un comando que lista carritos en `pago_aprobado` y reintenta la confirmación (emite comprobante, stock, cuentacliente, etc.):

```bash
# Listar carritos pagados sin confirmar (solo muestra, no confirma)
python manage.py self_checkout_confirm_pending --base-empresa NOMBRE_BASE --dry-run

# Reintentar confirmación (emite comprobante para cada uno)
python manage.py self_checkout_confirm_pending --base-empresa NOMBRE_BASE

# Limitar cantidad y/o días
python manage.py self_checkout_confirm_pending --base-empresa NOMBRE_BASE --limit 20 --days 7
```

- Solo se procesan carritos en estado **`pago_aprobado`** (no se tocan `pago_pendiente` sin evidencia de pago).
- La confirmación es **idempotente**: si un carrito ya está `confirmado`, no se duplica.
- Si falla AFIP (CAE/CAEA), ese carrito no pasa a `confirmado`; se puede volver a ejecutar el comando más tarde.

### 2. Reintentar desde la API (un carrito concreto)

Un supervisor puede llamar al endpoint de confirmación con el `cart_id` del carrito pagado sin comprobante:

```http
POST /api/self-checkout/cart/<cart_id>/confirm/
Content-Type: application/json

{
  "email": "cliente@email.com",
  "id_cliente": 1,
  "cuit": ""
}
```

- Requiere sesión con permiso de self-checkout (kiosk/supervisor).
- El carrito debe estar en `pago_aprobado` (o en `pago_pendiente` con el stub que lo pasa a `pago_aprobado` y confirma).
- Si el carrito ya está `confirmado`, la API responde éxito sin duplicar.

### 3. Recuperar borrador en autoservicio

Un carrito en `borrador` puede **recuperarse en el autoservicio** para modificar, eliminar o agregar ítems. El cliente vuelve al mismo kiosco con la URL del autoservicio incluyendo el `cart_id`; el proceso continúa desde ahí (pagar, confirmar).

### 4. Revisar logs

En el log del servidor podés ver:

- `cart_confirm: carrito X en pago_pendiente, pasando a pago_aprobado para confirmar` → se está confirmando un carrito que estaba en pago_pendiente.
- `cart_confirm: carrito X confirmado ok, cod_mov=... nro_comp=...` → confirmación exitosa.

Si no aparece el segundo mensaje después del primero, el fallo está dentro de la confirmación (stock, AFIP, etc.).

## Prevención

- Con los cambios de **auto-confirmación** en el kiosco, al detectar pago aprobado (QR o dispositivo) se llama solo a confirmar y se emite el comprobante sin depender del clic en "Confirmar compra".
- Asegurar que el módulo Mercado Pago actualice el carrito a `pago_aprobado` cuando el pago esté aprobado (webhook o al consultar el estado del order/point).
