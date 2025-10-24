-- Script simple para agregar campos id_tiendanube a las tablas de AdministraNET
-- Ejecutar en la base de datos de administraNET

-- Agregar campo id_tiendanube a la tabla articulo
ALTER TABLE articulo 
ADD COLUMN id_tiendanube BIGINT NULL COMMENT 'ID del producto en TiendaNube';

-- Agregar campo id_tiendanube a la tabla cliente  
ALTER TABLE cliente 
ADD COLUMN id_tiendanube BIGINT NULL COMMENT 'ID del cliente en TiendaNube';

-- Crear índices para mejorar performance
CREATE INDEX idx_articulo_id_tiendanube ON articulo(id_tiendanube);
CREATE INDEX idx_cliente_id_tiendanube ON cliente(id_tiendanube);

-- Verificar que los campos se agregaron correctamente
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME IN ('articulo', 'cliente')
AND COLUMN_NAME = 'id_tiendanube'
ORDER BY TABLE_NAME;
