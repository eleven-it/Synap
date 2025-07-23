-- Script para corregir fechas inválidas en administraNET
-- Ejecutar en la base de datos de administraNET

-- Verificar registros con fechas inválidas
SELECT 
    COUNT(*) as total_registros,
    SUM(CASE WHEN fecha_alta = '0000-00-00 00:00:00' THEN 1 ELSE 0 END) as fecha_alta_invalida,
    SUM(CASE WHEN fecha_mod = '0000-00-00 00:00:00' THEN 1 ELSE 0 END) as fecha_mod_invalida
FROM articulo;

-- Corregir fechas inválidas en fecha_alta
UPDATE articulo 
SET fecha_alta = CURRENT_TIMESTAMP 
WHERE fecha_alta = '0000-00-00 00:00:00';

-- Corregir fechas inválidas en fecha_mod
UPDATE articulo 
SET fecha_mod = CURRENT_TIMESTAMP 
WHERE fecha_mod = '0000-00-00 00:00:00';

-- Verificar que se corrigieron
SELECT 
    COUNT(*) as total_registros,
    SUM(CASE WHEN fecha_alta = '0000-00-00 00:00:00' THEN 1 ELSE 0 END) as fecha_alta_invalida,
    SUM(CASE WHEN fecha_mod = '0000-00-00 00:00:00' THEN 1 ELSE 0 END) as fecha_mod_invalida
FROM articulo;

-- Ahora agregar el campo de sincronización
ALTER TABLE articulo 
ADD COLUMN last_synced_with_synap TIMESTAMP NULL;

-- Crear índice para el nuevo campo
CREATE INDEX idx_articulo_last_synced ON articulo(last_synced_with_synap);

-- Verificar que se agregó correctamente
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME = 'articulo'
AND COLUMN_NAME = 'last_synced_with_synap'; 