-- =============================================================================
-- Schema MPR – Base administranet (base_empresa)
-- =============================================================================
-- Ejecutar en la base de la empresa (ej. administranet92).
-- Si alguna columna ya existe, MySQL devolverá error; se puede ignorar o
-- comprobar antes con: SHOW COLUMNS FROM deposito LIKE 'suma_stock';
--                    SHOW COLUMNS FROM articulo LIKE 'stock_reserva';
-- Referencia: docs/mpr/SCHEMA_MPR_ADMINISTRANET92.md
-- Plan: docs/mpr/ANALISIS_MPR_PROPUESTA_MVP.md (4.1, 4.2.1, 4.4)
-- =============================================================================

-- Depósito: indica si suma al stock total (Pedido producción trabajo (OPT)/Unidades, reportes).
-- 'Si' = suma; 'No' = no suma (tránsito, scrap, etc.).
ALTER TABLE deposito ADD COLUMN suma_stock VARCHAR(2) DEFAULT 'Si';

-- Artículo: stock de reserva para Pedido producción trabajo (OPT)/Unidades (stock_reserva - stock_actual).
ALTER TABLE articulo ADD COLUMN stock_reserva DECIMAL(15,2) DEFAULT NULL;

-- -----------------------------------------------------------------------------
-- lista_produccion_agrupada: fecha objetivo por OP (para KPI "OP atrasadas" y Nueva OP).
-- Ejecutar solo si la columna no existe (si existe, MySQL devuelve error 1060).
-- lista_produccion_agrupada_formula no lleva fecha_objetivo (la fecha es por OP).
-- -----------------------------------------------------------------------------
ALTER TABLE lista_produccion_agrupada ADD COLUMN fecha_objetivo DATE NULL DEFAULT NULL AFTER en_proceso_produccion;
