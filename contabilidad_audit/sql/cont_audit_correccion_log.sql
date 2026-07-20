-- Log de corrección contable Fase 3 (Synap contabilidad_audit).
-- Tablas NUEVAS; no altera cont_* existentes. Idempotente (CREATE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS cont_audit_correccion_lote (
  lote_id VARCHAR(64) NOT NULL PRIMARY KEY,
  base_empresa VARCHAR(64) NOT NULL,
  dry_run_id VARCHAR(64) NOT NULL,
  config_hash VARCHAR(80) NOT NULL,
  usuario VARCHAR(64) NOT NULL,
  fecha DATETIME NOT NULL,
  estado VARCHAR(24) NOT NULL DEFAULT 'aplicado',
  reapertura_flag TINYINT(1) NOT NULL DEFAULT 0,
  autorizador VARCHAR(64) DEFAULT NULL,
  backups_json TEXT DEFAULT NULL,
  INDEX idx_cont_audit_lote_dry_run (dry_run_id),
  INDEX idx_cont_audit_lote_fecha (fecha)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS cont_audit_correccion (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  lote_id VARCHAR(64) NOT NULL,
  check_id VARCHAR(64) NOT NULL,
  tabla VARCHAR(64) NOT NULL,
  clave TEXT NOT NULL,
  valor_anterior TEXT DEFAULT NULL,
  valor_nuevo TEXT DEFAULT NULL,
  usuario VARCHAR(64) NOT NULL,
  fecha DATETIME NOT NULL,
  INDEX idx_cont_audit_corr_lote (lote_id),
  INDEX idx_cont_audit_corr_tabla (tabla)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
