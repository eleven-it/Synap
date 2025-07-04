-- Script SQL para inicializar empresa_id y branch_id en tablas de inventory
-- Ejecutar en la base de datos de staging antes de aplicar la migración 0013

-- 1. Obtener la primera empresa y sucursal
DO $$
DECLARE
    empresa_id INTEGER;
    branch_id INTEGER;
    empresa_nombre VARCHAR(255);
    branch_nombre VARCHAR(255);
BEGIN
    -- Obtener la primera empresa
    SELECT id, nombre INTO empresa_id, empresa_nombre 
    FROM core_empresa 
    WHERE activa = true 
    ORDER BY id 
    LIMIT 1;
    
    IF empresa_id IS NULL THEN
        RAISE EXCEPTION 'No se encontró ninguna empresa activa en la base de datos';
    END IF;
    
    -- Obtener la primera sucursal de esa empresa
    SELECT id, name INTO branch_id, branch_nombre 
    FROM core_branch 
    WHERE empresa_id = empresa_id AND active = true 
    ORDER BY id 
    LIMIT 1;
    
    IF branch_id IS NULL THEN
        RAISE EXCEPTION 'No se encontró ninguna sucursal activa para la empresa %', empresa_nombre;
    END IF;
    
    RAISE NOTICE 'Usando empresa: % (ID: %)', empresa_nombre, empresa_id;
    RAISE NOTICE 'Usando sucursal: % (ID: %)', branch_nombre, branch_id;
    
    -- 2. Actualizar Warehouse
    UPDATE inventory_warehouse 
    SET empresa_id = empresa_id 
    WHERE empresa_id IS NULL;
    
    UPDATE inventory_warehouse 
    SET branch_id = branch_id 
    WHERE branch_id IS NULL;
    
    RAISE NOTICE 'Warehouse: Actualizados % registros con empresa_id nulo', ROW_COUNT;
    
    -- 3. Actualizar Location
    UPDATE inventory_location 
    SET empresa_id = empresa_id 
    WHERE empresa_id IS NULL;
    
    UPDATE inventory_location 
    SET branch_id = branch_id 
    WHERE branch_id IS NULL;
    
    RAISE NOTICE 'Location: Actualizados % registros con empresa_id nulo', ROW_COUNT;
    
    -- 4. Actualizar Product
    UPDATE inventory_product 
    SET empresa_id = empresa_id 
    WHERE empresa_id IS NULL;
    
    UPDATE inventory_product 
    SET branch_id = branch_id 
    WHERE branch_id IS NULL;
    
    RAISE NOTICE 'Product: Actualizados % registros con empresa_id nulo', ROW_COUNT;
    
    -- 5. Actualizar StockLot
    UPDATE inventory_stocklot 
    SET empresa_id = empresa_id 
    WHERE empresa_id IS NULL;
    
    UPDATE inventory_stocklot 
    SET branch_id = branch_id 
    WHERE branch_id IS NULL;
    
    RAISE NOTICE 'StockLot: Actualizados % registros con empresa_id nulo', ROW_COUNT;
    
    -- 6. Actualizar StockQuant
    UPDATE inventory_stockquant 
    SET empresa_id = empresa_id 
    WHERE empresa_id IS NULL;
    
    UPDATE inventory_stockquant 
    SET branch_id = branch_id 
    WHERE branch_id IS NULL;
    
    RAISE NOTICE 'StockQuant: Actualizados % registros con empresa_id nulo', ROW_COUNT;
    
    -- 7. Actualizar StockMove
    UPDATE inventory_stockmove 
    SET empresa_id = empresa_id 
    WHERE empresa_id IS NULL;
    
    UPDATE inventory_stockmove 
    SET branch_id = branch_id 
    WHERE branch_id IS NULL;
    
    RAISE NOTICE 'StockMove: Actualizados % registros con empresa_id nulo', ROW_COUNT;
    
    -- 8. Actualizar InventoryAdjustment
    UPDATE inventory_inventoryadjustment 
    SET empresa_id = empresa_id 
    WHERE empresa_id IS NULL;
    
    UPDATE inventory_inventoryadjustment 
    SET branch_id = branch_id 
    WHERE branch_id IS NULL;
    
    RAISE NOTICE 'InventoryAdjustment: Actualizados % registros con empresa_id nulo', ROW_COUNT;
    
    -- 9. Actualizar StockReservation
    UPDATE inventory_stockreservation 
    SET empresa_id = empresa_id 
    WHERE empresa_id IS NULL;
    
    UPDATE inventory_stockreservation 
    SET branch_id = branch_id 
    WHERE branch_id IS NULL;
    
    RAISE NOTICE 'StockReservation: Actualizados % registros con empresa_id nulo', ROW_COUNT;
    
    -- 10. Actualizar ReplenishmentRule
    UPDATE inventory_replenishmentrule 
    SET empresa_id = empresa_id 
    WHERE empresa_id IS NULL;
    
    UPDATE inventory_replenishmentrule 
    SET branch_id = branch_id 
    WHERE branch_id IS NULL;
    
    RAISE NOTICE 'ReplenishmentRule: Actualizados % registros con empresa_id nulo', ROW_COUNT;
    
    -- 11. Actualizar InitialStockDraft
    UPDATE inventory_initialstockdraft 
    SET empresa_id = empresa_id 
    WHERE empresa_id IS NULL;
    
    UPDATE inventory_initialstockdraft 
    SET branch_id = branch_id 
    WHERE branch_id IS NULL;
    
    RAISE NOTICE 'InitialStockDraft: Actualizados % registros con empresa_id nulo', ROW_COUNT;
    
    -- 12. Actualizar InitialStockDraftItem
    UPDATE inventory_initialstockdraftitem 
    SET empresa_id = empresa_id 
    WHERE empresa_id IS NULL;
    
    UPDATE inventory_initialstockdraftitem 
    SET branch_id = branch_id 
    WHERE branch_id IS NULL;
    
    RAISE NOTICE 'InitialStockDraftItem: Actualizados % registros con empresa_id nulo', ROW_COUNT;
    
    RAISE NOTICE '✅ Inicialización completada exitosamente';
    
END $$;

-- 3. Verificar que no queden registros nulos
SELECT 
    'inventory_warehouse' as tabla,
    COUNT(*) as registros_con_empresa_nulo,
    COUNT(*) FILTER (WHERE branch_id IS NULL) as registros_con_branch_nulo
FROM inventory_warehouse
WHERE empresa_id IS NULL OR branch_id IS NULL

UNION ALL

SELECT 
    'inventory_location' as tabla,
    COUNT(*) as registros_con_empresa_nulo,
    COUNT(*) FILTER (WHERE branch_id IS NULL) as registros_con_branch_nulo
FROM inventory_location
WHERE empresa_id IS NULL OR branch_id IS NULL

UNION ALL

SELECT 
    'inventory_product' as tabla,
    COUNT(*) as registros_con_empresa_nulo,
    COUNT(*) FILTER (WHERE branch_id IS NULL) as registros_con_branch_nulo
FROM inventory_product
WHERE empresa_id IS NULL OR branch_id IS NULL

UNION ALL

SELECT 
    'inventory_stocklot' as tabla,
    COUNT(*) as registros_con_empresa_nulo,
    COUNT(*) FILTER (WHERE branch_id IS NULL) as registros_con_branch_nulo
FROM inventory_stocklot
WHERE empresa_id IS NULL OR branch_id IS NULL

UNION ALL

SELECT 
    'inventory_stockquant' as tabla,
    COUNT(*) as registros_con_empresa_nulo,
    COUNT(*) FILTER (WHERE branch_id IS NULL) as registros_con_branch_nulo
FROM inventory_stockquant
WHERE empresa_id IS NULL OR branch_id IS NULL

UNION ALL

SELECT 
    'inventory_stockmove' as tabla,
    COUNT(*) as registros_con_empresa_nulo,
    COUNT(*) FILTER (WHERE branch_id IS NULL) as registros_con_branch_nulo
FROM inventory_stockmove
WHERE empresa_id IS NULL OR branch_id IS NULL

UNION ALL

SELECT 
    'inventory_inventoryadjustment' as tabla,
    COUNT(*) as registros_con_empresa_nulo,
    COUNT(*) FILTER (WHERE branch_id IS NULL) as registros_con_branch_nulo
FROM inventory_inventoryadjustment
WHERE empresa_id IS NULL OR branch_id IS NULL

UNION ALL

SELECT 
    'inventory_stockreservation' as tabla,
    COUNT(*) as registros_con_empresa_nulo,
    COUNT(*) FILTER (WHERE branch_id IS NULL) as registros_con_branch_nulo
FROM inventory_stockreservation
WHERE empresa_id IS NULL OR branch_id IS NULL

UNION ALL

SELECT 
    'inventory_replenishmentrule' as tabla,
    COUNT(*) as registros_con_empresa_nulo,
    COUNT(*) FILTER (WHERE branch_id IS NULL) as registros_con_branch_nulo
FROM inventory_replenishmentrule
WHERE empresa_id IS NULL OR branch_id IS NULL

UNION ALL

SELECT 
    'inventory_initialstockdraft' as tabla,
    COUNT(*) as registros_con_empresa_nulo,
    COUNT(*) FILTER (WHERE branch_id IS NULL) as registros_con_branch_nulo
FROM inventory_initialstockdraft
WHERE empresa_id IS NULL OR branch_id IS NULL

UNION ALL

SELECT 
    'inventory_initialstockdraftitem' as tabla,
    COUNT(*) as registros_con_empresa_nulo,
    COUNT(*) FILTER (WHERE branch_id IS NULL) as registros_con_branch_nulo
FROM inventory_initialstockdraftitem
WHERE empresa_id IS NULL OR branch_id IS NULL

ORDER BY tabla; 