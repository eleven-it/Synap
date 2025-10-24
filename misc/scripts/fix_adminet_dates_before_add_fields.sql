-- Script para corregir fechas inválidas antes de agregar nuevos campos
-- Ejecutar en la base de datos de administraNET

-- Corregir fechas inválidas en tabla articulo
UPDATE articulo 
SET fecha_alta = NULL 
WHERE fecha_alta = '0000-00-00 00:00:00';

UPDATE articulo 
SET fecha_mod = NULL 
WHERE fecha_mod = '0000-00-00 00:00:00';

-- Corregir fechas inválidas en tabla cliente
UPDATE cliente 
SET FechaAlta = NULL 
WHERE FechaAlta = '0000-00-00 00:00:00';

-- Modificar campos de fecha para permitir NULL
ALTER TABLE articulo 
MODIFY COLUMN fecha_alta TIMESTAMP NULL DEFAULT NULL,
MODIFY COLUMN fecha_mod TIMESTAMP NULL DEFAULT NULL;

ALTER TABLE cliente 
MODIFY COLUMN FechaAlta TIMESTAMP NULL DEFAULT NULL;

-- Ahora agregar los campos id_tiendanube
ALTER TABLE articulo 
ADD COLUMN id_tiendanube BIGINT NULL COMMENT 'ID del producto en TiendaNube';

ALTER TABLE cliente 
ADD COLUMN id_tiendanube BIGINT NULL COMMENT 'ID del cliente en TiendaNube';

-- Crear índices
CREATE INDEX idx_articulo_id_tiendanube ON articulo(id_tiendanube);
CREATE INDEX idx_cliente_id_tiendanube ON cliente(id_tiendanube);

-- Verificar que se agregaron correctamente
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
