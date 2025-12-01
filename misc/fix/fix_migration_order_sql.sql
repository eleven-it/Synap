-- Script SQL para corregir el orden de migraciones
-- Resuelve: reports.0001_initial aplicada antes que core.0007_increase_permiso_codigo_length

-- Paso 1: Verificar estado actual
SELECT app, name, applied 
FROM django_migrations 
WHERE app IN ('core', 'reports') 
AND name IN ('0007_increase_permiso_codigo_length', '0001_initial')
ORDER BY applied;

-- Paso 2: Obtener la fecha de core.0006 (anterior)
-- (Ejecutar esto primero para obtener la fecha)
-- SELECT applied FROM django_migrations WHERE app = 'core' AND name = '0006_empresa_country_alter_empresa_logo_and_more';

-- Paso 3: Obtener la fecha de reports.0001
-- (Ejecutar esto para obtener la fecha)
-- SELECT applied FROM django_migrations WHERE app = 'reports' AND name = '0001_initial';

-- Paso 4: Insertar o actualizar core.0007 con una fecha entre core.0006 y reports.0001
-- IMPORTANTE: Reemplazar 'YYYY-MM-DD HH:MM:SS' con una fecha entre las dos anteriores
-- Ejemplo: Si core.0006 es '2025-01-01 10:00:00' y reports.0001 es '2025-01-01 11:00:00'
-- usar '2025-01-01 10:59:59'

-- Si core.0007 no existe, insertarla:
INSERT INTO django_migrations (app, name, applied)
SELECT 'core', '0007_increase_permiso_codigo_length', 
       (SELECT applied FROM django_migrations 
        WHERE app = 'reports' AND name = '0001_initial' 
        ORDER BY applied DESC LIMIT 1) - INTERVAL '1 second'
WHERE NOT EXISTS (
    SELECT 1 FROM django_migrations 
    WHERE app = 'core' AND name = '0007_increase_permiso_codigo_length'
);

-- Si core.0007 ya existe, actualizar su fecha:
UPDATE django_migrations 
SET applied = (
    SELECT applied FROM django_migrations 
    WHERE app = 'reports' AND name = '0001_initial' 
    ORDER BY applied DESC LIMIT 1
) - INTERVAL '1 second'
WHERE app = 'core' AND name = '0007_increase_permiso_codigo_length'
AND applied > (
    SELECT applied FROM django_migrations 
    WHERE app = 'reports' AND name = '0001_initial' 
    ORDER BY applied DESC LIMIT 1
);

-- Paso 5: Verificar el nuevo orden
SELECT app, name, applied 
FROM django_migrations 
WHERE app IN ('core', 'reports') 
AND name IN ('0007_increase_permiso_codigo_length', '0001_initial')
ORDER BY applied;

