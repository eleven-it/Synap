-- =============================================================================
-- MPR Synap — Borrador de control de calidad (sin movimiento de stock)
-- =============================================================================
-- Idempotente: CREATE TABLE IF NOT EXISTS.
-- Proveedor: mpr_core_tables en legacy_mysql_schema/catalog.py
-- =============================================================================

CREATE TABLE IF NOT EXISTS mpr_clasificacion_borrador (
    id_mpr_clasificacion_borrador BIGINT NOT NULL AUTO_INCREMENT,
    fecha_produccion DATE NOT NULL,
    id_mpr_turno BIGINT NOT NULL,
    id_usuario INT NOT NULL,
    actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_mpr_clasificacion_borrador),
    UNIQUE KEY uk_mpr_cc_borrador_fecha_turno (fecha_produccion, id_mpr_turno)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Cabecera borrador CC por fecha y turno (sin stock)';

CREATE TABLE IF NOT EXISTS mpr_clasificacion_borrador_linea (
    id_mpr_clasificacion_borrador_linea BIGINT NOT NULL AUTO_INCREMENT,
    id_mpr_clasificacion_borrador BIGINT NOT NULL,
    id_articulo INT NOT NULL,
    id_operario INT NOT NULL,
    id_mpr_maquina INT NOT NULL DEFAULT 0,
    cant_semi DECIMAL(15,2) NOT NULL DEFAULT 0,
    cant_2da DECIMAL(15,2) NOT NULL DEFAULT 0,
    cant_scrap DECIMAL(15,2) NOT NULL DEFAULT 0,
    PRIMARY KEY (id_mpr_clasificacion_borrador_linea),
    UNIQUE KEY uk_mpr_cc_borrador_linea (
        id_mpr_clasificacion_borrador, id_articulo, id_operario, id_mpr_maquina
    ),
    CONSTRAINT fk_mpr_cc_borrador_linea_cab
        FOREIGN KEY (id_mpr_clasificacion_borrador)
        REFERENCES mpr_clasificacion_borrador (id_mpr_clasificacion_borrador)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Líneas borrador CC por artículo, operario y máquina';
