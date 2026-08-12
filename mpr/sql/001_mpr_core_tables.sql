-- =============================================================================
-- MPR Synap — Tablas core en MySQL (base_empresa / una BD = una empresa)
-- =============================================================================
-- Ejecutar en cada base de datos de empresa donde se use MPR.
-- Comando: python manage.py apply_mpr_core_tables --base-empresa <NOMBRE>
-- Proveedor: Archivo → Migración esquema MySQL → «MPR — tablas core Synap»
--
-- IDEMPOTENTE: CREATE TABLE IF NOT EXISTS. Seguro ejecutar múltiples veces.
-- Charset: utf8mb4. Sin columna base_empresa (tenancy = BD conectada).
-- Referencia: docs/mpr/PLAN_MIGRACION_MPR_MYSQL_FUENTE_UNICA.md
-- =============================================================================

-- 1. Configuración MPR (singleton por instalación)
CREATE TABLE IF NOT EXISTS mpr_config (
    id_mpr_config BIGINT NOT NULL AUTO_INCREMENT,
    bloquear_parte_supera_fabricando TINYINT(1) NOT NULL DEFAULT 1
        COMMENT '1=rechazar parte si supera Fabricando',
    actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_mpr_config)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Parámetros operativos MPR Synap (una fila por BD)';

-- 2. Turnos de producción
CREATE TABLE IF NOT EXISTS mpr_turno (
    id_mpr_turno BIGINT NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_mpr_turno),
    UNIQUE KEY uk_mpr_turno_nombre (nombre),
    KEY idx_mpr_turno_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Turnos de producción MPR';

-- 3. Roster — asignación turno × operario × fecha
CREATE TABLE IF NOT EXISTS mpr_roster_dia (
    id_mpr_roster_dia BIGINT NOT NULL AUTO_INCREMENT,
    fecha DATE NOT NULL,
    id_operario INT NOT NULL COMMENT 'FK lógica sue_abm_empleado.id_sue_abm_empleado',
    id_mpr_turno BIGINT NOT NULL,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_mpr_roster_dia),
    UNIQUE KEY uk_mpr_roster_fecha_operario_turno (fecha, id_operario, id_mpr_turno),
    KEY idx_mpr_roster_fecha (fecha),
    CONSTRAINT fk_mpr_roster_turno FOREIGN KEY (id_mpr_turno)
        REFERENCES mpr_turno (id_mpr_turno) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Planificación diaria de turnos por operario';

-- 4. Envíos directos a producción desde tablero (E7)
CREATE TABLE IF NOT EXISTS mpr_envio_produccion (
    id_mpr_envio_produccion BIGINT NOT NULL AUTO_INCREMENT,
    id_articulo INT NOT NULL COMMENT 'Componente (nivel BOM explotado)',
    cantidad DECIMAL(15,2) NOT NULL,
    id_usuario INT NOT NULL,
    anulado TINYINT(1) NOT NULL DEFAULT 0,
    anulado_en DATETIME NULL COMMENT 'Timestamp anulación supervisor',
    id_usuario_anula INT NULL COMMENT 'Usuario que anuló el envío',
    uuid_lote CHAR(36) NULL COMMENT 'Agrupa líneas del mismo envío desde tablero',
    codigo_movimiento_mstock INT NULL COMMENT 'MSTOCK futuro opcional',
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_mpr_envio_produccion),
    KEY idx_mpr_ep_art_fecha (id_articulo, creado_en),
    KEY idx_mpr_ep_creado (creado_en),
    KEY idx_mpr_ep_lote (uuid_lote)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Ledger envios tablero a produccion';

-- 5. Parte de producción — cabecera
CREATE TABLE IF NOT EXISTS mpr_parte (
    id_mpr_parte BIGINT NOT NULL AUTO_INCREMENT,
    uuid_parte CHAR(36) NULL COMMENT 'Compatibilidad URLs legacy Postgres',
    fecha_produccion DATE NOT NULL,
    id_mpr_turno BIGINT NOT NULL,
    id_usuario INT NOT NULL,
    registrado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notas VARCHAR(500) NOT NULL DEFAULT '',
    movimiento_fisico_ok TINYINT(1) NOT NULL DEFAULT 0,
    id_lista_produccion BIGINT NULL COMMENT 'OPT legacy, NULL en partes E8',
    PRIMARY KEY (id_mpr_parte),
    UNIQUE KEY uk_mpr_parte_uuid (uuid_parte),
    KEY idx_mpr_parte_fecha_turno (fecha_produccion, id_mpr_turno),
    KEY idx_mpr_parte_lista (id_lista_produccion),
    CONSTRAINT fk_mpr_parte_turno FOREIGN KEY (id_mpr_turno)
        REFERENCES mpr_turno (id_mpr_turno) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Cabecera parte de producción OPP-parte';

-- 6. Parte — líneas componente × operario
CREATE TABLE IF NOT EXISTS mpr_parte_linea (
    id_mpr_parte_linea BIGINT NOT NULL AUTO_INCREMENT,
    id_mpr_parte BIGINT NOT NULL,
    id_articulo INT NOT NULL,
    id_operario INT NOT NULL,
    operario_nombre VARCHAR(255) NOT NULL DEFAULT '-',
    cantidad DECIMAL(15,2) NOT NULL,
    PRIMARY KEY (id_mpr_parte_linea),
    UNIQUE KEY uk_mpr_parte_linea (id_mpr_parte, id_articulo, id_operario),
    CONSTRAINT fk_mpr_parte_linea_parte FOREIGN KEY (id_mpr_parte)
        REFERENCES mpr_parte (id_mpr_parte) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Líneas de parte de producción';

-- 7. Parte — ajustes append-only
CREATE TABLE IF NOT EXISTS mpr_parte_ajuste (
    id_mpr_parte_ajuste BIGINT NOT NULL AUTO_INCREMENT,
    uuid_ajuste CHAR(36) NULL,
    id_mpr_parte BIGINT NOT NULL,
    id_articulo INT NOT NULL,
    id_operario INT NOT NULL,
    delta DECIMAL(15,2) NOT NULL,
    motivo VARCHAR(255) NOT NULL,
    id_usuario INT NOT NULL,
    registrado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ajuste_fisico_ok TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id_mpr_parte_ajuste),
    UNIQUE KEY uk_mpr_parte_ajuste_uuid (uuid_ajuste),
    KEY idx_mpr_parte_ajuste_linea (id_mpr_parte, id_articulo, id_operario),
    CONSTRAINT fk_mpr_parte_ajuste_parte FOREIGN KEY (id_mpr_parte)
        REFERENCES mpr_parte (id_mpr_parte) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Ajustes delta sobre líneas de parte';

-- 8. Transiciones entre etapas MPR (E5)
CREATE TABLE IF NOT EXISTS mpr_transicion_lote (
    id_mpr_transicion_lote BIGINT NOT NULL AUTO_INCREMENT,
    id_articulo INT NOT NULL,
    tipo_origen VARCHAR(64) NOT NULL,
    tipo_destino VARCHAR(64) NOT NULL,
    cantidad DECIMAL(15,2) NOT NULL,
    codigo_movimiento INT NULL COMMENT 'CodigoMovimiento MSTOCK',
    id_usuario INT NOT NULL,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_mpr_transicion_lote),
    KEY idx_mpr_tl_art_fecha (id_articulo, creado_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Trazabilidad transferencias entre etapas';

-- 9. Packs habilitados para armado surtido
CREATE TABLE IF NOT EXISTS mpr_articulo_armado_surtido (
    id_mpr_articulo_armado_surtido BIGINT NOT NULL AUTO_INCREMENT,
    id_articulo INT NOT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_mpr_articulo_armado_surtido),
    UNIQUE KEY uk_mpr_aas_articulo (id_articulo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Packs habilitados armado surtido';

-- 10. Lote de armado (sesión POS)
CREATE TABLE IF NOT EXISTS mpr_armado_lote (
    id_mpr_armado_lote BIGINT NOT NULL AUTO_INCREMENT,
    uuid_lote CHAR(36) NULL,
    modo VARCHAR(3) NOT NULL COMMENT '1ra | 2da',
    id_operario INT NULL,
    id_usuario INT NOT NULL,
    deposito_origen INT NOT NULL,
    deposito_destino INT NOT NULL,
    ejecutado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cantidad_items INT NOT NULL DEFAULT 0,
    cantidad_exitosos INT NOT NULL DEFAULT 0,
    cantidad_fallidos INT NOT NULL DEFAULT 0,
    PRIMARY KEY (id_mpr_armado_lote),
    UNIQUE KEY uk_mpr_armado_lote_uuid (uuid_lote),
    KEY idx_mpr_armado_lote_modo (modo, ejecutado_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Lote de ejecución armado 1ra/2da';

-- 11. Movimiento armado surtido (cabecera por MSTOCK)
CREATE TABLE IF NOT EXISTS mpr_armado_surtido_movimiento (
    id_mpr_armado_surtido_movimiento BIGINT NOT NULL AUTO_INCREMENT,
    codigo_movimiento INT NOT NULL,
    id_articulo_pack INT NOT NULL,
    cantidad_packs INT NOT NULL,
    deposito_origen INT NOT NULL,
    deposito_destino INT NOT NULL,
    id_lista_produccion BIGINT NULL COMMENT 'OPT legacy opcional',
    id_mpr_armado_lote BIGINT NULL,
    modo VARCHAR(3) NOT NULL DEFAULT '2da',
    estado_imputacion VARCHAR(10) NOT NULL DEFAULT 'na',
    id_operario INT NULL,
    id_usuario INT NOT NULL,
    detalle VARCHAR(500) NOT NULL DEFAULT '',
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_mpr_armado_surtido_movimiento),
    KEY idx_mpr_asm_codigo (codigo_movimiento),
    KEY idx_mpr_asm_modo_imp (modo, estado_imputacion),
    CONSTRAINT fk_mpr_asm_lote FOREIGN KEY (id_mpr_armado_lote)
        REFERENCES mpr_armado_lote (id_mpr_armado_lote) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Cabecera trazabilidad armado surtido';

-- 12. Líneas composición armado surtido
CREATE TABLE IF NOT EXISTS mpr_armado_surtido_linea (
    id_mpr_armado_surtido_linea BIGINT NOT NULL AUTO_INCREMENT,
    id_mpr_armado_surtido_movimiento BIGINT NOT NULL,
    id_articulo_componente INT NOT NULL,
    codigo_articulo VARCHAR(64) NOT NULL DEFAULT '-',
    descripcion_articulo VARCHAR(255) NOT NULL DEFAULT '-',
    cantidad_por_pack INT NOT NULL,
    cantidad_total INT NOT NULL,
    PRIMARY KEY (id_mpr_armado_surtido_linea),
    CONSTRAINT fk_mpr_asl_mov FOREIGN KEY (id_mpr_armado_surtido_movimiento)
        REFERENCES mpr_armado_surtido_movimiento (id_mpr_armado_surtido_movimiento)
        ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Componentes por movimiento armado surtido';

-- 13. Imputación armado 1ra a pedidos
CREATE TABLE IF NOT EXISTS mpr_imputacion_armado (
    id_mpr_imputacion_armado BIGINT NOT NULL AUTO_INCREMENT,
    codigo_movimiento INT NOT NULL,
    id_articulo_pack INT NOT NULL,
    cantidad INT NOT NULL,
    codigo_movimiento_pedido INT NOT NULL,
    id_lista_detalle BIGINT NULL,
    origen_regla VARCHAR(10) NOT NULL COMMENT 'FIFO | MANUAL',
    id_usuario_supervisor INT NOT NULL,
    imputado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notas VARCHAR(500) NOT NULL DEFAULT '',
    PRIMARY KEY (id_mpr_imputacion_armado),
    KEY idx_mpr_imp_codigo (codigo_movimiento),
    KEY idx_mpr_imp_pedido (codigo_movimiento_pedido)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Imputacion supervisor armado 1ra a pedido';

-- Seed config (una fila si tabla vacía)
INSERT INTO mpr_config (bloquear_parte_supera_fabricando)
SELECT 1 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM mpr_config LIMIT 1);
