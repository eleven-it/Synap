# Integración de caja al autoservicio (administraNET)

Análisis de la situación actual, gaps y propuesta para que el autoservicio siga los procesos internos de caja de administraNET, sin cajero físico.

---

## 1. Situación actual

### 1.1 Flujo actual del autoservicio (resumen)

1. **Carrito** → usuario escanea/agrega ítems → `self_checkout_cart`, `self_checkout_cart_item`.
2. **Pago** → usuario elige “Pagar con MercadoPago” → se crea `self_checkout_payment_intent` → redirect a MP → pago aprobado.
3. **Webhook MP** → actualiza `mercadopago_transaction`, `self_checkout_payment_intent` (estado aprobado), `self_checkout_cart` (estado `pago_aprobado`). **No se escribe en `caja` ni se actualiza `caja_saldo`** (el comentario en código indica que eso se haría “tras confirmación”).
4. **Confirmación** → usuario vuelve al kiosco, ingresa email y hace clic en “Confirmar compra” → `cart_confirm` → `ConfirmationService.confirmar()`:
   - Obtiene `CodigoMovimiento` (codmov), reserva `NroComprobante` (talonarios).
   - INSERT en `cuentacliente`, `stock`, UPDATE `self_checkout_cart` (estado `confirmado`, `codigo_movimiento`, `id_cuentacliente`), audit_log.
   - **No se llama a `write_caja_ingreso`** en ningún punto: el movimiento de caja para el cobro MP nunca se registra.

### 1.2 Flujo de caja en administraNET (TPV con cajero)

- Usuario tiene asignada una caja (y opcionalmente caja tarjeta/cheque): `usuarios.id_caja`, `id_caja_tarjeta`, `id_caja_cheque`.
- Al confirmar una venta en TPV:
  1. Se abre `caja_saldo` para la caja correspondiente (efectivo/tarjeta/cheque) y moneda (Pesos/Dolar).
  2. Se actualiza **caja_saldo**: `Saldo = Saldo + ingreso` (o `- egreso` en anulaciones).
  3. Se INSERT en **caja**: `codigo_movimiento`, `id_caja_abm_origen`, `ingreso`/`egreso`, `Saldo` (saldo resultante), `id_usuario`, `cod_vendedor`, `Codigo_Cliente`, `nro_comprobante`, `tipo` ('Factura Contado TPV', 'Tarjeta', etc.), `tipo_cp` = 'Cliente', `cod_sucursal`, etc.

Conclusión: hoy el autoservicio **no integra con caja**: no se escribe en `caja` ni se actualiza `caja_saldo`, por lo que reportes de caja, arqueos y control por sucursal no incluyen las ventas del kiosco.

---

## 2. Gaps a cubrir

### 2.1 Momento y lugar de la escritura en caja

- **Gap:** `write_caja_ingreso` existe pero **nunca se invoca**.
- **Solución:** Llamar a `write_caja_ingreso` **después de una confirmación exitosa** en `cart_confirm`, cuando ya existen `codigo_movimiento`, `nro_comprobante`, `id_cuentacliente` y total. Usar la config MercadoPago del kiosco (por `kiosk_id` del carrito) para obtener `id_caja_abm`; si no hay caja configurada, no escribir (comportamiento opcional ya existente).

### 2.2 Actualización de `caja_saldo`

- **Gap:** En VB6 cada movimiento de caja va acompañado de un UPDATE de `caja_saldo` (Saldo += ingreso o -= egreso). La función actual solo hace INSERT en `caja` y **no toca `caja_saldo`**, por lo que el saldo de la caja queda desactualizado.
- **Solución:** Dentro de `write_caja_ingreso` (o en un servicio compartido):
  1. Obtener el registro de `caja_saldo` para `id_caja_abm` y moneda (por defecto 'Pesos').
  2. Calcular nuevo saldo: `Saldo = Saldo + importe`.
  3. UPDATE `caja_saldo` con el nuevo `Saldo`.
  4. INSERT en `caja` con ese mismo `Saldo` como campo `Saldo` del movimiento (alineado con VB6).

### 2.3 Campos del movimiento de caja (alinear con VB6)

- **nro_comprobante / nro_comp_busq:** Hoy se envía `str(codigo_movimiento)`. Debe usarse el **nro_comprobante** real del comprobante (ej. "00001234") y, si aplica, `nro_comp_busq` para búsquedas.
- **Codigo_Cliente:** VB6 guarda el cliente del comprobante. Pasar `codigo_cliente` (id_cliente del confirm) en el INSERT de `caja`.
- **tipo_comprobante:** VB6 usa el tipo de factura (ej. 'FB', 'FA'). Conviene guardar el `tipo_comprobante` del comprobante en el movimiento de caja.
- **Moneda:** Fijar 'Pesos' (o parámetro) y usarlo tanto en el UPDATE de `caja_saldo` como en el INSERT de `caja`.
- **Saldo:** Rellenar con el saldo **después** del movimiento (igual que en VB6), calculado tras actualizar `caja_saldo`.

### 2.4 Usuario cajero lógico (autoservicio)

- **Contexto:** En TPV, cada movimiento de caja lleva `id_usuario` y `cod_vendedor` del cajero. En autoservicio **no hay un usuario logueado** en el kiosco.
- **Solución adoptada:** Usar un **usuario lógico configurable** que se da de alta como cajero en administraNET y se **asocia a autoservicio** en Synap:
  1. En administraNET (VB6) se crea un usuario dedicado (ej. "AUTOSERVICIO", "Kiosk") y se lo configura como cajero (asignación de caja, puesto, etc.).
  2. En Synap, en la configuración de MercadoPago, se elige ese usuario en el dropdown **"Usuario cajero (autoservicio)"**, que lista los usuarios activos de la base.
  3. Todos los movimientos de caja generados por el autoservicio usan ese `id_usuario` (y opcionalmente `cod_vendedor`), de modo que reportes y auditoría filtran o agrupan por ese cajero lógico.
- Si no se selecciona usuario, los movimientos se registran con `id_usuario`/`cod_vendedor` NULL (si la base lo permite).

### 2.5 Config por kiosco para caja

- **Gap:** Para llamar a `write_caja_ingreso` desde `cart_confirm` hace falta saber **qué caja** usar. La caja ya está en la config MercadoPago (`id_caja_abm`), pero debe resolverse por **kiosco** (carrito tiene `kiosk_id`).
- **Solución:** En `cart_confirm`, leer `kiosk_id` (y `id_sucursal`) del carrito, obtener la config con `get_config_for_kiosk(base_empresa, kiosk_id)` y, si la config tiene `id_caja_abm`, llamar a `write_caja_ingreso` con ese `id_caja_abm`, el `codigo_movimiento` y datos del resultado de confirmación (total, nro_comprobante, tipo_comprobante, codigo_cliente).

### 2.6 Idempotencia y doble escritura

- **Riesgo:** Si el usuario confirma dos veces o hay reintentos, podría intentarse escribir dos veces el mismo cobro en caja.
- **Solución:** La confirmación ya es idempotente (si el carrito está `confirmado`, se devuelve el resultado existente sin volver a generar codigo_movimiento ni cuentacliente). Escribir caja **solo cuando se confirma por primera vez** (cuando `confirmar()` realmente genera un nuevo `codigo_movimiento`). No escribir caja en el camino “ya confirmado” de confirmar (donde solo se retorna el resultado previo). Así se evita duplicar movimientos de caja.

### 2.7 Tipo de movimiento y moneda

- **Tipo:** Para pagos con MercadoPago usar `tipo` = 'Tarjeta' (o 'Factura Contado TPV' si se quiere homogeneizar con TPV; hoy en VB6 “Factura Contado TPV” es venta contado y “Tarjeta” es pago con tarjeta; para MP es coherente “Tarjeta”).
- **Moneda:** Usar 'Pesos' por defecto y el mismo valor en `caja_saldo` y en el registro de `caja`.

---

## 3. Usuario cajero lógico (sin cajero físico)

- **Regla:** Usar un **usuario dado de alta como cajero en administraNET y asociado a autoservicio** en Synap. Ese usuario actúa como “cajero lógico” para todos los movimientos de caja del kiosco.
- **Implementación:**
  1. **Alta en administraNET:** Se crea un usuario (ej. cod_usuario "AUTOSERVICIO", nombre "Autoservicio") y se lo configura como cajero (asignación de caja, puesto, sucursal, etc.) en CargaUsuario/ABM Usuarios.
  2. **Configuración en Synap:** En MercadoPago → Configuración, el campo **"Usuario cajero (autoservicio)"** es un **dropdown** que lista los usuarios activos de la base; se elige el usuario cajero asociado a autoservicio. Opcionalmente se puede indicar **"Cod. vendedor caja (autoservicio)"**.
  3. **Caja por kiosco:** La caja donde se registra el ingreso es la configurada en MercadoPago (`id_caja_abm`), que puede ser una caja “Autoservicio” o “Tarjeta” compartida o por kiosco.
  4. Si no se selecciona usuario cajero, los movimientos se registran con `id_usuario`/`cod_vendedor` NULL (si la base lo permite).

Con esto, el autoservicio queda integrado al proceso de caja de administraNET (mismo modelo de datos y mismas reglas de saldo), usando un cajero lógico configurable.

---

## 4. Resumen de cambios a implementar

| # | Cambio | Dónde |
|---|--------|--------|
| 1 | Llamar a `write_caja_ingreso` después de confirmación exitosa, con datos del resultado y config por kiosk | `self_checkout/api_views.py` (`cart_confirm`) |
| 2 | En `write_caja_ingreso`: actualizar `caja_saldo` (Saldo += importe) y luego INSERT en `caja` con Saldo, nro_comprobante, nro_comp_busq, Codigo_Cliente, tipo_comprobante, Moneda | `mercadopago/services/payment_service.py` |
| 3 | Opcional: parámetro `id_usuario` (y `cod_vendedor`) para movimientos sin cajero; si se pasa, rellenar en INSERT caja; si no, NULL | `write_caja_ingreso` + config o settings |
| 4 | Opcional: campo en MercadoPagoConfig o settings para “Usuario caja autoservicio” (id_usuario) | `mercadopago/models.py` o `django_project/settings.py` |
| 5 | Obtener kiosk_id (e id_sucursal) del carrito en cart_confirm para resolver config y llamar write_caja_ingreso | `self_checkout/api_views.py` |

---

## 5. Orden sugerido de implementación

1. **write_caja_ingreso:** Añadir actualización de `caja_saldo` y ampliar el INSERT de `caja` con nro_comprobante, nro_comp_busq, Codigo_Cliente, tipo_comprobante, Moneda, Saldo; opcionalmente id_usuario/cod_vendedor.
2. **cart_confirm:** Tras confirmar con éxito, leer kiosk_id e id_sucursal del carrito, obtener config con `get_config_for_kiosk`, y si hay `id_caja_abm`, llamar `write_caja_ingreso` con codigo_movimiento, total, nro_comprobante, tipo_comprobante, codigo_cliente e id_sucursal.
3. **Config opcional:** Añadir en MercadoPagoConfig (o en settings) el id_usuario (y cod_vendedor si aplica) para “cajero autoservicio” y pasarlo a `write_caja_ingreso` cuando exista.

Con esto se cierra la integración del proceso de caja al autoservicio y se responde al caso “no hay cajero” usando un cajero lógico configurable o NULL.
