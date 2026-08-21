-- =============================================================================
-- MPR Synap — Auditoría baseline CC consolidado por artículo (solo SELECT)
-- =============================================================================
-- Fuente: docs/mpr/PLAN_CC_CONSOLIDADO_POR_ARTICULO.md §12.3
-- Ejecutar en cada base_empresa de prueba ANTES del primer confirm nuevo
-- y DESPUÉS de la batería S1–S9. MUST NOT contener UPDATE/DELETE/INSERT.
-- =============================================================================

-- A. Histórico intacto (guardar resultado)
SELECT tipo_destino,
       SUM(id_operario IS NOT NULL) AS con_operario,
       SUM(id_operario IS NULL) AS sin_operario,
       COUNT(*) AS filas,
       SUM(cantidad) AS qty
FROM mpr_transicion_lote
WHERE tipo_origen = 'Produccion'
  AND tipo_destino IN ('SemiElaborado', '2daSeleccion', 'Scrap')
GROUP BY tipo_destino;

-- B. Saldos Producción de una muestra de artículos (ids de la batería)
-- Comparar con stock_deposito del depósito tipo_mpr = Produccion
-- Reemplazar los ids de ejemplo por los de la batería de prueba:
SELECT sd.id_articulo,
       sd.cantidad AS saldo_produccion
FROM stock_deposito sd
INNER JOIN deposito d ON d.id_deposito = sd.id_deposito
WHERE d.tipo_mpr = 'Produccion'
  AND sd.id_articulo IN (/* ids artículos batería S1–S9 */)
ORDER BY sd.id_articulo;

-- Gate de deploy: A.con_operario y A.qty de filas anteriores al corte no bajan.
-- Las filas nuevas Semi aumentan sin_operario y qty según pruebas, sin repartir histórico.
