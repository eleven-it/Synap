-- Script para verificar y ajustar el modo SQL de MySQL
-- Ejecutar en la base de datos de administraNET

-- Verificar el modo SQL actual
SELECT @@sql_mode;

-- Verificar si hay registros con fechas inválidas
SELECT COUNT(*) as registros_con_fecha_invalida 
FROM articulo 
WHERE fecha_alta = '0000-00-00 00:00:00' 
   OR fecha_mod = '0000-00-00 00:00:00';

-- Opción 1: Cambiar temporalmente el modo SQL para la sesión
SET SESSION sql_mode = '';

-- Verificar que el cambio se aplicó
SELECT @@sql_mode;

-- Ahora intentar agregar el campo
ALTER TABLE articulo 
ADD COLUMN last_synced_with_synap TIMESTAMP NULL;

-- Restaurar el modo SQL original (opcional)
-- SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO';

-- Verificar que el campo se agregó
DESCRIBE articulo; 