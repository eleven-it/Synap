-- Armado: fecha de realizado, estado (borrador/aprobado/anulado) e ítems de borrador.
-- Idempotente vía aplicación en catalog.py (columna_existe / SHOW TABLES).

ALTER TABLE mpr_armado_lote
    ADD COLUMN fecha_realizado DATE NULL
        COMMENT 'Fecha de realizado del armado (puede ser pasada)' AFTER ejecutado_en;

ALTER TABLE mpr_armado_lote
    ADD COLUMN estado VARCHAR(20) NOT NULL DEFAULT 'aprobado'
        COMMENT 'borrador | aprobado | anulado' AFTER fecha_realizado;

ALTER TABLE mpr_armado_lote
    ADD COLUMN movimiento_fisico_ok TINYINT(1) NOT NULL DEFAULT 1
        COMMENT '1 si ya hay MSTOCK del lote' AFTER estado;

ALTER TABLE mpr_armado_lote
    ADD COLUMN detalle VARCHAR(500) NOT NULL DEFAULT ''
        COMMENT 'Detalle cabecera del lote' AFTER movimiento_fisico_ok;

CREATE TABLE IF NOT EXISTS mpr_armado_lote_item (
    id_mpr_armado_lote_item BIGINT NOT NULL AUTO_INCREMENT,
    id_mpr_armado_lote BIGINT NOT NULL,
    id_articulo_pack INT NOT NULL,
    cantidad_packs INT NOT NULL,
    orden INT NOT NULL DEFAULT 0,
    PRIMARY KEY (id_mpr_armado_lote_item),
    KEY idx_mpr_ali_lote (id_mpr_armado_lote),
    CONSTRAINT fk_mpr_ali_lote FOREIGN KEY (id_mpr_armado_lote)
        REFERENCES mpr_armado_lote (id_mpr_armado_lote) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Ítems de lote armado (borrador o snapshot pre-stock)';

CREATE TABLE IF NOT EXISTS mpr_armado_lote_item_linea (
    id_mpr_armado_lote_item_linea BIGINT NOT NULL AUTO_INCREMENT,
    id_mpr_armado_lote_item BIGINT NOT NULL,
    id_articulo_componente INT NOT NULL,
    codigo_articulo VARCHAR(64) NOT NULL DEFAULT '-',
    descripcion_articulo VARCHAR(255) NOT NULL DEFAULT '-',
    cantidad_por_pack INT NOT NULL,
    PRIMARY KEY (id_mpr_armado_lote_item_linea),
    KEY idx_mpr_alil_item (id_mpr_armado_lote_item),
    CONSTRAINT fk_mpr_alil_item FOREIGN KEY (id_mpr_armado_lote_item)
        REFERENCES mpr_armado_lote_item (id_mpr_armado_lote_item) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Composición por ítem de lote armado';
