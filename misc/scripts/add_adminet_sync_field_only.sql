-- Script para agregar solo el campo de control de sincronización en administraNET
-- Usa el campo fecha_mod existente para timestamps
-- Ejecutar en la base de datos de administraNET

-- Agregar campo de control de sincronización a la tabla articulo
ALTER TABLE articulo 
ADD COLUMN last_synced_with_synap TIMESTAMP NULL;

-- Agregar campo de control de sincronización a la tabla clientes
ALTER TABLE clientes 
ADD COLUMN last_synced_with_synap TIMESTAMP NULL;

-- Crear índices para mejorar performance
CREATE INDEX idx_articulo_last_synced ON articulo(last_synced_with_synap);
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

-- Mostrar estructura de campos de timestamp
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