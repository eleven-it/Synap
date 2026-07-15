-- =============================================================================
-- sandbox-tests.sql
-- ⚠️  SOLO DEV / SANDBOX — NO EJECUTAR EN PRODUCCIÓN
-- ⚠️  Contiene operaciones de escritura para validar reglas AS-IS
-- Base: copia MySQL AdministraNET aislada
-- Referencia: docs/reverse-engineering/orders/13-test-cases.md
-- =============================================================================

-- Marcar entorno antes de cualquier prueba
SELECT
    'SANDBOX_ONLY' AS entorno_requerido,
    DATABASE() AS base_actual,
    NOW() AS ejecutado_en;

-- ABORTAR si no es sandbox (ajustar nombre de base esperado)
-- IF DATABASE() NOT IN ('administranet_sandbox', 'synap_dev_legacy') THEN
--     SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Ejecutar solo en sandbox';
-- END IF;

-- =============================================================================
-- TC-PED-010 — Verificar reserva stock antes/después (lectura + manual)
-- =============================================================================
-- SET @id_art = 1001;
-- SET @id_dep = 1;
SELECT saldo_pedido_cliente AS saldo_antes
FROM stock_deposito
WHERE id_articulo = @id_art AND id_deposito = @id_dep;

-- Tras alta manual por UI o script, repetir:
-- SELECT saldo_pedido_cliente AS saldo_despues FROM stock_deposito WHERE ...;

-- =============================================================================
-- TC-PED-050 — Simular anulación (MUTACIÓN — SOLO SANDBOX)
-- Replicar lógica ajax-comprobante.php tipoComp=PED
-- =============================================================================

-- Variables de prueba — REEMPLAZAR con pedido sandbox desechable
-- SET @cod_mov_p = 999999;
-- SET @errores = 0;

START TRANSACTION;

-- Pre-check ped_fact
SELECT cc.NroComprobante AS bloqueo_factura
FROM ped_fact pf
LEFT JOIN cuentacliente cc ON cc.CodigoMovimiento = pf.CodigoMovimientoF
WHERE pf.CodigoMovimientoP = @cod_mov_p
  AND pf.Anulado = 'No';

-- Pre-check rem_ped
SELECT cp.NroComprobante AS bloqueo_remito
FROM rem_ped rp
LEFT JOIN comp_ped cp ON cp.CodigoMovimiento = rp.codmov_remito
WHERE rp.codmov_pedido = @cod_mov_p
  AND rp.Anulado = 'No';

-- Anular cabecera
UPDATE comp_ped
SET anulado = 'Si'
WHERE CodigoMovimiento = @cod_mov_p
  AND Tipocomprobante = 'PED'
  AND Anulado = 'No';

-- Reversa stock + anular renglones (paridad ajax-comprobante)
UPDATE stockp sp
INNER JOIN stock_deposito sd
    ON sd.id_articulo = sp.IDArt
   AND sd.id_deposito = sp.CodDeposito
SET sd.saldo_pedido_cliente = sd.saldo_pedido_cliente - sp.Cantidad,
    sp.anulado = 'Si'
WHERE sp.CodigoMovimiento = @cod_mov_p
  AND sp.anulado = 'No';

-- NOTA GAP PHP: percep_cli NO se anula aquí (TC-PED-053)
-- Verificar:
-- SELECT * FROM percep_cli WHERE codigo_movimiento = @cod_mov_p;

-- Revertir en sandbox si fue solo prueba:
-- ROLLBACK;
COMMIT;

-- =============================================================================
-- TC-PED-053 — Demostrar gap percep_cli post-anulación PHP
-- =============================================================================
-- SET @cod_mov_anulado = 999999;
SELECT
    cp.Anulado AS pedido_anulado,
    COUNT(pc.id_percep_cli_tipo) AS percep_activas
FROM comp_ped cp
LEFT JOIN percep_cli pc ON pc.codigo_movimiento = cp.CodigoMovimiento
WHERE cp.CodigoMovimiento = @cod_mov_anulado
GROUP BY cp.Anulado;

-- =============================================================================
-- TC-PED-022 — Rollback: forzar fallo (EXTREMO — solo sandbox vacío)
-- NO ejecutar sin pedido de prueba y backup
-- =============================================================================
/*
START TRANSACTION;
-- Simular consumo codmov sin comp_ped exitoso
-- Inspeccionar hueco:
SELECT MAX(CodigoMovimiento) FROM comp_ped;
SELECT CodigoMovimiento FROM codmov WHERE codigo = 1;
ROLLBACK;
*/

-- =============================================================================
-- TC-PED-041 — Demostrar filtro desalineado
-- =============================================================================
SELECT COUNT(*) AS con_tipo_ecom_vendedor
FROM comp_ped
WHERE Tipocomprobante = 'PED'
  AND TipoPedido = 'Ecom vendedor'
  AND Fecha >= DATE_SUB(CURDATE(), INTERVAL 30 DAY);

SELECT COUNT(*) AS con_filtro_ui_web
FROM comp_ped
WHERE Tipocomprobante = 'PED'
  AND TipoPedido = 'Web'
  AND Fecha >= DATE_SUB(CURDATE(), INTERVAL 30 DAY);

-- =============================================================================
-- Limpieza sandbox (opcional, SOLO registros de prueba marcados)
-- =============================================================================
/*
DELETE FROM stockp WHERE CodigoMovimiento = @cod_mov_p AND Detalle LIKE '%SANDBOX_TEST%';
DELETE FROM comp_ped WHERE CodigoMovimiento = @cod_mov_p AND Detalle LIKE '%SANDBOX_TEST%';
DELETE FROM cliente_datos_adicionales WHERE CodigoMovimiento = @cod_mov_p;
DELETE FROM percep_cli WHERE codigo_movimiento = @cod_mov_p;
*/

-- Fin — recordatorio
SELECT 'FIN sandbox-tests.sql — verificar ROLLBACK si no se desea persistir' AS nota;
