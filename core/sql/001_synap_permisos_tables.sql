-- =============================================================================
-- Synap — Tablas de permisos y roles independientes de AdministraNET
-- =============================================================================
-- Ejecutar en cada base de datos de empresa (una BD = una empresa).
-- Comando: python manage.py apply_synap_permisos_tables <base_empresa>
-- Proveedor: Archivo -> Migración esquema MySQL -> «Synap — permisos y roles»
--
-- IDEMPOTENTE: CREATE TABLE IF NOT EXISTS. Seguro ejecutar múltiples veces.
-- Charset: latin1 (alineado con permiso_sistema, self_checkout_* y conexiones legacy).
-- Sin FK a tablas VB6 (puestos): idpuesto se referencia por valor lógico.
-- FKs físicas solo intra-synap_* para integridad del catálogo propio.
-- Referencia: openspec/changes/permisos-roles-synap-independientes/design.md
-- =============================================================================

-- 1. Catálogo dinámico de permisos Synap (semilla desde PERMISOS_POR_MODULO)
CREATE TABLE IF NOT EXISTS synap_permiso (
    id_permiso INT NOT NULL AUTO_INCREMENT,
    key_permiso VARCHAR(128) NOT NULL,
    modulo VARCHAR(64) NOT NULL DEFAULT '-',
    nombre VARCHAR(255) NOT NULL DEFAULT '-',
    descripcion VARCHAR(500) NOT NULL DEFAULT '-',
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_permiso),
    UNIQUE KEY uk_synap_permiso_key (key_permiso),
    KEY idx_synap_permiso_modulo (modulo),
    KEY idx_synap_permiso_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=latin1
COMMENT='Catálogo de permisos Synap (independiente de permiso_sistema VB6)';

-- 2. Roles dinámicos de Synap (desacoplados de puestos.idpuesto fijos)
CREATE TABLE IF NOT EXISTS synap_rol (
    id_rol INT NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(128) NOT NULL,
    descripcion VARCHAR(500) NOT NULL DEFAULT '-',
    es_sistema TINYINT(1) NOT NULL DEFAULT 0
        COMMENT '1=rol generado por backfill o sistema (no eliminable desde UI)',
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_rol),
    UNIQUE KEY uk_synap_rol_nombre (nombre),
    KEY idx_synap_rol_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=latin1
COMMENT='Roles dinámicos de Synap';

-- 3. Asignación permiso <-> rol (M2M)
CREATE TABLE IF NOT EXISTS synap_rol_permiso (
    id_rol_permiso INT NOT NULL AUTO_INCREMENT,
    id_rol INT NOT NULL,
    id_permiso INT NOT NULL,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_rol_permiso),
    UNIQUE KEY uk_synap_rol_permiso (id_rol, id_permiso),
    KEY idx_synap_rp_rol (id_rol),
    KEY idx_synap_rp_permiso (id_permiso),
    CONSTRAINT fk_synap_rp_rol FOREIGN KEY (id_rol)
        REFERENCES synap_rol (id_rol) ON DELETE CASCADE ON UPDATE RESTRICT,
    CONSTRAINT fk_synap_rp_permiso FOREIGN KEY (id_permiso)
        REFERENCES synap_permiso (id_permiso) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=latin1
COMMENT='Permisos asignados a cada rol Synap';

-- 4. Mapeo puesto (idpuesto legacy, por valor) <-> rol Synap
CREATE TABLE IF NOT EXISTS synap_puesto_rol (
    id_puesto_rol INT NOT NULL AUTO_INCREMENT,
    idpuesto INT NOT NULL COMMENT 'Valor legacy puestos.idpuesto sin FK a VB6',
    id_rol INT NOT NULL,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_puesto_rol),
    UNIQUE KEY uk_synap_puesto_rol (idpuesto, id_rol),
    KEY idx_synap_pr_puesto (idpuesto),
    KEY idx_synap_pr_rol (id_rol),
    CONSTRAINT fk_synap_pr_rol FOREIGN KEY (id_rol)
        REFERENCES synap_rol (id_rol) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=latin1
COMMENT='Roles Synap asignados a cada puesto (idpuesto ancla fija AdministraNET)';
