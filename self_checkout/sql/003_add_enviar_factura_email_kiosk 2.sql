-- Envío de factura por correo: configurable por autoservicio (cada uno tiene un PV).
-- 1 = habilitado (se pide email; en Consumidor Final es opcional). 0 = no se pide ni se envía.
-- Aplicar una vez por base: ALTER TABLE self_checkout_kiosk ADD COLUMN enviar_factura_email ...

ALTER TABLE self_checkout_kiosk
ADD COLUMN enviar_factura_email TINYINT(1) NOT NULL DEFAULT 1
COMMENT '1=habilitar solicitud y envío de factura por email; 0=no pedir email' AFTER activo;
