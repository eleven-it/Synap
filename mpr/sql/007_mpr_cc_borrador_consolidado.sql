-- =============================================================================
-- MPR Synap — Borrador CC consolidado por artículo (shape nuevo, sin turno)
-- =============================================================================
-- Idempotente: CREATE TABLE IF NOT EXISTS.
-- Proveedor: run_mpr_core_tables_mysql en legacy_mysql_schema/catalog.py
-- Convive con mpr_clasificacion_borrador (006); no ALTER ni migración de datos.
-- Nombres UK/FK distintos de 006: InnoDB no permite reutilizar
-- uk_mpr_cc_borrador_linea / fk_mpr_cc_borrador_linea_cab en la misma base.
-- Semi: id_operario=0 e id_mpr_turno=0 (centinela; el repo mapea 0 → NULL al ledger).
-- 2da/scrap: id_operario e id_mpr_turno reales del fabricante.
-- =============================================================================

CREATE TABLE IF NOT EXISTS mpr_cc_borrador (
    id_mpr_cc_borrador BIGINT NOT NULL AUTO_INCREMENT,
    fecha_produccion DATE NOT NULL,
    id_usuario INT NOT NULL,
    actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_mpr_cc_borrador),
    UNIQUE KEY uk_mpr_cc_borrador_fecha (fecha_produccion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Cabecera borrador CC consolidado por fecha (sin turno)';

CREATE TABLE IF NOT EXISTS mpr_cc_borrador_linea (
    id_mpr_cc_borrador_linea BIGINT NOT NULL AUTO_INCREMENT,
    id_mpr_cc_borrador BIGINT NOT NULL,
    id_articulo INT NOT NULL,
    id_operario INT NOT NULL DEFAULT 0 COMMENT '0 = Semi consolidado (centinela)',
    id_mpr_turno BIGINT NOT NULL DEFAULT 0 COMMENT '0 = Semi consolidado (centinela)',
    cant_semi DECIMAL(15,2) NOT NULL DEFAULT 0,
    cant_2da DECIMAL(15,2) NOT NULL DEFAULT 0,
    cant_scrap DECIMAL(15,2) NOT NULL DEFAULT 0,
    PRIMARY KEY (id_mpr_cc_borrador_linea),
    UNIQUE KEY uk_mpr_cc_borrador_cons_linea (
        id_mpr_cc_borrador, id_articulo, id_operario, id_mpr_turno
    ),
    CONSTRAINT fk_mpr_cc_borrador_cons_linea_cab
        FOREIGN KEY (id_mpr_cc_borrador)
        REFERENCES mpr_cc_borrador (id_mpr_cc_borrador)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Líneas borrador CC: Semi (op/turno 0) o 2da/scrap por operario+turno';
