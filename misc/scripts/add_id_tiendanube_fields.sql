-- Script para agregar campos id_tiendanube a las tablas de AdministraNET
-- Esto permite integridad referencial completa entre TiendaNube y AdministraNET
-- Ejecutar en la base de datos de administraNET

-- Verificar configuración actual
SELECT @@sql_mode;

-- 1. Agregar campo id_tiendanube a la tabla articulo
-- Verificar si el campo ya existe
SELECT COUNT(*) INTO @articulo_tiendanube_exists 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'articulo' 
AND COLUMN_NAME = 'id_tiendanube';

-- Agregar campo si no existe
SET @sql = IF(@articulo_tiendanube_exists = 0, 
    'ALTER TABLE articulo ADD COLUMN id_tiendanube BIGINT NULL COMMENT "ID del producto en TiendaNube"', 
    'SELECT "Campo id_tiendanube ya existe en articulo" AS mensaje'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. Agregar campo id_tiendanube a la tabla cliente
-- Verificar si el campo ya existe
SELECT COUNT(*) INTO @cliente_tiendanube_exists 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'cliente' 
AND COLUMN_NAME = 'id_tiendanube';

-- Agregar campo si no existe
SET @sql = IF(@cliente_tiendanube_exists = 0, 
    'ALTER TABLE cliente ADD COLUMN id_tiendanube BIGINT NULL COMMENT "ID del cliente en TiendaNube"', 
    'SELECT "Campo id_tiendanube ya existe en cliente" AS mensaje'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 3. Crear índices para mejorar performance de búsquedas
-- Índice para articulo
SELECT COUNT(*) INTO @articulo_index_exists 
FROM INFORMATION_SCHEMA.STATISTICS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'articulo' 
AND INDEX_NAME = 'idx_articulo_id_tiendanube';

SET @sql = IF(@articulo_index_exists = 0, 
    'CREATE INDEX idx_articulo_id_tiendanube ON articulo(id_tiendanube)', 
    'SELECT "Índice idx_articulo_id_tiendanube ya existe" AS mensaje'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Índice para cliente
SELECT COUNT(*) INTO @cliente_index_exists 
FROM INFORMATION_SCHEMA.STATISTICS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'cliente' 
AND INDEX_NAME = 'idx_cliente_id_tiendanube';

SET @sql = IF(@cliente_index_exists = 0, 
    'CREATE INDEX idx_cliente_id_tiendanube ON cliente(id_tiendanube)', 
    'SELECT "Índice idx_cliente_id_tiendanube ya existe" AS mensaje'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 4. Verificar que los campos se agregaron correctamente
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME IN ('articulo', 'cliente')
AND COLUMN_NAME = 'id_tiendanube'
ORDER BY TABLE_NAME;

-- 5. Mostrar estructura actualizada de las tablas
SELECT 'Estructura de tabla articulo:' AS info;
DESCRIBE articulo;

SELECT 'Estructura de tabla cliente:' AS info;
DESCRIBE cliente;

-- 6. Verificar índices creados
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    COLUMN_NAME,
    NON_UNIQUE
FROM INFORMATION_SCHEMA.STATISTICS 
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME IN ('articulo', 'cliente')
AND INDEX_NAME LIKE '%tiendanube%'
ORDER BY TABLE_NAME, INDEX_NAME;
