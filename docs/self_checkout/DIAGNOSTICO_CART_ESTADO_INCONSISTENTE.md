# Diagnóstico: Carrito con comprobante emitido pero estado "Pendiente"

## Problema

Un carrito (ej. 121) aparece como "Pendiente" (pago_aprobado) con botón "Emitir comprobante", aunque el usuario ya emitió el comprobante, AFIP otorgó CAE e imprimió. Hay inconsistencia entre el estado del carrito y los datos reales.

## Dónde se actualiza el estado

El flujo normal en `ConfirmationService.confirmar()`:

1. **Línea 416-425** (`confirmation_service.py`): `UPDATE self_checkout_cart SET estado = 'confirmado', codigo_movimiento = ..., id_cuentacliente = ..., confirmed_at = NOW() WHERE id = ?`
2. Luego emite FE (AFIP CAE/CAEA).
3. Si FE falla → `conn.rollback()` (el UPDATE se deshace).
4. Si FE tiene éxito → `conn.commit()` (el UPDATE queda aplicado).

Si AFIP dio CAE y se imprimió, el `confirmar()` debería haber hecho `commit` y el carrito debería estar en `confirmado`. La tabla `self_checkout_invoice` se llena después, desde `api_views` (`guardar_invoice`), cuando `confirmar()` ya retornó ok.

## Posibles causas de inconsistencia

1. **Otra conexión/transacción**: `confirmar()` usa una conexión MySQL propia; si hubo fallo después del commit (p. ej. en `guardar_invoice` o en otra parte), el carrito ya habría quedado en `confirmado` porque el commit ocurrió dentro de `confirmar()`.

2. **Emisión fuera de Synap**: Si el comprobante se emitió desde administraNET VB6 u otro sistema, ese flujo no actualiza `self_checkout_cart`. Pero en ese caso tampoco se crearían filas en `self_checkout_invoice`, salvo que se haya hecho algo manual.

3. **Actualización manual posterior**: Algún script o usuario ejecutó `UPDATE self_checkout_cart SET estado = 'pago_aprobado'` después de la confirmación.

4. **Múltiples bases de datos**: Que la vista lea de una base y la confirmación escriba en otra (por ejemplo réplica desfasada).

## Consultas de diagnóstico

Ejecutá en la base de la empresa (MySQL, base_empresa):

```sql
-- 1. Estado actual del carrito 121
SELECT id, estado, codigo_movimiento, id_cuentacliente, tipo_comprobante, 
       confirmed_at, created_at, total
FROM self_checkout_cart 
WHERE id = 121;

-- 2. Invoice asociada (si existe)
SELECT id, cart_id, codigo_movimiento, id_cuentacliente, nro_comprobante, 
       tipo_comprobante, estado, cae, vto_cae
FROM self_checkout_invoice 
WHERE cart_id = 121;

-- 3. Cuentacliente (comprobante emitido)
SELECT id_cuentacliente, codigo_movimiento, Codigo_Cliente, NroComprobante, 
       TipoComprobante, fe_cae, fe_transmitido
FROM cuentacliente 
WHERE codigo_movimiento IN (
  SELECT codigo_movimiento FROM self_checkout_cart WHERE id = 121
  UNION
  SELECT codigo_movimiento FROM self_checkout_invoice WHERE cart_id = 121
);

-- 4. Audit log de confirmación
SELECT id, cart_id, accion, detalle, created_at
FROM self_checkout_audit_log 
WHERE cart_id = 121
ORDER BY created_at DESC
LIMIT 5;
```

## Qué esperar

- Si `self_checkout_cart.estado = 'pago_aprobado'` y `self_checkout_invoice` tiene fila para ese cart → **inconsistencia confirmada**.
- Si `cuentacliente` tiene el comprobante y `cae` → el flujo de emisión ya corrió; solo falta alinear el estado del carrito.

## Corrección

Si la inconsistencia está confirmada (invoice existe, cuentacliente tiene comprobante, cart sigue en `pago_aprobado`), corregí con:

```sql
-- Corregir estado del carrito 121 (reemplazá 121 por el cart_id correcto)
UPDATE self_checkout_cart sc
INNER JOIN self_checkout_invoice si ON si.cart_id = sc.id
SET sc.estado = 'confirmado',
    sc.codigo_movimiento = si.codigo_movimiento,
    sc.id_cuentacliente = si.id_cuentacliente,
    sc.tipo_comprobante = si.tipo_comprobante,
    sc.confirmed_at = COALESCE(sc.confirmed_at, NOW())
WHERE sc.id = 121 AND sc.estado != 'confirmado';
```

Script genérico para corregir todos los carritos inconsistentes:

```sql
-- Corregir todos los carritos que tienen invoice pero estado distinto de confirmado
UPDATE self_checkout_cart sc
INNER JOIN self_checkout_invoice si ON si.cart_id = sc.id
SET sc.estado = 'confirmado',
    sc.codigo_movimiento = si.codigo_movimiento,
    sc.id_cuentacliente = si.id_cuentacliente,
    sc.tipo_comprobante = si.tipo_comprobante,
    sc.confirmed_at = COALESCE(sc.confirmed_at, NOW())
WHERE sc.estado != 'confirmado';
```

Ejecutá primero las consultas de diagnóstico y, si coinciden con la inconsistencia descrita, aplicá el UPDATE correspondiente.
