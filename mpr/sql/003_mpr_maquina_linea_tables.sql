-- =============================================================================
-- MPR Synap — Trazabilidad por Máquina / Línea / Operario (tablas nuevas)
-- =============================================================================
-- Ejecutar en cada base de datos de empresa donde se use MPR.
-- Proveedor: Archivo -> Migración esquema MySQL -> «MPR — máquina/línea/trazabilidad»
--   (catalog.run_mpr_maquina_linea_mysql)
--
-- IDEMPOTENTE: CREATE TABLE IF NOT EXISTS. Seguro ejecutar múltiples veces.
-- Charset: utf8mb4. Sin columna base_empresa (tenancy = BD conectada).
-- Nombres snake_case (estándar AdministraNET). PK internas: id_mpr_<tabla>.
-- Referencia: openspec/changes/mpr-trazabilidad-maquina-linea-operario/design.md
-- =============================================================================

-- 1. Líneas de producción
CREATE TABLE IF NOT EXISTS mpr_linea (
    id_mpr_linea BIGINT NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_mpr_linea),
    UNIQUE KEY uk_mpr_linea_nombre (nombre),
    KEY idx_mpr_linea_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Líneas de producción MPR';

-- 2. Máquinas de producción
CREATE TABLE IF NOT EXISTS mpr_maquina (
    id_mpr_maquina BIGINT NOT NULL AUTO_INCREMENT,
    codigo VARCHAR(50) NOT NULL COMMENT 'Identificador visible (ej. M-001)',
    nombre VARCHAR(100) NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_mpr_maquina),
    UNIQUE KEY uk_mpr_maquina_codigo (codigo),
    KEY idx_mpr_maquina_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Máquinas de producción MPR';

-- 3. Pertenencia máquina->línea VERSIONADA (a lo sumo una vigente por máquina)
CREATE TABLE IF NOT EXISTS mpr_maquina_linea (
    id_mpr_maquina_linea BIGINT NOT NULL AUTO_INCREMENT,
    id_mpr_maquina BIGINT NOT NULL,
    id_mpr_linea BIGINT NOT NULL,
    vigencia_desde DATE NOT NULL,
    vigencia_hasta DATE NULL COMMENT 'NULL = vigente',
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_mpr_maquina_linea),
    KEY idx_mpr_ml_maquina_vig (id_mpr_maquina, vigencia_hasta),
    KEY idx_mpr_ml_linea_vig (id_mpr_linea, vigencia_hasta),
    CONSTRAINT fk_mpr_ml_maquina FOREIGN KEY (id_mpr_maquina)
        REFERENCES mpr_maquina (id_mpr_maquina) ON DELETE CASCADE ON UPDATE RESTRICT,
    CONSTRAINT fk_mpr_ml_linea FOREIGN KEY (id_mpr_linea)
        REFERENCES mpr_linea (id_mpr_linea) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Pertenencia versionada máquina->línea';

-- 4. Habilitación máquina->artículo VERSIONADA (varios artículos vigentes por máquina)
CREATE TABLE IF NOT EXISTS mpr_maquina_articulo (
    id_mpr_maquina_articulo BIGINT NOT NULL AUTO_INCREMENT,
    id_mpr_maquina BIGINT NOT NULL,
    id_articulo INT NOT NULL COMMENT 'FK lógica articulo.id_articulo',
    vigencia_desde DATE NOT NULL,
    vigencia_hasta DATE NULL COMMENT 'NULL = vigente',
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_mpr_maquina_articulo),
    KEY idx_mpr_ma_maquina_vig (id_mpr_maquina, vigencia_hasta),
    KEY idx_mpr_ma_articulo (id_articulo),
    CONSTRAINT fk_mpr_ma_maquina FOREIGN KEY (id_mpr_maquina)
        REFERENCES mpr_maquina (id_mpr_maquina) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Habilitación versionada máquina->artículo';

-- 5. Línea habitual del operario VERSIONADA
CREATE TABLE IF NOT EXISTS mpr_operario_linea (
    id_mpr_operario_linea BIGINT NOT NULL AUTO_INCREMENT,
    id_operario INT NOT NULL COMMENT 'FK lógica sue_abm_empleado.id_sue_abm_empleado',
    id_mpr_linea BIGINT NOT NULL,
    vigencia_desde DATE NOT NULL,
    vigencia_hasta DATE NULL COMMENT 'NULL = vigente',
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_mpr_operario_linea),
    KEY idx_mpr_ol_operario_vig (id_operario, vigencia_hasta),
    CONSTRAINT fk_mpr_ol_linea FOREIGN KEY (id_mpr_linea)
        REFERENCES mpr_linea (id_mpr_linea) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Línea habitual versionada por operario';

-- 6. Mapeo operario <-> usuario de login (AdministraNET)
CREATE TABLE IF NOT EXISTS mpr_operario_usuario (
    id_mpr_operario_usuario BIGINT NOT NULL AUTO_INCREMENT,
    id_operario INT NOT NULL COMMENT 'FK lógica sue_abm_empleado.id_sue_abm_empleado',
    id_usuario INT NOT NULL COMMENT 'FK lógica usuarios.id_usuario',
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_mpr_operario_usuario),
    UNIQUE KEY uk_mpr_ou_usuario (id_usuario),
    KEY idx_mpr_ou_operario (id_operario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Mapeo operario (sue_abm_empleado) <-> usuario login (usuarios)';
