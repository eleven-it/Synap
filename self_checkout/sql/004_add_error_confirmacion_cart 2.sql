-- =============================================================================
-- Self-Checkout: estado error_confirmacion y campos para recuperación
-- Ejecutar: python manage.py self_checkout_apply_migration_004 --base-empresa <NOMBRE>
--   o ejecutar las sentencias manualmente en la base de la empresa.
-- Compatible con MySQL 5.7 (no hay IF NOT EXISTS en ADD COLUMN).
-- =============================================================================

-- Agregar columnas para persistir error de confirmación (recuperación por supervisor)
ALTER TABLE self_checkout_cart ADD COLUMN ultimo_error_confirmacion VARCHAR(512) DEFAULT NULL COMMENT 'Mensaje del último fallo al confirmar';
ALTER TABLE self_checkout_cart ADD COLUMN ultimo_intento_confirmacion DATETIME DEFAULT NULL COMMENT 'Timestamp del último intento fallido';
