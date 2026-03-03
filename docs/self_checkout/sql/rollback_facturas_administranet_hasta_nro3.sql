-- =============================================================================
-- ROLLBACK FACTURAS ADMINISTRANET HASTA NRO 3
-- =============================================================================
-- Objetivo: Eliminar facturas 4, 5 y 6 y dejar talonario en Nro = 3, revirtiendo
-- cuentacliente, stock, stock_deposito, codmov y (opcional) self_checkout.
--
-- IMPORTANTE:
-- 1. Hacer BACKUP completo de la base antes de ejecutar.
-- 2. Ejecutar dentro de una transacción para poder hacer ROLLBACK si algo falla:
--    START TRANSACTION;
--    -- pegar aquí el cuerpo del script --
--    COMMIT;   (o ROLLBACK; si algo no cuadra)
-- 3. Reemplazar @id_punto_venta y @TipoComprobante por los valores reales
--    (ej. id_punto_venta del kiosco y 'FA' o 'FB').
-- 4. NroComprobante en cuentacliente se guarda con 8 dígitos: 00000004, 00000005, 00000006.
-- 5. En administraNET la PK de cuentacliente es id_cuentacliente (no "id").
-- 6. MySQL 5.7: ejecutar TODO el script en UNA SOLA SESIÓN (un solo batch), no consulta
--    por consulta, para que la tabla temporal exista en todos los pasos.
-- =============================================================================

-- Parámetros (reemplazar por valores reales)
SET @id_punto_venta = 1;        -- ID del punto de venta (ej. kiosco)
SET @TipoComprobante = 'FA';    -- 'FA' o 'FB'

-- -----------------------------------------------------------------------------
-- 1. Identificar facturas a revertir (Nros 4, 5, 6)
-- -----------------------------------------------------------------------------
DROP TEMPORARY TABLE IF EXISTS tmp_cc_rollback;
CREATE TEMPORARY TABLE tmp_cc_rollback AS
SELECT id_cuentacliente, CodigoMovimiento, NroComprobante
FROM cuentacliente
WHERE id_pv = @id_punto_venta
  AND TipoComprobante = @TipoComprobante
  AND NroComprobante IN ('00000004', '00000005', '00000006');

-- Verificación: ejecutar y comprobar que devuelve 3 antes de seguir
-- SELECT id_cuentacliente, CodigoMovimiento, NroComprobante FROM tmp_cc_rollback;
-- SELECT COUNT(*) AS cantidad_facturas_a_borrar FROM tmp_cc_rollback;  -- debe ser 3

-- -----------------------------------------------------------------------------
-- 2. Devolver stock: sumar Salida por (id_articulo, id_deposito) a stock_deposito
--    stock usa IDArt, CodDeposito; stock_deposito usa id_articulo, id_deposito
-- -----------------------------------------------------------------------------
UPDATE stock_deposito sd
INNER JOIN (
    SELECT s.IDArt AS id_articulo, s.CodDeposito AS id_deposito, SUM(s.Salida) AS suma_salida
    FROM stock s
    INNER JOIN tmp_cc_rollback t ON t.CodigoMovimiento = s.CodigoMovimiento
    WHERE s.Salida > 0
    GROUP BY s.IDArt, s.CodDeposito
) agg ON agg.id_articulo = sd.id_articulo AND agg.id_deposito = sd.id_deposito
SET sd.saldo = sd.saldo + agg.suma_salida;

-- -----------------------------------------------------------------------------
-- 3. Borrar registros de stock de esos movimientos
-- -----------------------------------------------------------------------------
DELETE s FROM stock s
INNER JOIN tmp_cc_rollback t ON t.CodigoMovimiento = s.CodigoMovimiento;

-- -----------------------------------------------------------------------------
-- 4. Borrar cuentacliente (facturas 4, 5, 6)
-- -----------------------------------------------------------------------------
DELETE FROM cuentacliente
WHERE id_cuentacliente IN (SELECT id_cuentacliente FROM tmp_cc_rollback);

-- -----------------------------------------------------------------------------
-- 5. Decrementar CodigoMovimiento en codmov (restar 3)
-- -----------------------------------------------------------------------------
UPDATE codmov SET CodigoMovimiento = CodigoMovimiento - 3 WHERE codigo = 1;

-- -----------------------------------------------------------------------------
-- 6. Dejar talonario en Nro = 3
-- -----------------------------------------------------------------------------
UPDATE talonarios
SET Nro = 3
WHERE id_punto_venta = @id_punto_venta AND TipoComprobante = @TipoComprobante;

-- -----------------------------------------------------------------------------
-- 7. (Opcional) Self-checkout: devolver carritos a pago_aprobado y limpiar FE
--    Solo si esas facturas vienen de self_checkout. Ajustar si no usáis estas tablas.
-- -----------------------------------------------------------------------------
-- Carritos que tenían id_cuentacliente en las facturas borradas
UPDATE self_checkout_cart sc
INNER JOIN tmp_cc_rollback t ON t.id_cuentacliente = sc.id_cuentacliente
SET
  sc.estado = 'pago_aprobado',
  sc.codigo_movimiento = NULL,
  sc.id_cuentacliente = NULL,
  sc.tipo_comprobante = NULL,
  sc.id_cliente = NULL,
  sc.email = NULL,
  sc.confirmed_at = NULL;

-- Borrar registros de factura FE asociados a esos carritos (por id_cuentacliente)
DELETE si FROM self_checkout_invoice si
WHERE si.id_cuentacliente IN (SELECT id_cuentacliente FROM tmp_cc_rollback);

-- Audit log: opcional borrar entradas 'confirmado' de esos cart_id
-- (si queréis dejar traza, no ejecutar el DELETE)
-- DELETE al FROM self_checkout_audit_log al
-- WHERE al.cart_id IN (SELECT cart_id FROM self_checkout_cart WHERE id_cuentacliente IS NULL AND estado = 'pago_aprobado' AND ...);
-- Mejor: no borrar audit_log para mantener historial.

-- -----------------------------------------------------------------------------
-- Limpieza
-- -----------------------------------------------------------------------------
DROP TEMPORARY TABLE IF EXISTS tmp_cc_rollback;

-- -----------------------------------------------------------------------------
-- Si solo aparece el error "Talonario próximo: 7, ARCA próximo: 4" y ya no hay
-- facturas 4/5/6 para borrar, basta con igualar el talonario a ARCA (próximo = 4):
-- -----------------------------------------------------------------------------
-- UPDATE talonarios SET Nro = 3
-- WHERE id_punto_venta = @id_punto_venta AND TipoComprobante = @TipoComprobante;
-- (Nro = 3 hace que el próximo número sea 4, que es lo que espera ARCA.)

-- =============================================================================
-- FIN ROLLBACK
-- =============================================================================
