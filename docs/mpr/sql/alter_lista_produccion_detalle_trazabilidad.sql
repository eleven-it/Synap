-- =============================================================================
-- Trazabilidad lista_produccion_detalle ↔ lista_produccion_agrupada
-- =============================================================================
-- Aplicar con tablas vacías (o tras borrar datos). Forma recomendada:
--
--   docker exec Synap_app python manage.py apply_alter_detalle_trazabilidad <base_empresa>
--
-- Ejemplo: apply_alter_detalle_trazabilidad administranet92
-- Con --dry-run solo muestra qué ALTER se ejecutarían.
--
-- Cambios:
-- 1. Eliminar FK existente en lista_produccion_detalle.id_lista_produccion
-- 2. Renombrar lista_produccion_detalle.id_lista_produccion → id_lista_detalle
-- 3. Añadir lista_produccion_detalle.id_lista_produccion (FK a agrupada)
-- 4. Crear índice idx_detalle_id_lista_produccion
--
-- Relaciones resultantes:
--   lista_produccion_agrupada.id_lista_produccion (PK)
--     ← lista_produccion_detalle.id_lista_produccion (FK)
--     ← lista_produccion_historico.id_lista_produccion (FK lógico)
--   lista_produccion_detalle.id_lista_detalle (PK, identificador de fila)
-- =============================================================================

-- Paso 1: Obtener nombre de la FK (ejecutar y usar el resultado en DROP):
-- SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
-- WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'lista_produccion_detalle'
--   AND COLUMN_NAME = 'id_lista_produccion' AND REFERENCED_TABLE_NAME IS NOT NULL
-- LIMIT 1;

-- Paso 2: Eliminar FK (reemplazar <FK_NAME> por el nombre obtenido):
-- ALTER TABLE lista_produccion_detalle DROP FOREIGN KEY <FK_NAME>;

-- Paso 3: Renombrar columna (ajustar tipo si en tu esquema es distinto):
-- ALTER TABLE lista_produccion_detalle
--   CHANGE COLUMN id_lista_produccion id_lista_detalle BIGINT NOT NULL AUTO_INCREMENT;

-- Paso 4: Añadir columna FK a agrupada:
-- ALTER TABLE lista_produccion_detalle
--   ADD COLUMN id_lista_produccion BIGINT NULL DEFAULT NULL AFTER id_lista_detalle;

-- Paso 5: Crear FK explícita:
-- ALTER TABLE lista_produccion_detalle
--   ADD CONSTRAINT fk_detalle_agrupada_lista_produccion
--   FOREIGN KEY (id_lista_produccion) REFERENCES lista_produccion_agrupada(id_lista_produccion);

-- Paso 6: Índice para JOINs y filtros:
-- CREATE INDEX idx_detalle_id_lista_produccion ON lista_produccion_detalle(id_lista_produccion);
