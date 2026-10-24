-- Cajas armadas en Synap antes del control de salida de administraNET.
-- No modifica las tablas stock_control_* ni genera remitos.
CREATE TABLE IF NOT EXISTS synap_prep_caja_secuencia (
    codigo_movimiento_prep BIGINT NOT NULL PRIMARY KEY,
    proximo_numero INT NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS synap_prep_caja (
    id_caja BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    codigo_movimiento_prep BIGINT NOT NULL,
    numero_caja INT NOT NULL,
    codigo_movimiento_ped_origen BIGINT NOT NULL,
    id_cliente BIGINT NOT NULL,
    id_cliente_domicilio BIGINT NULL,
    destino_entrega VARCHAR(255) NOT NULL DEFAULT '',
    estado VARCHAR(12) NOT NULL DEFAULT 'Abierta',
    id_usuario_apertura BIGINT NOT NULL,
    fecha_apertura DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    id_usuario_cierre BIGINT NULL,
    fecha_cierre DATETIME NULL,
    id_stock_control BIGINT NULL,
    fecha_importacion DATETIME NULL,
    UNIQUE KEY uq_synap_prep_numero (codigo_movimiento_prep, numero_caja),
    KEY idx_synap_prep_caja_estado (codigo_movimiento_prep, estado),
    CONSTRAINT fk_synap_prep_caja_secuencia FOREIGN KEY (codigo_movimiento_prep)
      REFERENCES synap_prep_caja_secuencia (codigo_movimiento_prep)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS synap_prep_caja_lectura (
    id_lectura BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    id_caja BIGINT NOT NULL,
    codigo_movimiento_ped BIGINT NOT NULL,
    id_articulo BIGINT NOT NULL,
    id_stock_pedido BIGINT NOT NULL,
    codigo_leido VARCHAR(128) NOT NULL,
    tipo_lectura VARCHAR(32) NOT NULL,
    cantidad_unidades DECIMAL(18,4) NOT NULL,
    idempotency_key CHAR(36) NOT NULL,
    id_usuario BIGINT NOT NULL,
    fecha_lectura DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    anulada TINYINT(1) NOT NULL DEFAULT 0,
    id_usuario_anulacion BIGINT NULL,
    fecha_anulacion DATETIME NULL,
    UNIQUE KEY uq_synap_prep_lectura_key (idempotency_key),
    KEY idx_synap_prep_lectura_pedido_art (codigo_movimiento_ped, id_articulo, anulada),
    KEY idx_synap_prep_lectura_caja (id_caja, anulada),
    CONSTRAINT fk_synap_prep_lectura_caja FOREIGN KEY (id_caja)
      REFERENCES synap_prep_caja (id_caja)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
