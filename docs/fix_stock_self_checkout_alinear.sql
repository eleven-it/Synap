-- Rellena los campos vacíos en registros de stock creados por Self-Checkout,
-- necesarios para el correcto funcionamiento de administraNET.
-- TipoComp se deja en 'Venta Self Checkout'.
--
-- Afecta a los movimientos de stock de los 3 comprobantes (id_cuentacliente 10764, 10765, 10766).
-- Si tus comprobantes tienen otros ids, cambia la lista en el WHERE del JOIN con cuentacliente.

-- Orígenes (TPV VB6): imp_alicuota_iva e imp_alicuota_iibb = porcentajes (21, 3.5), no importes.
-- IVA: iva.Alicuota (porcentaje) si articulo.Alicuota = iva.id; si no, articulo.Alicuota. IIBB: articulo.AlicuotaIB.

UPDATE stock s
INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = s.CodigoMovimiento
  AND cc.id_cuentacliente IN (10764, 10765, 10766)
INNER JOIN articulo a ON a.IDArt = s.IDArt
LEFT JOIN iva ON iva.id = a.Alicuota
LEFT JOIN self_checkout_cart c ON c.id_cuentacliente = cc.id_cuentacliente
SET
  s.Fecha = DATE(cc.Fecha),
  s.CodigoArticulo = COALESCE(TRIM(a.id_manual), ''),
  s.Descripcion = COALESCE(TRIM(a.NombreArticulo), ''),
  s.Tipo = 'Cliente',
  s.TipoComp = 'Venta Self Checkout',
  s.Comprobante = COALESCE(cc.TipoComprobante, 'FB'),
  s.NroComprobante = CONCAT(LPAD(COALESCE(cc.id_pv, 0), 4, '0'), '-', COALESCE(cc.NroComprobante, '')),
  s.CodigoCP = COALESCE(cc.Codigo, 1),
  s.CodSucursal = COALESCE(cc.CodSucursal, 0),
  s.IdUsuario = 0,
  s.CodViajante = COALESCE(cc.CodViajante, 0),
  s.CodDeposito = COALESCE(c.id_deposito, s.CodDeposito),
  s.CodLaboratorio = COALESCE(a.CodLaboratorio, 0),
  s.TipoIVA = COALESCE(NULLIF(TRIM(a.tipoIVA), ''), 'Gravado'),
  s.Alicuota = COALESCE(a.Alicuota, 0),
  s.AlicuotaIB = COALESCE(a.AlicuotaIB, 0),
  s.Impdesc = 0,
  s.Pordesc = 0,
  s.PrecioCostoxU = COALESCE(a.PrecioCosto, 0),
  s.PrecioNetoxU = COALESCE(a.PrecioCosto, 0),
  s.PrecioIVAxU = COALESCE(a.PrecioCosto, 0) * (COALESCE(iva.Alicuota, a.Alicuota, 0) / 100),
  s.PrecioBrutoxU = COALESCE(a.PrecioCosto, 0) * (1 + COALESCE(iva.Alicuota, a.Alicuota, 0) / 100),
  s.PrecioVentaxU = COALESCE(a.PrecioCosto, 0),
  s.PrecioCostoxR = COALESCE(a.PrecioCosto, 0) * COALESCE(s.Cantidad, 1),
  s.PrecioNetoxR = COALESCE(a.PrecioCosto, 0) * COALESCE(s.Cantidad, 1),
  s.PrecioIVAxR = COALESCE(a.PrecioCosto, 0) * COALESCE(s.Cantidad, 1) * (COALESCE(iva.Alicuota, a.Alicuota, 0) / 100),
  s.PrecioBrutoxR = COALESCE(a.PrecioCosto, 0) * COALESCE(s.Cantidad, 1) * (1 + COALESCE(iva.Alicuota, a.Alicuota, 0) / 100),
  s.PrecioVentaxR = COALESCE(a.PrecioCosto, 0) * COALESCE(s.Cantidad, 1),
  s.imp_alicuota_iva = COALESCE(iva.Alicuota, a.Alicuota, 0),
  s.imp_alicuota_iibb = COALESCE(a.AlicuotaIB, 0),
  s.Anulado = 'No',
  s.id_manual = a.id_manual,
  s.detalle = COALESCE(TRIM(a.NombreArticulo), '');
-- Si la columna anulado es minúscula: usar s.anulado = 'No' en lugar de s.Anulado = 'No'

-- Si la tabla stock usa 'Detalle' (D mayúscula) en lugar de 'detalle', descomenta y usa:
-- s.Detalle = COALESCE(TRIM(a.NombreArticulo), '')

-- Saldo en depósito: opcional (dejar como está o actualizar al valor actual).
-- Descomenta las 2 líneas siguientes si quieres dejar saldo = saldo actual de stock_deposito:
-- s.saldo = (SELECT COALESCE(sd.saldo, 0) FROM stock_deposito sd
--            WHERE sd.id_articulo = s.IDArt AND sd.id_deposito = s.CodDeposito LIMIT 1)

-- Verificación (ejecutar después):
-- SELECT s.id_stock, s.CodigoMovimiento, s.IDArt, s.Fecha, s.CodigoArticulo, s.Descripcion,
--        s.Tipo, s.TipoComp, s.NroComprobante, s.CodigoCP, s.CodSucursal, s.CodViajante,
--        s.PrecioCostoxU, s.PrecioVentaxU, s.Alicuota, s.TipoIVA
-- FROM stock s
-- INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = s.CodigoMovimiento
--   AND cc.id_cuentacliente IN (10764, 10765, 10766);
