-- MPR — Parte con estado/origen (flujo dos etapas), máquina y gap en líneas, override de línea en roster.
-- Ejecutar vía: Migración esquema MySQL -> «MPR — máquina/línea/trazabilidad» (catalog.run_mpr_maquina_linea_mysql)
-- Idempotente: los ALTER se aplican solo si faltan columnas/índices (el proveedor usa columna_existe/indice_existe).
-- Este archivo documenta el DDL; la aplicación idempotente vive en catalog.py.

-- Cabecera de parte: estado del flujo, origen, auditoría de aprobación.
ALTER TABLE mpr_parte
    ADD COLUMN estado VARCHAR(12) NOT NULL DEFAULT 'aprobado'
        COMMENT 'borrador | pendiente | aprobado (backfill aprobado)';
ALTER TABLE mpr_parte
    ADD COLUMN origen VARCHAR(20) NOT NULL DEFAULT 'directo_supervisor'
        COMMENT 'movil_operario | directo_supervisor';
ALTER TABLE mpr_parte
    ADD COLUMN id_usuario_supervisor INT NULL COMMENT 'Supervisor que aprobó';
ALTER TABLE mpr_parte
    ADD COLUMN aprobado_en DATETIME NULL COMMENT 'Timestamp de aprobación';
CREATE INDEX idx_mpr_parte_estado ON mpr_parte (estado);

-- Líneas de parte: dimensión máquina + gap declarado/aprobado.
ALTER TABLE mpr_parte_linea
    ADD COLUMN id_mpr_maquina BIGINT NULL COMMENT 'FK lógica mpr_maquina.id_mpr_maquina';
ALTER TABLE mpr_parte_linea
    ADD COLUMN maquina_nombre VARCHAR(100) NULL COMMENT 'Snapshot código/nombre máquina';
ALTER TABLE mpr_parte_linea
    ADD COLUMN cantidad_declarada DECIMAL(15,2) NOT NULL DEFAULT 0 COMMENT 'Declarada por operario (pares)';
ALTER TABLE mpr_parte_linea
    ADD COLUMN cantidad_aprobada DECIMAL(15,2) NULL COMMENT 'Aprobada por supervisor (pares)';
ALTER TABLE mpr_parte_linea
    ADD COLUMN gap DECIMAL(15,2) NOT NULL DEFAULT 0 COMMENT 'cantidad_aprobada - cantidad_declarada';
ALTER TABLE mpr_parte_linea
    ADD COLUMN motivo VARCHAR(255) NULL COMMENT 'Requerido si gap != 0';
-- La unicidad pasa a incluir la máquina (una fila por parte×artículo×operario×máquina).
ALTER TABLE mpr_parte_linea DROP INDEX uk_mpr_parte_linea;
ALTER TABLE mpr_parte_linea
    ADD UNIQUE KEY uk_mpr_parte_linea_maq (id_mpr_parte, id_articulo, id_operario, id_mpr_maquina);

-- Roster: override de línea por día/turno (NULL = usar línea habitual).
ALTER TABLE mpr_roster_dia
    ADD COLUMN id_mpr_linea BIGINT NULL COMMENT 'Override de línea; NULL = habitual';
