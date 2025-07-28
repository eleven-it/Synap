-- Script de inicialización para integración Tiendanube → administraNET
-- 1. Agregar campo de trazabilidad en comp_ped
ALTER TABLE comp_ped 
  ADD COLUMN IF NOT EXISTS id_tiendanube VARCHAR(50) DEFAULT NULL COMMENT 'ID de pedido original en Tiendanube';

-- 2. Crear vendedor especial para Tiendanube (código 75) si no existe
INSERT IGNORE INTO viajantes (CodViajante, Nombre, ComisionVta, ComisionCob, anulado)
VALUES (75, 'Tiendanube', 0.00, 0.00, 'No');

-- 3. (Opcional) Crear tabla de equivalencias de condiciones de venta
CREATE TABLE IF NOT EXISTS tiendanube_cond_venta_map (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metodo_pago_tiendanube VARCHAR(100) NOT NULL,
    id_cv INT NOT NULL,
    descripcion VARCHAR(255)
); 