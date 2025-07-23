-- Script para agregar campos de timestamp en administraNET
-- Evita problemas con el modo SQL de MySQL
-- Ejecutar en la base de datos de administraNET

-- Verificar configuración actual
SELECT @@sql_mode;

-- Agregar campos de timestamp a la tabla articulo (sin DEFAULT para evitar conflictos)
ALTER TABLE articulo 
ADD COLUMN fecha_modificacion TIMESTAMP NULL;

ALTER TABLE articulo 
ADD COLUMN last_synced_with_synap TIMESTAMP NULL;

-- Agregar campos de timestamp a la tabla clientes (sin DEFAULT para evitar conflictos)
ALTER TABLE clientes 
ADD COLUMN fecha_modificacion TIMESTAMP NULL;

ALTER TABLE clientes 
ADD COLUMN last_synced_with_synap TIMESTAMP NULL;

-- Crear índices para mejorar performance
CREATE INDEX idx_articulo_fecha_modificacion ON articulo(fecha_modificacion);
CREATE INDEX idx_articulo_last_synced ON articulo(last_synced_with_synap);
CREATE INDEX idx_clientes_fecha_modificacion ON clientes(fecha_modificacion);
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
AND COLUMN_NAME IN ('fecha_modificacion', 'last_synced_with_synap')
ORDER BY TABLE_NAME, COLUMN_NAME; 