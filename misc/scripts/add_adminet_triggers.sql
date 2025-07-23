-- Script para agregar triggers en administraNET
-- Actualiza automáticamente fecha_modificacion cuando se modifica un registro
-- Ejecutar en la base de datos de administraNET

-- Eliminar triggers existentes si existen
DROP TRIGGER IF EXISTS articulo_update_trigger;
DROP TRIGGER IF EXISTS clientes_update_trigger;

-- Trigger para tabla articulo
DELIMITER //
CREATE TRIGGER articulo_update_trigger
BEFORE UPDATE ON articulo
FOR EACH ROW
BEGIN
    SET NEW.fecha_modificacion = CURRENT_TIMESTAMP;
END//
DELIMITER ;

-- Trigger para tabla clientes
DELIMITER //
CREATE TRIGGER clientes_update_trigger
BEFORE UPDATE ON clientes
FOR EACH ROW
BEGIN
    SET NEW.fecha_modificacion = CURRENT_TIMESTAMP;
END//
DELIMITER ;

-- Trigger para insertar fecha_modificacion en nuevos registros de articulo
DELIMITER //
CREATE TRIGGER articulo_insert_trigger
BEFORE INSERT ON articulo
FOR EACH ROW
BEGIN
    IF NEW.fecha_modificacion IS NULL THEN
        SET NEW.fecha_modificacion = CURRENT_TIMESTAMP;
    END IF;
END//
DELIMITER ;

-- Trigger para insertar fecha_modificacion en nuevos registros de clientes
DELIMITER //
CREATE TRIGGER clientes_insert_trigger
BEFORE INSERT ON clientes
FOR EACH ROW
BEGIN
    IF NEW.fecha_modificacion IS NULL THEN
        SET NEW.fecha_modificacion = CURRENT_TIMESTAMP;
    END IF;
END//
DELIMITER ;

-- Verificar que los triggers se crearon correctamente
SELECT 
    TRIGGER_NAME,
    EVENT_MANIPULATION,
    EVENT_OBJECT_TABLE,
    ACTION_TIMING,
    ACTION_STATEMENT
FROM INFORMATION_SCHEMA.TRIGGERS 
WHERE TRIGGER_SCHEMA = DATABASE()
AND EVENT_OBJECT_TABLE IN ('articulo', 'clientes')
ORDER BY EVENT_OBJECT_TABLE, TRIGGER_NAME; 