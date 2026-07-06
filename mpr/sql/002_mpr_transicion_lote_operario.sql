-- MPR — Operario fabricante y contexto fecha/turno en transiciones (clasificación por rendimiento)
-- Ejecutar vía: Migración esquema MySQL → «MPR — tablas core Synap» (catalog.run_mpr_core_tables_mysql)
-- Idempotente: los ALTER se aplican solo si faltan columnas.

ALTER TABLE mpr_transicion_lote
    ADD COLUMN id_operario INT NULL COMMENT 'Operario que fabricó (no el clasificador)' AFTER id_usuario;

ALTER TABLE mpr_transicion_lote
    ADD COLUMN operario_nombre VARCHAR(255) NOT NULL DEFAULT '-' COMMENT 'Snapshot nombre operario fabricante' AFTER id_operario;

ALTER TABLE mpr_transicion_lote
    ADD COLUMN fecha_produccion DATE NULL COMMENT 'Fecha de carga del parte/clasificación' AFTER operario_nombre;

ALTER TABLE mpr_transicion_lote
    ADD COLUMN id_mpr_turno BIGINT NULL COMMENT 'Turno de producción del parte/clasificación' AFTER fecha_produccion;

CREATE INDEX idx_mpr_tl_fecha_turno_art_op ON mpr_transicion_lote (fecha_produccion, id_mpr_turno, id_articulo, id_operario);
