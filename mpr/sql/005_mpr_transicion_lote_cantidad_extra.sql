-- MPR — Cantidad clasificada por encima del parte (extra producción) en transiciones CC
-- Ejecutar vía: Migración esquema MySQL → «MPR — tablas core Synap» (catalog.run_mpr_core_tables_mysql)
-- Idempotente: el ALTER se aplica solo si falta la columna.

ALTER TABLE mpr_transicion_lote
    ADD COLUMN cantidad_extra DECIMAL(15,2) NOT NULL DEFAULT 0
    COMMENT 'Unidades clasificadas por encima del remanente atribuible del parte'
    AFTER cantidad;
