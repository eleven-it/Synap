-- Alinea los 3 comprobantes de cuentacliente creados por Self-Checkout con los
-- mismos campos que graba el TPV VB6 (y que desde ahora persiste confirmation_service).
--
-- IDs de los 3 comprobantes (los mismos que en fix_cuentacliente_vencimiento_estado.sql):
--   10764, 10765, 10766
--
-- Ejecutar en la base administraNET (MySQL). Si alguna columna no existe, comentar
-- la línea correspondiente o añadirla a la tabla antes de ejecutar.

-- 1) Saldo desde cliente, total_costo desde stock, id_deposito_despacho desde carrito
UPDATE cuentacliente cc
LEFT JOIN cliente cl ON cl.codigo = cc.Codigo
LEFT JOIN self_checkout_cart c ON c.id_cuentacliente = cc.id_cuentacliente
LEFT JOIN (
  SELECT CodigoMovimiento, SUM(COALESCE(PrecioCostoxR, 0)) AS tot
  FROM stock
  GROUP BY CodigoMovimiento
) st ON st.CodigoMovimiento = cc.CodigoMovimiento
SET
  cc.ReciboMov = 0,
  cc.ImporteCobro = NULL,
  cc.Saldo = COALESCE(cl.saldo, 0),
  cc.Alicuota1 = 21,
  cc.alicuota2 = 0,
  cc.Exento = 0,
  cc.Subtotal1 = cc.ImporteVenta - COALESCE(cc.Iva1, 0),
  cc.Subtotal2 = 0,
  cc.SubtotalGral = COALESCE(cc.ImporteVenta, 0),
  cc.PorDesc1 = 0,
  cc.ImpDesc1 = 0,
  cc.ImpDesc2 = 0,
  cc.SubTotalDesc1 = COALESCE(cc.SubtotalDesc, cc.ImporteVenta - COALESCE(cc.Iva1, 0)),
  cc.SubTotalDesc2 = 0,
  cc.idUsuario = 0,
  cc.TipoFactura = 'Sistema',
  cc.Detalle = COALESCE(cc.Detalle, ''),
  cc.Vencimiento = DATE(cc.Fecha),
  cc.Vencido = 'No',
  cc.Estado = 'Canc',
  cc.CondVenta = 'Contado',
  cc.id_condventa = 1,
  cc.tpv_importe_efectivo = 0,
  cc.tpv_importe_tarjeta = COALESCE(cc.ImporteVenta, 0),
  cc.tpv_importe_cheque = 0,
  cc.tpv_importe_ctacte = 0,
  cc.id_vendedor_asistente = 0,
  cc.impuesto_interno_total = 0,
  cc.total_percep = 0,
  cc.id_deposito_despacho = c.id_deposito,
  cc.CotiDolar = 0,
  cc.total_costo = COALESCE(st.tot, 0)
WHERE cc.id_cuentacliente IN (10764, 10765, 10766);
-- (Monto_Devol no existe en esta tabla; omitido.)

-- 2) Si la PK de cuentacliente es 'id' (y el carrito guarda ese valor en id_cuentacliente):
--    cambiar JOIN a: LEFT JOIN self_checkout_cart c ON c.id_cuentacliente = cc.id
--    y WHERE a: WHERE cc.id IN (10764, 10765, 10766);

-- Verificación (ejecutar después):
-- SELECT cc.id_cuentacliente, cc.CodigoMovimiento, cc.Fecha, cc.ImporteVenta, cc.SubtotalDesc,
--        cc.Vencimiento, cc.Vencido, cc.Estado, cc.CondVenta, cc.id_condventa,
--        cc.ReciboMov, cc.Saldo, cc.Subtotal1, cc.SubtotalGral, cc.TipoFactura,
--        cc.tpv_importe_tarjeta, cc.total_costo, cc.id_deposito_despacho
-- FROM cuentacliente cc
-- WHERE cc.id_cuentacliente IN (10764, 10765, 10766);
