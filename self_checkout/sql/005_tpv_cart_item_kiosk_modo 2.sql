-- TPV: columnas extendidas en cart_item (grilla carrito) y modo_tpv en kiosk.
-- Ejecutar en cada base de empresa donde se use self_checkout/TPV.
-- Ejecutar una sola vez por base; si la columna ya existe, omitir el ALTER correspondiente.

-- self_checkout_cart_item: datos por renglón para grilla extendida
ALTER TABLE self_checkout_cart_item ADD COLUMN codigo_barras VARCHAR(64) DEFAULT NULL COMMENT 'Código de barra' AFTER codigo_articulo;
ALTER TABLE self_checkout_cart_item ADD COLUMN porcentaje_descuento DECIMAL(8,4) NOT NULL DEFAULT 0 COMMENT '% descuento renglón' AFTER importe_total;
ALTER TABLE self_checkout_cart_item ADD COLUMN promocion VARCHAR(255) DEFAULT NULL COMMENT 'Promoción' AFTER porcentaje_descuento;
ALTER TABLE self_checkout_cart_item ADD COLUMN detalle TEXT DEFAULT NULL COMMENT 'Detalle renglón' AFTER promocion;

-- self_checkout_kiosk: modo TPV (1 = cajero/TPV, 0 = autoservicio)
ALTER TABLE self_checkout_kiosk ADD COLUMN modo_tpv TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1=TPV' AFTER activo;
