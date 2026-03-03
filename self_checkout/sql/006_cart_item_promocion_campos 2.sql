-- Promociones por artículo (réplica TPV VB6): campos en cart_item para persistir en stock.
-- Ejecutar en cada base de empresa donde se use self_checkout/TPV.
-- Si la columna ya existe, omitir el ALTER correspondiente.
--
-- Alternativa con comando Django (idempotente):
--   python manage.py self_checkout_apply_migration_006 --base-empresa <NOMBRE>
--   python manage.py self_checkout_apply_migrations_promociones_voucher --base-empresa <NOMBRE>

ALTER TABLE self_checkout_cart_item ADD COLUMN promocion_por DECIMAL(18,4) DEFAULT NULL COMMENT 'Promoción % o monto' AFTER promocion;
ALTER TABLE self_checkout_cart_item ADD COLUMN promocion_tipo VARCHAR(64) DEFAULT NULL COMMENT 'Monto fijo, Importe descuento, Cantidad, etc.' AFTER promocion_por;
ALTER TABLE self_checkout_cart_item ADD COLUMN promocion_cant DECIMAL(18,4) DEFAULT NULL COMMENT 'Cantidad mínima promo' AFTER promocion_tipo;
