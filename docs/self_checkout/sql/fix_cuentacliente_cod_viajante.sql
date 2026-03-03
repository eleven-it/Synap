-- Actualiza CodViajante = 2 en facturas de Self-Checkout ya creadas.
-- Las facturas del kiosco se identifican por tpv_comp = 'Si'.
--
-- Ejecutar en la base MySQL de la empresa (ej: administranet):
--   mysql -u ... -p nombre_base < docs/fix_cuentacliente_cod_viajante.sql
-- O desde un cliente SQL:
--   USE administranet;
--   SOURCE /ruta/docs/fix_cuentacliente_cod_viajante.sql;

-- Opción: actualizar solo las que tienen CodViajante NULL o 0 (facturas creadas antes de asignar vendedor)
UPDATE cuentacliente
SET CodViajante = 2
WHERE tpv_comp = 'Si'
  AND (CodViajante IS NULL OR CodViajante = 0);

-- Para forzar todas las facturas TPV a viajante 2 (incluidas las que ya tenían otro valor), usar:
-- UPDATE cuentacliente SET CodViajante = 2 WHERE tpv_comp = 'Si';
