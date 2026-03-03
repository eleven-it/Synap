-- =============================================================================
-- Corrección pendiente OPT 16 tras OPP ya registrada (bug id_lista_produccion)
-- =============================================================================
-- Contexto: Se registró la OPP de 4520 unidades a Terminado, pero el detalle
-- de la OPT 16 seguía mostrando 4520 pendientes en 2 artículos porque el UPDATE
-- en lista_produccion_agrupada usaba solo id_lista_produccion=16; en OPT
-- agrupada cada artículo tiene su propio id_lista_produccion (16, 17, 18).
--
-- Ejecutar en la base de la empresa (ej. administranet92).
-- Ajustar el nombre de la tabla si en tu servidor es distinto
-- (ej. Lista_Produccion_Agrupada). Ver con: SHOW TABLES LIKE '%produccion%';
-- =============================================================================

-- 1) Ver estado actual: filas con pendiente > 0 que podrían ser de OPT 16
--    (id_lista_produccion 16 y, si existe OPT agrupada, 17 y 18)
SELECT
    l.id_lista_produccion,
    l.id_articulo,
    a.CodigoArticuloT AS codigo,
    l.cantidad_pedida,
    l.cantidad_pendiente_prod AS pendiente,
    l.en_proceso_produccion
FROM lista_produccion_agrupada l
JOIN articulo a ON a.IDArt = l.id_articulo
WHERE l.id_lista_produccion IN (16, 17, 18)
ORDER BY l.id_lista_produccion, l.id_articulo;

-- 2) Corregir: poner a 0 el pendiente de las filas que corresponden a OPT 16.
--    Opción A: Si los 3 artículos están bajo id_lista_produccion = 16:
-- UPDATE lista_produccion_agrupada
-- SET cantidad_pendiente_prod = 0
-- WHERE id_lista_produccion = 16;

--    Opción B: Si OPT 16 es agrupada (id_lista 16, 17, 18) y solo se actualizó
--    la fila 16, poner a 0 las filas 17 y 18:
-- UPDATE lista_produccion_agrupada
-- SET cantidad_pendiente_prod = 0
-- WHERE id_lista_produccion IN (17, 18);

--    Opción C (recomendada): Poner a 0 todo lo que sea OPT 16 (16, 17 y 18),
--    por si en algún caso quedó pendiente en 16 también:
UPDATE lista_produccion_agrupada
SET cantidad_pendiente_prod = 0
WHERE id_lista_produccion IN (16, 17, 18);

-- 3) Comprobar después: el total pendiente para 16/17/18 debería ser 0
SELECT
    id_lista_produccion,
    SUM(cantidad_pendiente_prod) AS total_pendiente
FROM lista_produccion_agrupada
WHERE id_lista_produccion IN (16, 17, 18)
GROUP BY id_lista_produccion;
