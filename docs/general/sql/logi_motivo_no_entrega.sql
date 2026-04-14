-- Catálogo de motivos de no entrega — Logística Synap (MySQL AdministraNET).
-- Ejecutar una vez por base de datos de empresa (mismo criterio que otras tablas en la DB de cliente).
-- Charset alineado al resto de tablas típicas en instalaciones legacy (latin1).

CREATE TABLE IF NOT EXISTS logi_motivo_no_entrega (
  id INT NOT NULL AUTO_INCREMENT,
  descripcion VARCHAR(255) NOT NULL,
  activo VARCHAR(2) NOT NULL DEFAULT 'Si',
  orden INT NOT NULL DEFAULT 0,
  requiere_detalle VARCHAR(2) NOT NULL DEFAULT 'No',
  visible_portal VARCHAR(2) NOT NULL DEFAULT 'No',
  PRIMARY KEY (id),
  KEY idx_logi_motivo_activo_orden (activo, orden, id)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Semilla alineada al legado Synap (MOTIVOS_NO_ENTREGA en código); idempotente por descripción.
INSERT INTO logi_motivo_no_entrega (descripcion, activo, orden, requiere_detalle, visible_portal)
SELECT * FROM (
  SELECT 'No se encuentra en domicilio' AS descripcion, 'Si' AS activo, 10 AS orden, 'No' AS requiere_detalle, 'No' AS visible_portal
  UNION ALL SELECT 'Error de facturación', 'Si', 20, 'No', 'No'
  UNION ALL SELECT 'Error de mercadería', 'Si', 30, 'No', 'No'
  UNION ALL SELECT 'Mercadería defectuosa', 'Si', 40, 'No', 'No'
) AS seed
WHERE NOT EXISTS (
  SELECT 1 FROM logi_motivo_no_entrega m WHERE m.descripcion = seed.descripcion
);
