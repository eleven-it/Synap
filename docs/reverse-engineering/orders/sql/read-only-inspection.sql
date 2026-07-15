-- =============================================================================
-- read-only-inspection.sql
-- ABM Pedidos administraNET eCom — SOLO LECTURA
-- Uso: inspección AS-IS post ingeniería inversa (jul 2026)
-- NO ejecutar en producción sin ventana acordada; no modifica datos.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Últimos pedidos eCom (cualquier origen web)
-- -----------------------------------------------------------------------------
SELECT
    cp.CodigoMovimiento,
    cp.NroComprobante,
    DATE_FORMAT(cp.Fecha, '%d/%m/%Y') AS Fecha,
    cp.TipoPedido,
    cp.Estado,
    cp.Anulado,
    cp.autorizacion_sistema,
    cp.autorizacion_web,
    cp.ImporteVenta,
    cp.Codigo AS id_cliente,
    cp.CodViajante,
    cp.id_pv
FROM comp_ped cp
WHERE cp.Tipocomprobante = 'PED'
ORDER BY cp.CodigoMovimiento DESC
LIMIT 20;

-- -----------------------------------------------------------------------------
-- 2. Verificar pedido por NroComprobante (reemplazar placeholder)
-- -----------------------------------------------------------------------------
-- SET @nro = '0001-00000042';
SELECT
    cp.*,
    (SELECT COUNT(*) FROM stockp sp WHERE sp.CodigoMovimiento = cp.CodigoMovimiento AND sp.anulado = 'No') AS renglones_activos,
    (SELECT COUNT(*) FROM percep_cli pc WHERE pc.codigo_movimiento = cp.CodigoMovimiento) AS percepciones
FROM comp_ped cp
WHERE cp.Tipocomprobante = 'PED'
  AND cp.NroComprobante = @nro;

-- -----------------------------------------------------------------------------
-- 3. Renglones y reserva stock de un pedido
-- -----------------------------------------------------------------------------
-- SET @cod_mov = 123456;
SELECT
    sp.IDArt,
    sp.CodigoArticulo,
    sp.Descripcion,
    sp.Cantidad,
    sp.tipo_unidad,
    sp.anulado,
    sp.PrecioNetoxR,
    sp.PrecioBrutoxR,
    sd.saldo_pedido_cliente,
    sd.id_deposito
FROM stockp sp
LEFT JOIN stock_deposito sd
    ON sd.id_articulo = sp.IDArt
   AND sd.id_deposito = sp.CodDeposito
WHERE sp.CodigoMovimiento = @cod_mov
ORDER BY sp.Orden;

-- -----------------------------------------------------------------------------
-- 4. Datos adicionales entrega
-- -----------------------------------------------------------------------------
SELECT *
FROM cliente_datos_adicionales
WHERE CodigoMovimiento = @cod_mov
  AND TipoComprobante = 'PED';

-- -----------------------------------------------------------------------------
-- 5. Distribución TipoPedido (OQ-001 / OQ-002)
-- -----------------------------------------------------------------------------
SELECT
    TipoPedido,
    COUNT(*) AS cantidad,
    MIN(Fecha) AS primera_fecha,
    MAX(Fecha) AS ultima_fecha
FROM comp_ped
WHERE Tipocomprobante = 'PED'
GROUP BY TipoPedido
ORDER BY cantidad DESC;

-- -----------------------------------------------------------------------------
-- 6. Distribución Estado (OQ-003)
-- -----------------------------------------------------------------------------
SELECT
    Estado,
    Anulado,
    COUNT(*) AS cantidad
FROM comp_ped
WHERE Tipocomprobante = 'PED'
GROUP BY Estado, Anulado
ORDER BY cantidad DESC;

-- -----------------------------------------------------------------------------
-- 7. Pedidos Ecom vendedor recientes (alta PHP actual)
-- -----------------------------------------------------------------------------
SELECT
    CodigoMovimiento,
    NroComprobante,
    Fecha,
    Estado,
    Anulado,
    autorizacion_sistema
FROM comp_ped
WHERE Tipocomprobante = 'PED'
  AND TipoPedido IN ('Ecom vendedor', 'Web')
ORDER BY CodigoMovimiento DESC
LIMIT 50;

-- -----------------------------------------------------------------------------
-- 8. Bloqueos anulación: remitos y facturas vinculados
-- -----------------------------------------------------------------------------
SELECT
    cp.CodigoMovimiento,
    cp.NroComprobante,
    rp.codmov_remito,
    cp_rem.NroComprobante AS nro_remito,
    rp.Anulado AS rem_ped_anulado
FROM comp_ped cp
LEFT JOIN rem_ped rp
    ON rp.codmov_pedido = cp.CodigoMovimiento
   AND rp.Anulado = 'No'
LEFT JOIN comp_ped cp_rem
    ON cp_rem.CodigoMovimiento = rp.codmov_remito
WHERE cp.Tipocomprobante = 'PED'
  AND cp.Anulado = 'No'
  AND rp.codmov_pedido IS NOT NULL
LIMIT 50;

SELECT
    cp.CodigoMovimiento,
    cp.NroComprobante,
    pf.CodigoMovimientoF,
    cc.NroComprobante AS nro_factura,
    pf.Anulado AS ped_fact_anulado
FROM comp_ped cp
LEFT JOIN ped_fact pf
    ON pf.CodigoMovimientoP = cp.CodigoMovimiento
   AND pf.Anulado = 'No'
LEFT JOIN cuentacliente cc
    ON cc.CodigoMovimiento = pf.CodigoMovimientoF
WHERE cp.Tipocomprobante = 'PED'
  AND cp.Anulado = 'No'
  AND pf.CodigoMovimientoP IS NOT NULL
LIMIT 50;

-- -----------------------------------------------------------------------------
-- 9. percep_cli huérfanas (pedido anulado, percepción activa) — gap PHP
-- -----------------------------------------------------------------------------
SELECT
    cp.CodigoMovimiento,
    cp.NroComprobante,
    cp.Anulado,
    pc.id_percep_cli_tipo,
    pc.importe_percep_cli
FROM comp_ped cp
INNER JOIN percep_cli pc
    ON pc.codigo_movimiento = cp.CodigoMovimiento
WHERE cp.Tipocomprobante = 'PED'
  AND cp.Anulado = 'Si'
  -- Ajustar si existe columna anulado en percep_cli:
  -- AND (pc.anulado IS NULL OR pc.anulado = 'No')
LIMIT 100;

-- -----------------------------------------------------------------------------
-- 10. Numeración: estado codmov y talonario PED
-- -----------------------------------------------------------------------------
SELECT CodigoMovimiento
FROM codmov
WHERE codigo = 1;

-- Reemplazar @id_pv con punto de venta real
-- SET @id_pv = 1;
SELECT id_punto_venta, TipoComprobante, PV, Nro
FROM talonarios
WHERE TipoComprobante = 'PED'
  AND id_punto_venta = @id_pv;

-- -----------------------------------------------------------------------------
-- 11. Comparar filtro desalineado Web vs Ecom vendedor (PED-RN-081)
-- -----------------------------------------------------------------------------
SELECT COUNT(*) AS filtro_web_legacy
FROM comp_ped
WHERE Tipocomprobante = 'PED'
  AND TipoPedido = 'Web'
  AND Fecha >= DATE_SUB(CURDATE(), INTERVAL 365 DAY);

SELECT COUNT(*) AS alta_ecom_vendedor
FROM comp_ped
WHERE Tipocomprobante = 'PED'
  AND TipoPedido = 'Ecom vendedor'
  AND Fecha >= DATE_SUB(CURDATE(), INTERVAL 365 DAY);

-- -----------------------------------------------------------------------------
-- 12. autorizacion_web poblado sin autorizacion_sistema (OQ-004)
-- -----------------------------------------------------------------------------
SELECT
    CodigoMovimiento,
    NroComprobante,
    TipoPedido,
    autorizacion_sistema,
    autorizacion_web,
    Fecha
FROM comp_ped
WHERE Tipocomprobante = 'PED'
  AND (autorizacion_web IS NOT NULL AND autorizacion_web != '')
  AND Fecha >= DATE_SUB(CURDATE(), INTERVAL 180 DAY)
LIMIT 50;
