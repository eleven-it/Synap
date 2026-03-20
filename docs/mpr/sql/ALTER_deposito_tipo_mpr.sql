-- Añadir columna tipo_mpr a la tabla deposito (AdministraNET/MySQL).
-- Valores: 'Produccion', 'SemiElaborado', 'Terminado', 'Scrap', '2daSeleccion', o NULL.
-- Un solo depósito por tipo (validado en aplicación).
-- Ejecutar en cada base de empresa donde se use MPR.

ALTER TABLE deposito
ADD COLUMN tipo_mpr VARCHAR(20) NULL
COMMENT 'Uso MPR: Produccion, SemiElaborado, Terminado, Scrap, 2daSeleccion';
