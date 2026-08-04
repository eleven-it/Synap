-- =============================================================================
-- Inventario físico Synap — Ajuste post-snapshot (columnas + auditoría)
-- =============================================================================
-- Ejecutar vía proveedor «Inventario físico Synap» (run_stock_inv_fisico_tables_mysql).
-- Las columnas en inv_fisico_linea se agregan idempotentemente desde catalog.py
-- (columna_existe). Este archivo: tabla auditoría + backfill fecha_snapshot.
--
-- IDEMPOTENTE: CREATE TABLE IF NOT EXISTS; UPDATE backfill seguro repetir.
-- Referencia: sdd/ajuste-post-snapshot-inventario-fisico
-- =============================================================================

CREATE TABLE IF NOT EXISTS inv_fisico_ajuste_auditoria (
    id_auditoria INT NOT NULL AUTO_INCREMENT,
    id_campana INT NOT NULL,
    id_linea INT NOT NULL,
    id_articulo INT NOT NULL,
    id_deposito INT NOT NULL,
    accion VARCHAR(32) NOT NULL COMMENT 'override_guardado|override_quitado|override_pisado|autorizacion',
    ajuste_sistema DECIMAL(18, 4) NULL,
    ajuste_anterior DECIMAL(18, 4) NULL,
    ajuste_nuevo DECIMAL(18, 4) NULL,
    diferencia_real DECIMAL(18, 4) NULL,
    codigo_movimiento INT NULL COMMENT 'MSTOCK vinculado en autorización',
    id_usuario INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_auditoria),
    KEY idx_ifaa_campana (id_campana),
    KEY idx_ifaa_linea (id_linea)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Auditoría de ajustes post-snapshot inventario físico';

UPDATE inv_fisico_campana SET fecha_snapshot = created_at WHERE fecha_snapshot IS NULL;
