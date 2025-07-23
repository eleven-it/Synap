-- Script para agregar campos de timestamp en administraNET
-- Ejecutar en la base de datos de administraNET

-- Agregar campos de timestamp a la tabla articulo
ALTER TABLE articulo 
ADD COLUMN fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
ADD COLUMN last_synced_with_synap TIMESTAMP NULL;

-- Agregar campos de timestamp a la tabla clientes
ALTER TABLE clientes 
ADD COLUMN fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
ADD COLUMN last_synced_with_synap TIMESTAMP NULL;

-- Agregar campos de timestamp a la tabla stock_deposito (si existe)
ALTER TABLE stock_deposito 
ADD COLUMN fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
ADD COLUMN last_synced_with_synap TIMESTAMP NULL;

-- Agregar campos de timestamp a la tabla pedidos (si existe)
ALTER TABLE pedidos 
ADD COLUMN fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
ADD COLUMN last_synced_with_synap TIMESTAMP NULL;

-- Crear índices para mejorar performance
CREATE INDEX idx_articulo_fecha_modificacion ON articulo(fecha_modificacion);
CREATE INDEX idx_articulo_last_synced ON articulo(last_synced_with_synap);
CREATE INDEX idx_clientes_fecha_modificacion ON clientes(fecha_modificacion);
CREATE INDEX idx_clientes_last_synced ON clientes(last_synced_with_synap);

-- Comentarios para documentar los campos
ALTER TABLE articulo 
MODIFY COLUMN fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP 
COMMENT 'Timestamp de última modificación del artículo';

ALTER TABLE articulo 
MODIFY COLUMN last_synced_with_synap TIMESTAMP NULL 
COMMENT 'Timestamp de última sincronización exitosa con Synap';

ALTER TABLE clientes 
MODIFY COLUMN fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP 
COMMENT 'Timestamp de última modificación del cliente';

ALTER TABLE clientes 
MODIFY COLUMN last_synced_with_synap TIMESTAMP NULL 
COMMENT 'Timestamp de última sincronización exitosa con Synap';

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