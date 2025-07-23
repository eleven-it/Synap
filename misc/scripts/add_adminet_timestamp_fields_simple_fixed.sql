-- Script simple para agregar campos de timestamp en administraNET
-- Ejecutar en la base de datos de administraNET

-- Agregar campos de timestamp a la tabla articulo
ALTER TABLE articulo 
ADD COLUMN fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

ALTER TABLE articulo 
ADD COLUMN last_synced_with_synap TIMESTAMP NULL;

-- Agregar campos de timestamp a la tabla clientes
ALTER TABLE clientes 
ADD COLUMN fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

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