-- =============================================================================
-- Self-Checkout Synap - DDL para MySQL (base_empresa)
-- Ejecutar en cada base de datos de empresa donde se use el módulo.
-- Comando: python manage.py create_self_checkout_tables --base-empresa <NOMBRE>
--
-- IDEMPOTENTE: CREATE TABLE IF NOT EXISTS. Seguro ejecutar múltiples veces.
-- Índices: cart_id, kiosk_id, estado, timestamps (created_at) en todas las tablas.
-- Sin FKs físicas para máxima compatibilidad con esquemas AdministraNET.
-- FKs lógicas documentadas en comentarios y en self_checkout/README.md.
-- =============================================================================

-- 1. Configuración por kiosco
-- FK lógica: id_sucursal -> sucursales, id_punto_venta -> puntos_venta, id_deposito -> deposito, cod_viajante -> viajantes.CodViajante
CREATE TABLE IF NOT EXISTS self_checkout_kiosk (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    kiosk_id VARCHAR(64) NOT NULL,
    id_sucursal INT NOT NULL,
    id_punto_venta INT NOT NULL,
    id_deposito INT NOT NULL,
    cod_viajante INT NULL DEFAULT NULL COMMENT 'FK viajantes.CodViajante - vendedor asignado al kiosco',
    modo_rfid VARCHAR(16) NOT NULL DEFAULT 'delta' COMMENT 'delta|snapshot',
    activo TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_kiosk_id (kiosk_id),
    INDEX idx_kiosk_activo (kiosk_id, activo),
    INDEX idx_sucursal (id_sucursal),
    INDEX idx_sucursal_pv_dep (id_sucursal, id_punto_venta, id_deposito)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Para bases existentes (tabla creada sin cod_viajante), ejecutar una vez:
-- ALTER TABLE self_checkout_kiosk ADD COLUMN cod_viajante INT NULL DEFAULT NULL COMMENT 'FK viajantes.CodViajante' AFTER id_deposito;

-- 2. Carrito principal
-- FK lógica: kiosk_id -> self_checkout_kiosk.kiosk_id, id_cliente -> clientes
CREATE TABLE IF NOT EXISTS self_checkout_cart (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    kiosk_id VARCHAR(64) NOT NULL,
    id_sucursal INT NOT NULL,
    id_punto_venta INT NOT NULL,
    id_deposito INT NOT NULL,
    estado VARCHAR(32) NOT NULL DEFAULT 'borrador' COMMENT 'borrador|pago_pendiente|pago_aprobado|confirmado|cancelado|error',
    id_cliente INT DEFAULT 1 COMMENT '1=CF Consumidor Final',
    email VARCHAR(255) DEFAULT NULL,
    cuit VARCHAR(20) DEFAULT NULL,
    tipo_comprobante VARCHAR(4) DEFAULT NULL COMMENT 'FA|FB',
    codigo_movimiento BIGINT DEFAULT NULL,
    id_cuentacliente BIGINT DEFAULT NULL COMMENT 'FK lógica -> cuentacliente.id',
    subtotal DECIMAL(18,4) NOT NULL DEFAULT 0,
    total DECIMAL(18,4) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    confirmed_at DATETIME DEFAULT NULL,
    INDEX idx_kiosk_estado (kiosk_id, estado),
    INDEX idx_sucursal_created (id_sucursal, created_at),
    INDEX idx_estado (estado),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- 3. Ítems del carrito
-- FK lógica: cart_id -> self_checkout_cart.id, id_articulo -> articulo, rfid_event_id -> self_checkout_rfid_event.id
CREATE TABLE IF NOT EXISTS self_checkout_cart_item (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    cart_id BIGINT NOT NULL COMMENT 'FK lógica -> self_checkout_cart.id',
    id_articulo INT NOT NULL COMMENT 'FK lógica -> articulo.IDArt',
    codigo_articulo VARCHAR(64) DEFAULT NULL,
    descripcion VARCHAR(255) DEFAULT NULL,
    cantidad DECIMAL(18,4) NOT NULL,
    precio_unitario DECIMAL(18,4) NOT NULL,
    alicuota_iva DECIMAL(8,4) DEFAULT NULL,
    importe_iva DECIMAL(18,4) DEFAULT NULL,
    importe_total DECIMAL(18,4) NOT NULL,
    origen VARCHAR(16) NOT NULL DEFAULT 'scan' COMMENT 'scan|rfid',
    rfid_event_id BIGINT DEFAULT NULL COMMENT 'FK lógica -> self_checkout_rfid_event.id',
    orden INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_cart (cart_id),
    INDEX idx_id_articulo (id_articulo),
    INDEX idx_cart_articulo (cart_id, id_articulo),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- 4. Payment intents (stub)
-- FK lógica: cart_id -> self_checkout_cart.id
-- Índices: cart_id, kiosk_id, estado, created_at
CREATE TABLE IF NOT EXISTS self_checkout_payment_intent (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    cart_id BIGINT NOT NULL COMMENT 'FK lógica -> self_checkout_cart.id',
    kiosk_id VARCHAR(64) NOT NULL,
    id_sucursal INT NOT NULL,
    id_punto_venta INT NOT NULL,
    monto DECIMAL(18,4) NOT NULL,
    estado VARCHAR(32) NOT NULL DEFAULT 'pendiente' COMMENT 'pendiente|aprobado|rechazado|expirado|cancelado',
    id_externo VARCHAR(128) DEFAULT NULL,
    metodo VARCHAR(32) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    approved_at DATETIME DEFAULT NULL,
    INDEX idx_cart (cart_id),
    INDEX idx_kiosk (kiosk_id),
    INDEX idx_estado (estado),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- 5. Factura FE (CAE/CAEA)
-- FK lógica: cart_id -> self_checkout_cart.id, id_cuentacliente -> cuentacliente.id
CREATE TABLE IF NOT EXISTS self_checkout_invoice (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    cart_id BIGINT NOT NULL COMMENT 'FK lógica -> self_checkout_cart.id',
    codigo_movimiento BIGINT NOT NULL,
    id_cuentacliente BIGINT NOT NULL COMMENT 'FK lógica -> cuentacliente.id',
    nro_comprobante VARCHAR(32) NOT NULL,
    tipo_comprobante VARCHAR(4) NOT NULL,
    estado VARCHAR(32) NOT NULL DEFAULT 'pendiente' COMMENT 'pendiente|issued_cae|issued_caea_pending|sent|failed',
    cae VARCHAR(64) DEFAULT NULL,
    vto_cae DATE DEFAULT NULL,
    fe_regimen VARCHAR(8) DEFAULT NULL COMMENT 'CAE|CAEA',
    request_payload TEXT DEFAULT NULL,
    response_payload TEXT DEFAULT NULL,
    error_msg VARCHAR(512) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_cart (cart_id),
    INDEX idx_cuentacliente (id_cuentacliente),
    INDEX idx_estado (estado),
    INDEX idx_nro_comprobante (nro_comprobante),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- 6. Eventos RFID
-- FK lógica: id_articulo -> articulo, cart_id -> self_checkout_cart.id, cart_item_id -> self_checkout_cart_item.id
CREATE TABLE IF NOT EXISTS self_checkout_rfid_event (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    kiosk_id VARCHAR(64) NOT NULL,
    id_sucursal INT NOT NULL,
    tag_id VARCHAR(128) NOT NULL,
    id_articulo INT DEFAULT NULL COMMENT 'FK lógica -> articulo.IDArt',
    sesion_id VARCHAR(64) NOT NULL,
    estado VARCHAR(32) NOT NULL DEFAULT 'leido' COMMENT 'leido|mapeado|propuesto|confirmado|rechazado',
    confirmado_por_usuario TINYINT(1) NOT NULL DEFAULT 0,
    cart_id BIGINT DEFAULT NULL COMMENT 'FK lógica -> self_checkout_cart.id',
    cart_item_id BIGINT DEFAULT NULL COMMENT 'FK lógica -> self_checkout_cart_item.id',
    payload TEXT DEFAULT NULL COMMENT 'JSON opcional',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_kiosk_sesion (kiosk_id, sesion_id),
    INDEX idx_tag (tag_id, created_at),
    INDEX idx_estado (estado),
    INDEX idx_cart (cart_id)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- 7. Sesión activa por kiosco (un kiosco solo puede estar abierto en una máquina a la vez)
-- session_key = Django session key, last_heartbeat se actualiza por heartbeat desde la app
CREATE TABLE IF NOT EXISTS self_checkout_kiosk_session (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    kiosk_id VARCHAR(64) NOT NULL,
    session_key VARCHAR(255) NOT NULL,
    machine_id VARCHAR(128) DEFAULT NULL COMMENT 'Identificador opcional de la máquina',
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_heartbeat DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_kiosk_id (kiosk_id),
    INDEX idx_last_heartbeat (last_heartbeat)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- 8. Audit log
-- FK lógica: cart_id -> self_checkout_cart.id
CREATE TABLE IF NOT EXISTS self_checkout_audit_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    kiosk_id VARCHAR(64) NOT NULL,
    id_sucursal INT NOT NULL,
    id_punto_venta INT NOT NULL,
    cart_id BIGINT DEFAULT NULL COMMENT 'FK lógica -> self_checkout_cart.id',
    accion VARCHAR(64) NOT NULL,
    detalle TEXT DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_kiosk_created (kiosk_id, created_at),
    INDEX idx_cart (cart_id),
    INDEX idx_sucursal_created (id_sucursal, created_at),
    INDEX idx_accion (accion)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
