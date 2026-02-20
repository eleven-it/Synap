-- =============================================================================
-- SINCRONIZAR TALONARIO CON ARCA (solo numeración)
-- =============================================================================
-- Cuando al "Emitir comprobante" aparece:
--   "No coincide el Nro. de talonario con el de ARCA. Talonario próximo: 1, ARCA próximo: 2."
--   (u otro par de valores)
--
-- En administraNET/VB6 TPV, talonarios.Nro = próximo número a usar (no "último usado").
-- Synap usa la misma convención: hay que poner talonarios.Nro = valor "ARCA próximo".
--
-- ¿Por qué pasa?
-- - Comprobante en AFIP que no está en AdministraNET: se autorizó el número en AFIP y luego
--   hubo error/rollback antes de grabar en cuentacliente, o se emitió desde otro sistema/homologación.
-- - Comprobante sí está en cuentacliente: lo creó otro sistema (ej. TPV VB6) que no actualizó
--   talonarios, o talonarios se bajó a 1 después.
--
-- Para comprobar si el número "falta" en cuentacliente (ej. Nro 1 para PV 1 y FC):
--   SELECT id_cuentacliente, NroComprobante, TipoComprobante, Fecha, ImporteVenta
--   FROM cuentacliente
--   WHERE id_pv = 1 AND TipoComprobante = 'FC' AND NroComprobante = '00000001';
-- Si no devuelve filas, el comprobante está en AFIP pero no en AdministraNET (sincronizar Nro = 2).
-- Si devuelve una fila, el comprobante existe en AdministraNET; igual hay que poner talonarios.Nro = 2.
--
-- Reemplazar @id_punto_venta, @TipoComprobante y @ARCA_proximo con los del mensaje.
-- TipoComprobante: 'FA', 'FB' o 'FC' según el comprobante que estés emitiendo.
-- =============================================================================

SET @id_punto_venta = 1;        -- mismo que en el kiosco (Self-Checkout / carritos pendientes)
SET @TipoComprobante = 'FC';    -- 'FA', 'FB' o 'FC' (el que usa el comprobante que falla)
SET @ARCA_proximo = 2;          -- valor "ARCA próximo" del mensaje (ej. si dice "ARCA próximo: 2" poner 2)

-- Nro = ARCA próximo (próximo número a usar; igual que VB6 TPV)
UPDATE talonarios
SET Nro = @ARCA_proximo
WHERE id_punto_venta = @id_punto_venta AND TipoComprobante = @TipoComprobante;

-- Comprobar: próximo será Nro = ARCA próximo
-- SELECT id_punto_venta, TipoComprobante, Nro AS proximo FROM talonarios
-- WHERE id_punto_venta = @id_punto_venta AND TipoComprobante = @TipoComprobante;
