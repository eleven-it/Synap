-- Añade cod_viajante a self_checkout_kiosk (bases existentes creadas antes de esta columna).
-- Ejecutar una sola vez por base de empresa:
--   mysql -u ... -p nombre_base < 002_add_cod_viajante_kiosk.sql
-- Si la columna ya existe (ej. tabla creada con 001 actualizado), el ALTER fallará; ignorar en ese caso.

ALTER TABLE self_checkout_kiosk
ADD COLUMN cod_viajante INT NULL DEFAULT NULL COMMENT 'FK viajantes.CodViajante - vendedor asignado al kiosco' AFTER id_deposito;
