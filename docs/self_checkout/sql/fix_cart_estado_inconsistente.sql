-- =============================================================================
-- Fix: Carritos con comprobante emitido pero estado pago_aprobado
-- Ejecutar en la base de datos de la empresa (MySQL, base_empresa)
-- 
-- Uso: Corregir inconsistencia donde self_checkout_invoice tiene fila (comprobante
-- emitido, CAE de AFIP) pero self_checkout_cart.estado sigue en 'pago_aprobado'.
-- =============================================================================

-- PASO 1: Diagnóstico - Ver carritos inconsistentes (tienen invoice pero estado != confirmado)
SELECT 
    sc.id AS cart_id,
    sc.estado AS cart_estado,
    sc.codigo_movimiento AS cart_cod_mov,
    sc.id_cuentacliente AS cart_id_cc,
    si.nro_comprobante,
    si.tipo_comprobante,
    si.cae
FROM self_checkout_cart sc
INNER JOIN self_checkout_invoice si ON si.cart_id = sc.id
WHERE sc.estado != 'confirmado';

-- PASO 2: Corregir (descomentar y ejecutar después de verificar el diagnóstico)
/*
UPDATE self_checkout_cart sc
INNER JOIN self_checkout_invoice si ON si.cart_id = sc.id
SET 
    sc.estado = 'confirmado',
    sc.codigo_movimiento = COALESCE(si.codigo_movimiento, sc.codigo_movimiento),
    sc.id_cuentacliente = COALESCE(si.id_cuentacliente, sc.id_cuentacliente),
    sc.tipo_comprobante = COALESCE(si.tipo_comprobante, sc.tipo_comprobante),
    sc.confirmed_at = COALESCE(sc.confirmed_at, NOW())
WHERE sc.estado != 'confirmado';
*/
