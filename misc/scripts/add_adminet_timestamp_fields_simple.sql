-- Script simplificado para agregar campos de timestamp en administraNET
-- Ejecutar en la base de datos de administraNET

-- Verificar si los campos ya existen antes de agregarlos
SET @sql = '';

-- Agregar campos de timestamp a la tabla articulo
SELECT COUNT(*) INTO @articulo_fecha_exists 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'articulo' 
AND COLUMN_NAME = 'fecha_modificacion';

IF @articulo_fecha_exists = 0 THEN
    ALTER TABLE articulo 
    ADD COLUMN fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
    SELECT 'Campo fecha_modificacion agregado a articulo' AS mensaje;
ELSE
    SELECT 'Campo fecha_modificacion ya existe en articulo' AS mensaje;
END IF;

SELECT COUNT(*) INTO @articulo_sync_exists 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'articulo' 
AND COLUMN_NAME = 'last_synced_with_synap';

IF @articulo_sync_exists = 0 THEN
    ALTER TABLE articulo 
    ADD COLUMN last_synced_with_synap TIMESTAMP NULL;
    SELECT 'Campo last_synced_with_synap agregado a articulo' AS mensaje;
ELSE
    SELECT 'Campo last_synced_with_synap ya existe en articulo' AS mensaje;
END IF;

-- Agregar campos de timestamp a la tabla clientes
SELECT COUNT(*) INTO @clientes_fecha_exists 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'clientes' 
AND COLUMN_NAME = 'fecha_modificacion';

IF @clientes_fecha_exists = 0 THEN
    ALTER TABLE clientes 
    ADD COLUMN fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
    SELECT 'Campo fecha_modificacion agregado a clientes' AS mensaje;
ELSE
    SELECT 'Campo fecha_modificacion ya existe en clientes' AS mensaje;
END IF;

SELECT COUNT(*) INTO @clientes_sync_exists 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'clientes' 
AND COLUMN_NAME = 'last_synced_with_synap';

IF @clientes_sync_exists = 0 THEN
    ALTER TABLE clientes 
    ADD COLUMN last_synced_with_synap TIMESTAMP NULL;
    SELECT 'Campo last_synced_with_synap agregado a clientes' AS mensaje;
ELSE
    SELECT 'Campo last_synced_with_synap ya existe en clientes' AS mensaje;
END IF;

-- Crear índices para mejorar performance (solo si no existen)
CREATE INDEX IF NOT EXISTS idx_articulo_fecha_modificacion ON articulo(fecha_modificacion);
CREATE INDEX IF NOT EXISTS idx_articulo_last_synced ON articulo(last_synced_with_synap);
CREATE INDEX IF NOT EXISTS idx_clientes_fecha_modificacion ON clientes(fecha_modificacion);
CREATE INDEX IF NOT EXISTS idx_clientes_last_synced ON clientes(last_synced_with_synap);

-- Verificar que los campos se agregaron correctamente
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME IN ('articulo', 'clientes')
AND COLUMN_NAME IN ('fecha_modificacion', 'last_synced_with_synap')
ORDER BY TABLE_NAME, COLUMN_NAME; 