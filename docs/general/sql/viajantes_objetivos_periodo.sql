-- Referencia DDL: cabecera de período para objetivos de venta.
-- Creación idempotente en entornos reales: core/services/legacy_mysql_schema/catalog.py (proveedor viajantes_objetivos_ventas).

CREATE TABLE IF NOT EXISTS viajantes_objetivos_periodo (
    id BIGINT NOT NULL AUTO_INCREMENT,
    fecha_desde DATE NOT NULL,
    fecha_hasta DATE NOT NULL,
    descripcion VARCHAR(120) NOT NULL DEFAULT '-'
        COMMENT 'Etiqueta del período (ej. mes y año); "-" si no se informa',
    anulado VARCHAR(3) NOT NULL DEFAULT 'No' COMMENT 'Si / No (paridad AdministraNET)',
    PRIMARY KEY (id),
    INDEX idx_vop_fechas (fecha_desde, fecha_hasta),
    INDEX idx_vop_anulado (anulado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Cabecera de intervalo para objetivos de venta (Synap)';
