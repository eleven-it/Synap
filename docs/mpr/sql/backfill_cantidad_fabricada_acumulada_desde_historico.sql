-- =============================================================================
-- Opcional: inicializar cantidad_fabricada_acumulada desde lista_produccion_historico
-- =============================================================================
-- Ejecutar DESPUÉS de alter_lista_produccion_agrupada_cantidad_fabricada_acumulada.sql
-- Suma cantidad_armada de eventos OPA (armado) por id_lista_produccion e id_articulo (pack).
-- Ajustar nombre de tabla si difiere en la empresa.
-- =============================================================================

UPDATE lista_produccion_agrupada g
INNER JOIN (
    SELECT
        id_lista_produccion,
        id_articulo,
        COALESCE(SUM(COALESCE(cantidad_armada, 0)), 0) AS total_arm
    FROM lista_produccion_historico
    WHERE tipo_evento = 'OPA'
      AND id_lista_produccion IS NOT NULL
      AND id_articulo IS NOT NULL
    GROUP BY id_lista_produccion, id_articulo
) h ON g.id_lista_produccion = h.id_lista_produccion
   AND g.id_articulo = h.id_articulo
SET g.cantidad_fabricada_acumulada = h.total_arm;
