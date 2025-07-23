-- Script seguro para agregar campo de sincronización
-- Evita conflictos con el modo SQL estricto
-- Ejecutar en la base de datos de administraNET

-- Verificar si el campo ya existe
SELECT COUNT(*) as campo_existe
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME = 'articulo'
AND COLUMN_NAME = 'last_synced_with_synap';

-- Si no existe, agregarlo usando una aproximación segura
-- Usar DATETIME en lugar de TIMESTAMP para evitar problemas de modo SQL
ALTER TABLE articulo 
ADD COLUMN last_synced_with_synap DATETIME NULL;

-- Crear índice para el nuevo campo
CREATE INDEX idx_articulo_last_synced ON articulo(last_synced_with_synap);

-- Hacer lo mismo para la tabla clientes
ALTER TABLE clientes 
ADD COLUMN last_synced_with_synap DATETIME NULL;

CREATE INDEX idx_clientes_last_synced ON clientes(last_synced_with_synap);

-- Verificar que los campos se agregaron correctamente
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME IN ('articulo', 'clientes')
AND COLUMN_NAME = 'last_synced_with_synap'
ORDER BY TABLE_NAME;

-- Mostrar estructura final de campos de timestamp
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    EXTRA
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME IN ('articulo', 'clientes')
AND COLUMN_NAME IN ('fecha_mod', 'last_synced_with_synap')
ORDER BY TABLE_NAME, COLUMN_NAME; 