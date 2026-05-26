-- Corrige los 3 registros de cuentacliente (Self-Checkout) sin Vencimiento ni Estado.
-- Ejecutar manualmente en el servidor MySQL de la base administraNET.
--
-- Valores aplicados (contado = Mercado Pago):
--   Vencimiento = fecha del comprobante (misma que Fecha)
--   Vencido = 'No'
--   Estado = 'Canc'
--   CondVenta = 'Contado'
--   id_condventa = 1

-- Opción A: Si Fecha es tipo DATE o DATETIME
UPDATE cuentacliente
SET
  Vencimiento = DATE(Fecha),
  Vencido = 'No',
  Estado = 'Canc',
  CondVenta = 'Contado',
  id_condventa = 1
WHERE id_cuentacliente IN (10764, 10765, 10766)
  AND (Vencimiento IS NULL OR Vencimiento = '' OR TRIM(Vencimiento) = '');

-- ----------
-- Si Fecha es VARCHAR con formato 'dd/mm/yyyy hh:mi:ss', usar en su lugar:
--
-- UPDATE cuentacliente
-- SET
--   Vencimiento = STR_TO_DATE(LEFT(Fecha, 10), '%d/%m/%Y'),
--   Vencido = 'No',
--   Estado = 'Canc',
--   CondVenta = 'Contado',
--   id_condventa = 1
-- WHERE id_cuentacliente IN (10764, 10765, 10766)
--   AND (Vencimiento IS NULL OR Vencimiento = '' OR TRIM(Vencimiento) = '');
--
-- ----------

-- Verificación (ejecutar después del UPDATE):
-- SELECT id_cuentacliente, Fecha, Vencimiento, Vencido, Estado, CondVenta, id_condventa
-- FROM cuentacliente
-- WHERE id_cuentacliente IN (10764, 10765, 10766);
