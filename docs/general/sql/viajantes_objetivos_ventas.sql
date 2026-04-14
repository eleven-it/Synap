-- Referencia DDL: tabla legacy AdministraNET para objetivos de venta por cliente.
-- La creación idempotente en entornos reales debe hacerse vía
-- core/services/legacy_mysql_schema/catalog.py (proveedor dedicado).
--
-- Ajustar tipos de Codigo/CodViajante si en la instancia cliente.Codigo o viajantes.CodViajante difieren.

CREATE TABLE IF NOT EXISTS viajantes_objetivos_ventas (
    id BIGINT NOT NULL AUTO_INCREMENT,
    Codigo INT NOT NULL COMMENT 'cliente.Codigo',
    CodViajante INT NOT NULL COMMENT 'Snapshot viajante al guardar',
    id_periodo BIGINT NULL COMMENT 'viajantes_objetivos_periodo.id',
    fecha_desde DATE NOT NULL,
    fecha_hasta DATE NOT NULL,
    objetivo DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    PRIMARY KEY (id),
    INDEX idx_vov_cliente (Codigo),
    INDEX idx_vov_viajante (CodViajante),
    INDEX idx_vov_periodo_id (id_periodo),
    INDEX idx_vov_periodo (fecha_desde, fecha_hasta)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Objetivos de venta por cliente y período (Synap + AdministraNET)';
