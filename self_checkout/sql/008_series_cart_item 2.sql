-- Series (números de serie) en ítems del carrito TPV (réplica administraNET).
-- articulo.serie = 'Si' → el ítem debe tener N números de serie (N = cantidad).
--
-- Alternativa con comando Django:
--   python manage.py self_checkout_apply_migration_008 --base-empresa <NOMBRE>

ALTER TABLE self_checkout_cart_item ADD COLUMN serie VARCHAR(8) DEFAULT NULL COMMENT 'Si/No artículo seriado' AFTER promocion_cant;
ALTER TABLE self_checkout_cart_item ADD COLUMN desc_serie VARCHAR(500) DEFAULT NULL COMMENT 'Resumen números de serie' AFTER serie;

CREATE TABLE IF NOT EXISTS self_checkout_cart_item_serie (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    cart_item_id BIGINT NOT NULL COMMENT 'FK self_checkout_cart_item.id',
    id_serie_entrada BIGINT NOT NULL COMMENT 'FK serie_entrada.id_serie_entrada',
    nro_serie VARCHAR(128) DEFAULT NULL,
    desc_serie VARCHAR(255) DEFAULT NULL,
    vto_serie DATE DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_cart_item (cart_item_id),
    INDEX idx_serie_entrada (id_serie_entrada)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
