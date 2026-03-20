-- =============================================================================
-- OPT solo en MySQL: columnas en lista_produccion_agrupada (sin tablas mpr_opt/mpr_opt_linea)
-- =============================================================================
-- Ejecutar en la base de la empresa (ej. administranet92).
-- Si alguna columna ya existe, omitir esa línea o comprobar con:
--   SHOW COLUMNS FROM lista_produccion_agrupada LIKE 'id_opt';
-- Referencia: docs/mpr/SCHEMA_MPR_ADMINISTRANET92.md
-- Plan: OPT solo en MySQL (extender lista_produccion_agrupada)
-- =============================================================================

-- id_opt: opcional / heredado. Synap ya no escribe id_opt; agrupa por codigo_movimiento_opt (ver docs/mpr/OPT_AGRUPACION_CODIGO_MOVIMIENTO.md).
-- "OPT N° 46" = id_lista_produccion de la línea principal devuelta al generar la OPT.
ALTER TABLE lista_produccion_agrupada ADD COLUMN id_opt BIGINT NULL DEFAULT NULL;

-- codigo_movimiento_opt: negativo = placeholder (-id_lista_principal) hasta liberar; positivo = CodigoMovimiento MSTOCK en todas las líneas del lote.
ALTER TABLE lista_produccion_agrupada ADD COLUMN codigo_movimiento_opt INT NULL DEFAULT NULL;

-- id_operario_opt: id_sue_abm_empleado del operario para esta línea (una fila por artículo).
ALTER TABLE lista_produccion_agrupada ADD COLUMN id_operario_opt INT NULL DEFAULT NULL;

-- Índice opcional para listar OPTs y búsquedas por id_opt (descomentar si se desea):
-- CREATE INDEX idx_agrupada_id_opt ON lista_produccion_agrupada (id_opt);
