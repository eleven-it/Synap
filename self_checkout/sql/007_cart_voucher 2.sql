-- Voucher / programa de descuentos aplicado al carrito (réplica TPV VB6).
-- id_sp_cupon = cupón usado; monto_descuento_voucher = % descuento al pie (desde sp_desc_programa.monto_descuento).
-- Ejecutar en cada base de empresa. Omitir ALTER si la columna ya existe.
--
-- Alternativa con comando Django (idempotente):
--   python manage.py self_checkout_apply_migration_007 --base-empresa <NOMBRE>
--   python manage.py self_checkout_apply_migrations_promociones_voucher --base-empresa <NOMBRE>

ALTER TABLE self_checkout_cart ADD COLUMN id_sp_cupon BIGINT DEFAULT NULL COMMENT 'FK sp_cupon_cliente.id_sp_cupon' AFTER id_cliente;
ALTER TABLE self_checkout_cart ADD COLUMN monto_descuento_voucher DECIMAL(18,4) DEFAULT NULL COMMENT '% descuento voucher al pie' AFTER id_sp_cupon;
