-- Añade `descripcion` a `viajantes_objetivos_periodo` (Synap).
-- Ejecutar una vez por base de empresa si aún no corrió el proveedor del catálogo legacy.
-- Si la columna ya existe, MySQL devolverá error 1060 (se puede ignorar).

ALTER TABLE viajantes_objetivos_periodo
ADD COLUMN descripcion VARCHAR(120) NOT NULL DEFAULT '-'
  COMMENT 'Etiqueta del período (ej. mes y año); "-" si no se informa'
AFTER fecha_hasta;
