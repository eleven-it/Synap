-- =============================================================================
-- Inventario físico Synap — Tablas core en MySQL (base de empresa)
-- =============================================================================
-- Ejecutar en cada base de datos de empresa donde se use inventario físico.
-- Proveedor: Archivo → Migración esquema MySQL → «Inventario físico Synap»
--
-- IDEMPOTENTE: CREATE TABLE IF NOT EXISTS. Seguro ejecutar múltiples veces.
-- Charset: utf8mb4. Sin columna base_empresa (tenancy = BD conectada).
-- Referencia: openspec/changes/stock-inventario-fisico/design.md
-- =============================================================================

CREATE TABLE IF NOT EXISTS inv_fisico_campana (
    id_campana INT NOT NULL AUTO_INCREMENT,
    fecha DATE NOT NULL,
    estado VARCHAR(32) NOT NULL DEFAULT 'Borrador',
    depositos_json TEXT NOT NULL COMMENT 'JSON array id_deposito o tipos MPR',
    contadores_json TEXT NULL COMMENT 'JSON array id_usuario contadores asignados',
    catalogo_version VARCHAR(64) NOT NULL DEFAULT '',
    umbral_cantidad DECIMAL(18, 4) NULL,
    umbral_porcentaje DECIMAL(10, 4) NULL,
    id_usuario_alta INT NOT NULL,
    fecha_snapshot DATETIME NULL,
    id_movimiento_mstock INT NULL COMMENT 'MSTOCK masivo post-autorización',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_campana),
    KEY idx_inv_fisico_campana_fecha (fecha),
    KEY idx_inv_fisico_campana_estado (estado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Campaña de inventario físico Synap';

CREATE TABLE IF NOT EXISTS inv_fisico_linea (
    id_linea INT NOT NULL AUTO_INCREMENT,
    id_campana INT NOT NULL,
    id_articulo INT NOT NULL,
    id_deposito INT NOT NULL,
    saldo_snapshot DECIMAL(18, 4) NOT NULL DEFAULT 0 COMMENT 'Privado — no exponer a contadores',
    cantidad_contada DECIMAL(18, 4) NULL,
    diferencia DECIMAL(18, 4) NULL COMMENT 'Privado — no exponer a contadores',
    id_contador INT NULL,
    estado_linea VARCHAR(32) NOT NULL DEFAULT 'Pendiente',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_linea),
    UNIQUE KEY uk_inv_fisico_linea_camp_art_dep (id_campana, id_articulo, id_deposito),
    KEY idx_inv_fisico_linea_campana (id_campana),
    KEY idx_inv_fisico_linea_contador (id_contador)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Proyección materializada por artículo×depósito×campaña';

CREATE TABLE IF NOT EXISTS inv_fisico_evento (
    id_evento INT NOT NULL AUTO_INCREMENT,
    client_event_id VARCHAR(36) NOT NULL,
    id_campana INT NOT NULL,
    id_articulo INT NOT NULL,
    id_deposito INT NOT NULL,
    id_contador INT NOT NULL,
    cantidad DECIMAL(18, 4) NOT NULL,
    client_ts DATETIME NOT NULL,
    server_ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resultado VARCHAR(32) NOT NULL DEFAULT 'aceptado',
    motivo VARCHAR(255) NULL,
    PRIMARY KEY (id_evento),
    UNIQUE KEY uk_inv_fisico_evento_client (client_event_id),
    KEY idx_inv_fisico_evento_camp_art_dep (id_campana, id_articulo, id_deposito),
    KEY idx_inv_fisico_evento_campana (id_campana)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Ledger append-only de eventos de conteo (idempotencia sync)';
