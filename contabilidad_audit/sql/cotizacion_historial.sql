-- Historial diario de cotización dólar (Synap / AdministraNET).
-- Tabla NUEVA; no altera cotizacion existente. Idempotente (CREATE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS cotizacion_historial (
  id_historial INT NOT NULL AUTO_INCREMENT,
  id_cotizacion INT NOT NULL,
  fecha DATE NOT NULL,
  valor_pesos DECIMAL(18,6) NOT NULL,
  tipo_cotizacion VARCHAR(32) NOT NULL DEFAULT 'manual',
  origen VARCHAR(32) NOT NULL DEFAULT 'manual',
  id_usuario INT NULL,
  observacion VARCHAR(255) NOT NULL DEFAULT '-',
  created_at DATETIME NOT NULL,
  PRIMARY KEY (id_historial),
  UNIQUE KEY uq_cotiz_hist_fecha (id_cotizacion, fecha),
  KEY ix_cotiz_hist_cotiz_fecha (id_cotizacion, fecha)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
