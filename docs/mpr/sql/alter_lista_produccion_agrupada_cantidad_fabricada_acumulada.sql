-- =============================================================================
-- MPR: acumulado de unidades armadas (pack) por línea de demanda / OPT
-- =============================================================================
-- Ejecutar en la base de la empresa (ej. administranet92).
-- Si la columna ya existe, omitir esta línea o comprobar con:
--   SHOW COLUMNS FROM lista_produccion_agrupada LIKE 'cantidad_fabricada_acumulada';
-- Referencia: docs/mpr/SCHEMA_MPR_ADMINISTRANET92.md
-- Synap incrementa el valor en ejecutar_armado; al cerrar OPT con demanda restaurada
-- se puede inicializar en la nueva fila (ver cerrar_opt). Opcional: backfill desde histórico.
-- =============================================================================

ALTER TABLE lista_produccion_agrupada
  ADD COLUMN cantidad_fabricada_acumulada DOUBLE NULL DEFAULT 0
  COMMENT 'Unidades de pack armadas acumuladas (OPA) para esta id_lista + id_articulo';
